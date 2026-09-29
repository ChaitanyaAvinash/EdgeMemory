"""Benchmark runner (SPEC §14.1, §14.2): runs one arm over a dataset split and records per-case results.

Owns:
- A: policy document + ledger extract + request, one LLM call.
- B: A plus top-k plain vector search over the seed narratives (same 2,048-token budget), one LLM call.
- C: the full pipeline with HindsightBackend (reflect composes). E is computed from C's coverage in the same
  run (`--arm C` writes both), so it costs no extra LLM requests.
- D: the same pipeline.py with VectorBackend; one LLM call composes (no forked pipeline).
Each run gets a fresh ledger (data/runs/<run>.db) and its own memory bank (SPEC §8.1). The quota guard refuses
a run that would exceed the primary model's remaining tokens unless --force. `--resume` continues a run across
quota days: it keeps the run's ledger and bank, skips cases already in its results file, saves after every case,
and stops cleanly (recording nothing for the case) when the primary model's quota is nearly used up or a call
fails on quota, so a quota stop is never scored as an escalation. Scoring is eval/report.py's job.
Never: reads data/ground_truth/ (scoring does), or runs the test split without --split test being explicit.

Usage: python -m eval.run_arms --arm C|D|A|B --dataset gate1|bench [--split dev] [--only ID,ID] [--force]
       [--run ID [--resume]]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlmodel import Session, select

from api import ledger
from api.engine.composer import STEP_CODES, compose, review_mode
from api.engine.extractor import IntakeForm
from api.engine.normalise import match_vendor, parse_amount
from api.engine.pipeline import (
    floor_context,
    ledger_cases,
    load_master_json,
    master_snapshot,
    run_case,
)
from api.engine.rules import approver_for, inr
from api.engine.types import RequestFacts, fiscal_year
from api.llm import LLM, LLMUnavailable
from api.memory.hindsight_backend import HindsightBackend
from api.memory.vector_backend import VectorBackend
from api.settings import IST, ROOT, config
from scripts.import_history import import_to_ledger, import_to_memory, read_csv

RESULTS = ROOT / "eval" / "results"
RUNS = ROOT / "data" / "runs"
REQUESTS_PER_CASE = {
    "A": 2,
    "B": 2,
    "C": 2,
    "D": 3,
}  # extraction (cached after first) + verifier (+ composer)

# --- datasets ------------------------------------------------------------------------------------


def load_dataset(name: str, split: str) -> tuple[dict, list[dict], list[dict], str]:
    """(master, history records, intake forms, history hash) for a dataset."""
    if name == "gate1":
        g = ROOT / "data" / "gate1"
        master = json.loads((g / "master.json").read_text(encoding="utf-8"))
        hist_path = g / "history.json"
        history = json.loads(hist_path.read_text(encoding="utf-8"))["records"]
        cases = json.loads((g / "cases.json").read_text(encoding="utf-8"))["cases"]
    else:
        master = json.loads((ROOT / "data" / "master" / "master.json").read_text(encoding="utf-8"))
        hist_path = ROOT / "data" / "seed" / "history.csv"
        history = read_csv(hist_path)
        cases = [
            json.loads(f.read_text(encoding="utf-8"))
            for f in sorted((ROOT / "data" / "cases" / split).glob("*.json"))
        ]
    return master, history, cases, hashlib.sha256(hist_path.read_bytes()).hexdigest()[:8]


def form_of(c: dict) -> IntakeForm:
    at = datetime.fromisoformat(c["submitted_at"])
    return IntakeForm(**(c | {"submitted_at": at if at.tzinfo else at.replace(tzinfo=IST)}))


# --- arms A and B --------------------------------------------------------------------------------

StepCode = Literal[STEP_CODES]  # type: ignore[valid-type]


class ArmStep(BaseModel):
    code: StepCode
    reason: str


class ArmAnswer(BaseModel):
    case_class: Literal["normal", "known", "generalized", "composed", "unknown"]
    escalate: bool
    steps: list[ArmStep]


ARM_SYSTEM = """You are a procurement assistant at Kaveri Precision Components (synthetic test data). Given the
procurement policy, a ledger extract and a purchase request, decide how the request should be handled.
case_class: normal (every check passes), known (one check fails and a past resolution applies directly),
generalized (one check fails and a past resolution applies with differences), composed (several checks fail,
each covered by past resolutions), unknown (a failure with no applicable past resolution; escalate).
Recommend steps only from the step library; never recommend releasing a payment. Keep reasons short."""


def ledger_extract(form: IntakeForm, md) -> str:
    """Facts a generic agent with database access would see (no rule results)."""
    vid = match_vendor(form.vendor_name, md.vendors)
    v = md.vendors.get(vid or "")
    amount = parse_amount(form.amount_raw) or 0
    d = form.submitted_at.date()
    lines = [
        f"Request date {d.isoformat()}; cost centre {form.cost_centre}; amount {inr(amount)}; "
        f"quotes attached {form.quotes_attached}."
    ]
    if v:
        lines.append(
            f"Vendor {v.id} {v.name}: status {v.status}, GST {v.gst_status}, {v.cert_name} valid until "
            f"{v.cert_expiry}, bank details last changed {v.bank_changed_at or 'never'}, sole source "
            f"{'yes' if v.sole_source else 'no'}."
        )
    else:
        lines.append(f"Vendor '{form.vendor_name}' not found in the vendor master.")
    b = md.budgets.get((form.cost_centre, fiscal_year(d)))
    if b:
        lines.append(f"Budget FY {b.fiscal_year}: allocated {inr(b.allocated)}, spent {inr(b.spent)}.")
    facts = RequestFacts(form.request_id, d, vid, form.vendor_name, amount, form.cost_centre, "", "", "", 0)
    rule = approver_for(facts, md)
    if rule:
        e = md.employees.get(rule.approver_id)
        leave = f"on leave {e.leave_from} to {e.leave_to}" if e and e.leave_from else "no leave recorded"
        lines.append(f"Approver {rule.approver_id} ({leave}).")
        lines += [
            f"Delegation {x.approver_id} -> {x.delegate_id} up to {inr(x.max_amount)}, valid {x.valid_from} "
            f"to {x.valid_to}."
            for x in md.delegations
            if x.approver_id == rule.approver_id
        ]
    lines += [
        f"Earlier request {p.id} to {p.vendor_id} on {p.submitted_on} for {inr(p.amount)}."
        for p in md.prior_requests
        if p.vendor_id == vid and p.id != form.request_id
    ]
    return "\n".join(lines)


async def run_ab(
    arm: str, form: IntakeForm, s: Session, llm: LLM, rag: VectorBackend | None
) -> dict[str, Any]:
    md = master_snapshot(s)
    policy = (ROOT / "data" / "seed" / "policy.md").read_text(encoding="utf-8")
    parts = [
        f"POLICY\n{policy}",
        f"STEP LIBRARY: {', '.join(STEP_CODES)}",
        f"LEDGER EXTRACT\n{ledger_extract(form, md)}",
    ]
    if rag is not None:
        q = f"{form.justification} {form.email_thread}"[:1600]
        r = await rag.recall(q, None)
        parts.append("PAST RESOLVED CASES (retrieved)\n" + "\n\n".join(h.text for h in r.hits))
    parts.append(
        f"REQUEST\njustification: {form.justification}\nemail_thread: {form.email_thread or '(none)'}\n"
        f"attachment_text: {form.attachment_text or '(none)'}"
    )
    r = await llm.call(
        f"arm_{arm.lower()}",
        "\n\n".join(parts),
        ArmAnswer,
        f"arm-{arm.lower()}-v1",
        system=ARM_SYSTEM,
        case_id=form.request_id,
    )
    a = r.parsed
    return {
        "predicted_class": a.case_class,
        "predicted_steps": [x.code for x in a.steps],
        "review_mode": "escalate" if a.escalate else "",
        "flags": [],
        "model": r.model,
    }


# --- the runner ----------------------------------------------------------------------------------


# Stop before a case when the primary model has less than this left: about the dearest arm's (D) measured
# per-case cost on dev (5,345 tokens), rounded up.
CASE_MARGIN_TOKENS = 6000


def quota_check(arm: str, n: int, llm: LLM, force: bool) -> None:
    primary = config("models")["roles"]["verifier"]["model"]
    left = llm.limiter.tokens_remaining_today(primary)
    need = n * REQUESTS_PER_CASE.get(arm, 2) * 2000
    print(f"quota: ~{need} tokens needed for {n} cases; {left} left on {primary} (rolling 24 h)")
    if left is not None and need > left and not force:
        raise SystemExit("refusing: this run would exceed the remaining quota (use --force, or resume later)")


def llm_usage(case_id: str, since: datetime) -> tuple[int, list[str]]:
    with Session(ledger.engine()) as s:
        rows = s.exec(
            select(ledger.LlmCall).where(
                ledger.LlmCall.case_id == case_id, ledger.LlmCall.created_at >= since
            )
        ).all()
        tokens = sum(_cost(s, r) for r in rows)
    return tokens, sorted({r.model for r in rows if not r.error})


def _cost(s: Session, r: ledger.LlmCall) -> int:
    """Tokens a call costs an uncached run. A cache hit replays an earlier output, so it is charged that
    call's tokens: the latest earlier uncached call with the same role, case, model and prompt version (the
    cache itself stores no token counts)."""
    if not r.cache_hit:
        return r.input_tokens + r.output_tokens + r.thinking_tokens
    L = ledger.LlmCall
    o = s.exec(
        select(L)
        .where(
            L.role == r.role,
            L.case_id == r.case_id,
            L.model == r.model,
            L.prompt_version == r.prompt_version,
            L.cache_hit == False,  # noqa: E712
            L.error == "",
            L.created_at < r.created_at,
        )
        .order_by(L.created_at.desc())
    ).first()
    return (o.input_tokens + o.output_tokens + o.thinking_tokens) if o else 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["A", "B", "C", "D"], help="C also writes arm E")
    ap.add_argument("--dataset", default="bench", choices=["gate1", "bench"])
    ap.add_argument("--split", default="dev", choices=["dev", "test", "gate1"])
    ap.add_argument("--only")
    ap.add_argument("--run", help="run id (default: timestamp)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--resume", action="store_true", help="continue --run ID: skip finished cases, keep its bank"
    )
    ap.add_argument(
        "--bank",
        help="reuse an existing seeded bank or store (eval runs never retain, so it still holds exactly the seeds)",
    )
    args = ap.parse_args()
    split = "gate1" if args.dataset == "gate1" else args.split
    master, history, cases, hist_hash = load_dataset(args.dataset, split)
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["request_id"] in keep]
    if args.resume and not args.run:
        raise SystemExit("--resume needs --run ID")
    run_id = args.run or datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS / f"run-{args.dataset}-{split}-{args.arm}-{run_id}.json"
    rows: list[dict[str, Any]] = []
    if args.resume and out_path.exists():
        rows = json.loads(out_path.read_text(encoding="utf-8"))["rows"]
        done = {r["case_id"] for r in rows if r["arm"] == args.arm}
        cases = [c for c in cases if c["request_id"] not in done]
        print(f"resuming {run_id}: {len(done)} cases done, {len(cases)} to go", flush=True)
    llm = LLM()
    quota_check(args.arm, len(cases), llm, args.force)
    primary = config("models")["roles"]["verifier"]["model"]

    def save() -> None:
        RESULTS.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {"run_id": run_id, "arm": args.arm, "dataset": args.dataset, "split": split, "rows": rows},
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    RUNS.mkdir(parents=True, exist_ok=True)
    db = RUNS / f"{args.dataset}-{split}-{args.arm}-{run_id}.db"
    if not args.resume:
        db.unlink(missing_ok=True)
    eng = ledger.engine(f"sqlite:///{db}")

    # Memory per SPEC §8.1. The gate dataset reuses its seeded banks (identical seeding) to save credit.
    backend = None
    rag = None
    if args.arm == "C":
        bank = (
            f"kaveri-gate1-{hist_hash}" if args.dataset == "gate1" else f"kaveri-{split}-C-{run_id}".lower()
        )
        backend = HindsightBackend(args.bank or bank)
    if args.arm in ("B", "D"):
        store = (
            f"kaveri-{args.dataset}-{hist_hash}-vec"
            if args.dataset == "gate1"
            else f"kaveri-{split}-{args.arm}-{run_id}".lower()
        )
        store = args.bank or store
        rag = backend = VectorBackend(store) if args.arm == "D" else None
        if args.arm == "B":
            rag = VectorBackend(store)

    started = datetime.now(UTC)
    with Session(eng) as s:
        if not (args.resume and s.exec(select(ledger.Vendor)).first()):  # a resumed ledger is already loaded
            load_master_json(s, master)
            import_to_ledger(history, s)
        mem = backend if backend is not None else rag
        if mem is not None and args.bank and await mem.bank_exists():
            print(f"reusing {mem.bank_id} (seeded identically; eval runs retain nothing)", flush=True)
        elif mem is not None and not await mem.bank_exists():
            print(f"seeding {mem.bank_id} with {len(history)} records ...", flush=True)
            await mem.ensure_bank()
            await import_to_memory(history, mem, s)
            await mem.wait_consolidated()
        for c in cases:
            form = form_of(c)
            left = llm.limiter.tokens_remaining_today(primary)
            if left is not None and left < CASE_MARGIN_TOKENS:
                print(
                    f"stopping before {form.request_id}: {left} tokens left on {primary}; resume later",
                    flush=True,
                )
                break
            t0 = time.perf_counter()
            per_arm: dict[str, dict[str, Any]] = {}
            try:
                if args.arm in ("A", "B"):
                    per_arm[args.arm] = await run_ab(args.arm, form, s, llm, rag if args.arm == "B" else None)
                else:
                    out = await run_case(form, s, backend, llm, arm=args.arm)
                    comp = out.composition
                    per_arm[args.arm] = {
                        "predicted_class": out.detection.classification.cls,
                        "predicted_steps": [x.code for x in comp.steps]
                        if comp
                        else (["STANDARD_APPROVAL"] if out.detection.classification.cls == "normal" else []),
                        "review_mode": out.review_mode,
                        "flags": (comp.flags if comp else []) + out.detection.flags,
                        "novel_combination": out.detection.classification.novel_combination,
                    }
                    if args.arm == "C" and out.detection.detection is not None:
                        det, r = out.detection.detection, out.detection
                        md = master_snapshot(s)
                        e = await compose(
                            r.extraction.facts,
                            r.violations,
                            det,
                            r.classification,
                            ledger_cases(s),
                            floor_context(r.extraction.facts, r.violations, md),
                            None,
                        )
                        pf = [f for cov in det.coverage for f in cov.flags]
                        per_arm["E"] = {
                            "predicted_class": r.classification.cls,
                            "predicted_steps": [x.code for x in e.steps],
                            "review_mode": review_mode(r.classification, e, pf),
                            "flags": e.flags,
                            "novel_combination": r.classification.novel_combination,
                        }
                    elif args.arm == "C":
                        per_arm["E"] = dict(per_arm["C"])
            except LLMUnavailable as e:
                if "quota" in str(e) or "429" in str(e):
                    print(
                        f"stopping at {form.request_id} on quota ({str(e)[:160]}); resume later", flush=True
                    )
                    break
                per_arm[args.arm] = {
                    "predicted_class": "unknown",
                    "predicted_steps": [],
                    "review_mode": "escalate",
                    "flags": [f"llm_unavailable: {str(e)[:200]}"],
                }
            ms = int((time.perf_counter() - t0) * 1000)
            tokens, models = llm_usage(form.request_id, started)
            for arm, res in per_arm.items():
                row = {
                    "run_id": run_id,
                    "arm": arm,
                    "split": split,
                    "case_id": form.request_id,
                    **res,
                    "tokens": tokens,  # E needs the same extraction and verification calls as C
                    "latency_ms": ms,
                    "models": models,
                }
                rows.append(row)
                s.add(
                    ledger.EvalRun(
                        run_id=run_id,
                        arm=arm,
                        split=split,
                        case_id=form.request_id,
                        predicted_class=res["predicted_class"],
                        predicted_steps=res["predicted_steps"],
                        review_mode=res["review_mode"],
                        flags=res["flags"],
                        tokens=row["tokens"],
                        latency_ms=ms,
                    )
                )
                s.commit()
                print(
                    f"{arm} {form.request_id:<9} {res['predicted_class']:<11} {res['review_mode']:<13} "
                    f"{', '.join(res['predicted_steps'])[:110]}",
                    flush=True,
                )
            save()
    if hasattr(backend, "aclose"):
        await backend.aclose()
    save()
    print(f"wrote {out_path.relative_to(ROOT)} ({len({r['case_id'] for r in rows})} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
