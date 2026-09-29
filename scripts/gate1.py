"""Gate G1 (SPEC §17, `make gate1`): the detector on 15 hand-written borderline cases.

Owns: building the gate's ledger (data/gate1/gate1.db, rebuilt every run) and memory bank, running each case
through pipeline.run_detection, and scoring against data/gate1/expected.json (read only here).
Pass: 0 false confidence; at least 12 of 15 classes correct; every citation resolves to a ledger case ID.
The bank `kaveri-gate1-<hash of history.json>` is reused across runs (retains cost Hindsight credit) unless
--reseed. Never tunes on or reads data/ground_truth/.

Usage: python -m scripts.gate1 [--reseed] [--no-cache] [--only GATE-K1,GATE-U5]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import UTC, datetime

from sqlmodel import Session, select

from api import ledger
from api.engine.extractor import IntakeForm
from api.engine.pipeline import CaseResult, load_master_json, run_case, run_detection
from api.llm import LLM
from api.memory.hindsight_backend import HindsightBackend
from api.settings import IST, ROOT
from scripts.import_history import import_to_ledger, import_to_memory

GATE = ROOT / "data" / "gate1"
RESULTS = ROOT / "eval" / "results"


def bank_id() -> str:
    h = hashlib.sha256((GATE / "history.json").read_bytes()).hexdigest()[:8]
    return f"kaveri-gate1-{h}"


def form_of(c: dict) -> IntakeForm:
    at = datetime.fromisoformat(c["submitted_at"])
    return IntakeForm(**(c | {"submitted_at": at if at.tzinfo else at.replace(tzinfo=IST)}))


def row_for(r: CaseResult, exp: dict) -> dict:
    det = r.detection
    predicted_checks = sorted(v.check for v in r.violations)
    cls = r.classification.cls
    fc = exp["class"] == "unknown" and cls != "unknown" and not r.escalated
    return {
        "case": r.request_id,
        "expected": exp["class"],
        "predicted": cls,
        "correct": cls == exp["class"],
        "false_confidence": fc,
        "checks_expected": sorted(exp["failed_checks"]),
        "checks_found": predicted_checks,
        "checks_match": predicted_checks == sorted(exp["failed_checks"]),
        "novel_expected": exp.get("novel_combination"),
        "novel_predicted": r.classification.novel_combination if cls == "composed" else None,
        "coverage": [
            {
                "check": c.check,
                "status": c.status,
                "cases": c.case_ids,
                "strength": c.strength,
                "differences": c.differences,
                "reason": c.reason,
                "flags": c.flags,
            }
            for c in (det.coverage if det else [])
        ],
        "interaction": (
            {
                "status": det.interaction.status,
                "combo": det.interaction.combo,
                "cases": det.interaction.case_ids,
                "reason": det.interaction.reason,
            }
            if det and det.interaction
            else None
        ),
        "verdicts": (
            {
                k: {"verdict": v.verdict, "guard": v.guard, "reason": v.reason, "differences": v.differences}
                for k, v in det.verdicts.items()
            }
            if det
            else {}
        ),
        "citations_total": det.citations.total if det else 0,
        "citations_resolved": det.citations.resolved if det else 0,
        "unresolved": det.citations.unresolved if det else [],
        "signals": [s.name for s in r.extraction.facts.signals] if r.extraction else [],
        "urgency": r.extraction.facts.urgency if r.extraction else "",
        "category": r.extraction.facts.category if r.extraction else "",
        "amount": r.extraction.facts.amount if r.extraction else None,
        "flags": r.flags,
        "escalated": r.escalated,
        "verifier_model": det.verifier_model if det else "",
        "recall_ms": det.recall_ms if det else [],
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseed", action="store_true", help="delete and re-seed the gate bank")
    ap.add_argument("--no-cache", action="store_true", help="don't reuse cached verifier outputs")
    ap.add_argument("--only", help="comma-separated case IDs")
    ap.add_argument(
        "--compose", choices=["C", "D", "E"], help="also run stage 7 with this arm; print procedures"
    )
    args = ap.parse_args()

    history = json.loads((GATE / "history.json").read_text(encoding="utf-8"))["records"]
    master = json.loads((GATE / "master.json").read_text(encoding="utf-8"))
    cases = json.loads((GATE / "cases.json").read_text(encoding="utf-8"))["cases"]
    expected = json.loads((GATE / "expected.json").read_text(encoding="utf-8"))["cases"]
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["request_id"] in keep]

    db = GATE / "gate1.db"
    ledger._engines.pop(f"sqlite:///{db}", None)
    db.unlink(missing_ok=True)
    eng = ledger.engine(f"sqlite:///{db}")
    backend = HindsightBackend(bank_id())
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    with Session(eng) as s:
        load_master_json(s, master)
        import_to_ledger(history, s)
        exists = await backend.bank_exists()
        if args.reseed and exists:
            await backend.delete_bank()
            exists = False
        if not exists:
            print(f"seeding {backend.bank_id} with {len(history)} records ...", flush=True)
            await backend.ensure_bank()
            await import_to_memory(history, backend, s)
            settled = await backend.wait_consolidated()
            print(f"consolidation settled: {settled}", flush=True)
        else:
            print(f"reusing {backend.bank_id}", flush=True)

        llm = LLM()
        rows = []
        for c in cases:
            outcome = None
            if args.compose:
                outcome = await run_case(
                    form_of(c), s, backend, llm, arm=args.compose, use_cache=not args.no_cache
                )
                r = outcome.detection
            else:
                r = await run_detection(form_of(c), s, backend, llm, use_cache=not args.no_cache)
            row = row_for(r, expected[c["request_id"]])
            rows.append(row)
            mark = "ok " if row["correct"] else "XX "
            print(
                f"{mark}{row['case']:<8} expected {row['expected']:<9} got {row['predicted']:<9} "
                f"checks {','.join(row['checks_found']) or '-':<22} "
                + " ".join(f"{x['check']}={x['status']}" for x in row["coverage"])
                + (f" | interaction {row['interaction']['status']}" if row["interaction"] else "")
                + (f" | ESCALATED {row['escalated'][:60]}" if row["escalated"] else ""),
                flush=True,
            )
            if outcome is not None:
                comp = outcome.composition
                row["review_mode"], row["maturity"] = outcome.review_mode, outcome.maturity
                row["procedure"] = [f"{x.code}[{x.origin}]" for x in comp.steps] if comp else []
                row["composition_flags"] = comp.flags if comp else []
                row["diff"] = comp.diff_text if comp else ""
                print(
                    f"     {outcome.review_mode}/{outcome.maturity or '-'}: {', '.join(row['procedure']) or '-'}"
                )
                if row["diff"]:
                    print(f"     {row['diff'][:300]}")
                if row["composition_flags"]:
                    print(f"     flags: {', '.join(row['composition_flags'])}", flush=True)
    await backend.aclose()

    with Session(ledger.engine()) as s:
        calls = s.exec(select(ledger.LlmCall).where(ledger.LlmCall.created_at >= started)).all()
    tokens = sum(c.input_tokens + c.output_tokens + c.thinking_tokens for c in calls)
    n = len(rows)
    correct = sum(r["correct"] for r in rows)
    fc = [r["case"] for r in rows if r["false_confidence"]]
    cit_total = sum(r["citations_total"] for r in rows)
    cit_ok = sum(r["citations_resolved"] for r in rows)
    checks_ok = sum(r["checks_match"] for r in rows)
    composed = [r for r in rows if r["expected"] == "composed" and r["predicted"] == "composed"]
    novel_ok = sum(r["novel_predicted"] == r["novel_expected"] for r in composed)
    passed = not fc and correct >= (12 if n == 15 else n) and cit_ok == cit_total

    print()
    print(f"False confidence: {len(fc)} of {n}" + (f" ({', '.join(fc)})" if fc else ""))
    print(f"Classes correct: {correct} of {n}")
    print(f"Citations resolved to ledger case IDs: {cit_ok} of {cit_total}")
    print(f"Failed checks found exactly: {checks_ok} of {n}")
    print(f"Novel-combination flag right on composed cases: {novel_ok} of {len(composed)}")
    print(
        f"LLM calls: {len([c for c in calls if not c.cache_hit])} (+{len([c for c in calls if c.cache_hit])} cached), "
        f"tokens {tokens}; wall time {time.perf_counter() - t0:.0f} s"
    )
    print(f"GATE G1: {'PASS' if passed else 'FAIL'}" + ("" if n == 15 else f" (partial run: {n} cases)"))

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"gate1-{started:%Y%m%dT%H%M%S}.json"
    out.write_text(
        json.dumps(
            {
                "bank": backend.bank_id,
                "started": started.isoformat(),
                "passed": passed,
                "summary": {
                    "false_confidence": len(fc),
                    "classes_correct": correct,
                    "cases": n,
                    "citations_resolved": cit_ok,
                    "citations_total": cit_total,
                    "checks_exact": checks_ok,
                    "novel_flag_correct": novel_ok,
                    "composed_cases": len(composed),
                    "tokens": tokens,
                },
                "cases": rows,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
