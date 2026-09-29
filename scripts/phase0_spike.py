"""Phase 0 spike: verifies every Hindsight and Gemini call we plan to use, against the live services.

Owns: recording fixtures (tests/fixtures/) and measurements (docs/phase0_results.json).
Never: touches the demo or benchmark banks (it creates scratch banks `kaveri-spike-*` and deletes them
unless --keep), reads ground truth, or sends anything but synthetic data.

Usage: python -m scripts.phase0_spike [--part gemini|hindsight|all] [--keep]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlmodel import Session, select

from api import ledger
from api.llm import LLM, LLMUnavailable, gemini_schema
from api.memory.hindsight_backend import make_client
from api.settings import ROOT, config

FIX = ROOT / "tests" / "fixtures"
RESULTS = ROOT / "docs" / "phase0_results.json"

STEP_CODES = list(config("step_library")["steps"])
StepCode = Literal[tuple(STEP_CODES)]  # type: ignore[valid-type]


def dump(obj: Any) -> Any:
    """JSON-safe form of an SDK response (generated pydantic models or plain values)."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", by_alias=True, exclude_none=True)
    return json.loads(json.dumps(obj, default=str))


def save(rel: str, obj: Any) -> None:
    path = FIX / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dump(obj), indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# --- synthetic seeds (SPEC §8.3 template). Spike-only; the real seed set is built in Phase 2. -----

SEEDS: list[dict[str, Any]] = [
    dict(
        case_id="PR-2026-0233",
        kind="experience",
        checks=["bank"],
        resolved="2026-02-20",
        vendor="V-031",
        approver="E-104",
        reviewer="R. Menon",
        outcome="callback confirmed; PO released",
        codes=["VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "HOLD_PO"],
        why="the bank check only flags the change; it says nothing about whether the change is genuine",
        body="""Failed checks: bank (cause: bank_changed_recently).
Request: ₹3,20,000 direct material, forged steel blanks, vendor V-031 (supplier for 4 years).
What happened: vendor V-031 changed its bank account 9 days before the request, by email.
Why the standard process did not fit: the bank check only flags the change; it says nothing about whether the change is genuine, and a changed account is a classic payment-fraud route.
Steps approved (codes): VERIFY_BANK_CALLBACK, HOLD_PAYMENT, HOLD_PO.
Outcome: callback to the number on file confirmed the new account; PO released after 2 days.
Lesson: a recent bank change means a callback on a known number and a payment hold before anything else.""",
    ),
    dict(
        case_id="PR-2026-0301",
        kind="experience",
        checks=["approver"],
        resolved="2026-03-05",
        vendor="V-008",
        approver="E-104",
        reviewer="R. Menon",
        outcome="delegate approved same day",
        codes=["ROUTE_DELEGATE"],
        why="the approver was on leave and the request would otherwise wait eight days",
        body="""Failed checks: approver (cause: approver_on_leave).
Request: ₹1,10,000 indirect MRO, spindle bearings, vendor V-008, cost centre CC-MACH.
What happened: approver E-104 was on leave until 13 Mar; delegate E-112 holds a valid delegation up to ₹2,00,000.
Why the standard process did not fit: the approver was on leave and the request would otherwise wait eight days.
Steps approved (codes): ROUTE_DELEGATE.
Outcome: delegate E-112 approved the same day.
Lesson: when the approver is away and the amount is within the delegate's limit, route to the delegate.""",
    ),
    dict(
        case_id="PR-2026-0312",
        kind="interaction",
        checks=["bank", "budget"],
        resolved="2026-03-11",
        vendor="V-031",
        approver="E-104",
        reviewer="R. Menon",
        outcome="line restarted; payment released after callback",
        codes=[
            "EXPEDITE_PO",
            "VERIFY_BANK_CALLBACK",
            "HOLD_PAYMENT",
            "ALLOW_BUDGET_OVERRUN",
            "ATTACH_LINE_DOWN_EVIDENCE",
            "ADD_CONTROLLER_SIGNOFF",
        ],
        why="holding the PO for the bank callback would have kept line 3 down; a PO is not a payment",
        body="""Failed checks: bank (cause: bank_changed_recently) + budget (cause: overrun 7%).
Request: ₹4,10,000 direct material, coolant pump assemblies, vendor V-031, urgency line_down (line 3 stopped).
What happened: V-031 changed bank details 12 days earlier and cost centre CC-MACH was 7% over budget.
Why the standard process did not fit: the plain combination holds the PO until the bank callback, which would have kept line 3 down; a PO is not a payment.
Plain combination would have been: VERIFY_BANK_CALLBACK, HOLD_PAYMENT, HOLD_PO, ALLOW_BUDGET_OVERRUN, ATTACH_LINE_DOWN_EVIDENCE, ADD_CONTROLLER_SIGNOFF, EXPEDITE_PO.
Steps approved (codes): EXPEDITE_PO, VERIFY_BANK_CALLBACK, HOLD_PAYMENT, ALLOW_BUDGET_OVERRUN, ATTACH_LINE_DOWN_EVIDENCE, ADD_CONTROLLER_SIGNOFF.
Removed from the plain combination: HOLD_PO, because the PO was released while payment stayed held until the callback.
Outcome: parts arrived next day; callback confirmed the account; payment released after controller sign-off.
Lesson: when a bank change meets a line-down overrun, release the PO but hold the payment until the callback.""",
    ),
    dict(
        case_id="PR-2026-0417",
        kind="experience",
        checks=["vendor"],
        resolved="2026-03-14",
        vendor="V-017",
        approver="E-107",
        reviewer="R. Menon",
        outcome="renewed certificate received in 3 days; PO released",
        codes=["REQUEST_RENEWED_CERT", "KEEP_VENDOR_ACTIVE", "HOLD_PO"],
        why="the vendor check blocks the vendor outright, but the vendor was otherwise in good standing",
        body="""Failed checks: vendor (cause: cert_expired).
Request: ₹1,40,000 direct material, bearing housings, vendor V-017 (in good standing, 2 years on-time delivery).
What happened: ISO 9001 certificate expired 6 days before the request.
Why the standard process did not fit: the vendor check blocks the vendor outright, but the vendor was otherwise in good standing and renewal was in progress.
Steps approved (codes): REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, HOLD_PO.
Outcome: renewed certificate received in 3 days; PO released.
Lesson: a recently expired certificate is a hold, not a rejection, when the vendor is otherwise in good standing.""",
    ),
    dict(
        case_id="PR-2026-0488",
        kind="experience",
        checks=["vendor"],
        resolved="2026-04-02",
        vendor="V-023",
        approver="E-109",
        reviewer="R. Menon",
        outcome="renewed certificate received in 5 days; PO released",
        codes=["REQUEST_RENEWED_CERT", "KEEP_VENDOR_ACTIVE", "HOLD_PO"],
        why="blocking the vendor would have cut off the only calibrated gauge supplier nearby",
        body="""Failed checks: vendor (cause: cert_expired).
Request: ₹85,000 indirect MRO, calibrated bore gauges, vendor V-023 (in good standing, no quality incidents).
What happened: ISO/IEC 17025 calibration certificate expired 3 days before the request; the renewal audit was already booked.
Why the standard process did not fit: blocking the vendor would have cut off the only calibrated gauge supplier nearby, and the lapse was administrative.
Steps approved (codes): REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, HOLD_PO.
Outcome: renewed certificate received in 5 days; PO released.
Lesson: a recently expired certificate is a hold, not a rejection, when the vendor is otherwise in good standing.""",
    ),
]


def seed_content(s: dict[str, Any]) -> str:
    d = datetime.fromisoformat(s["resolved"]).strftime("%d %b %Y")
    return (
        f"SYNTHETIC DATA. Case {s['case_id']}, resolved {d} by {s['reviewer']} (Procurement Ops). "
        f"Kind: {s['kind']}.\n{s['body']}"
    )


def seed_tags(s: dict[str, Any]) -> list[str]:
    if s["kind"] == "interaction":
        return ["interaction", "combo:" + "+".join(sorted(s["checks"]))]
    return [f"step:{c}" for c in s["checks"]]


def seed_item(s: dict[str, Any], scopes: str | None) -> dict[str, Any]:
    item = {
        "content": seed_content(s),
        "timestamp": datetime.fromisoformat(s["resolved"] + "T12:00:00+05:30"),
        "context": "procurement exception resolution",
        "document_id": s["case_id"],
        "metadata": {
            "case_id": s["case_id"],
            "kind": s["kind"],
            "outcome": s["outcome"],
            "reviewer": s["reviewer"],
            "combo": "+".join(sorted(s["checks"])),
            "overrides": "",
        },
        "entities": [{"text": s["vendor"], "type": "vendor"}, {"text": s["approver"], "type": "approver"}],
        "resolve_entities": False,
        "tags": seed_tags(s),
    }
    if scopes:
        item["observation_scopes"] = scopes
    return item


MISSIONS = dict(
    retain_mission=(
        "Extract how procurement exceptions at Kaveri were resolved: which standard check failed and why, "
        "why the standard process did not fit, the exact step codes the human approved, the outcome, and the "
        "lesson. Keep case IDs, vendor IDs, dates and rupee amounts exact."
    ),
    observations_mission=(
        "Form one durable lesson per failed check, and one per combination of failed checks, stating when the "
        "exception applies, the procedure as step codes, the supporting case IDs, and any override or policy "
        "change that limits it."
    ),
    reflect_mission=(
        "I help Kaveri's procurement analysts handle purchase requests that break the standard process. I apply "
        "lessons from past exceptions cautiously, cite the case behind every step, and say when no lesson applies."
    ),
)
DIRECTIVES = [
    ("cite-cases", "Cite the case ID behind every step."),
    ("no-payment-release", "Never recommend releasing a payment. Propose only steps for a human to approve."),
    (
        "bank-change-floor",
        "Whenever vendor bank details changed recently or are claimed to have changed, include "
        "VERIFY_BANK_CALLBACK and HOLD_PAYMENT.",
    ),
    ("say-unknown", "If no experience covers a condition, say so explicitly."),
    (
        "prefer-post-policy",
        "Prefer lessons dated after any relevant policy change; flag any lesson that predates one.",
    ),
]


# --- schemas (shapes the real ones will take; spike versions) -----------------------------------


class SpikeCandidateVerdict(BaseModel):
    candidate_id: str
    verdict: Literal["yes", "partial", "no"]
    differences: list[str]
    reason: str


class SpikeVerifierOut(BaseModel):
    verdicts: list[SpikeCandidateVerdict]


class ProcStep(BaseModel):
    code: StepCode
    reason: str
    cited_case_ids: list[str]


class Procedure(BaseModel):
    steps: list[ProcStep]
    removed_from_union: list[ProcStep]
    open_questions: list[str]


VERIFY_PROMPT = """SYNTHETIC DATA. You verify whether past procurement exception precedents apply to a new request.
Verdicts: yes = same failed check, same cause, conditions hold, same amount band (up to 2L, 2-10L, over 10L) and category.
partial = same check and cause but different band/category or an unconfirmed condition; list the differences.
no = different cause, contradicted condition, overridden, or superseded by a policy memo.

New request: Rs 60,000 indirect MRO, vendor V-044 (in good standing), ISO 9001 certificate expired 6 days ago.
Failed check: vendor (cause: cert_expired).

Candidates:
C1 (case PR-2026-0417): Rs 1,40,000 direct material; ISO 9001 expired 6 days before; vendor in good standing; steps REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, HOLD_PO.
C2 (case PR-2026-0233): bank details changed 9 days before; steps VERIFY_BANK_CALLBACK, HOLD_PAYMENT, HOLD_PO.

Return one verdict per candidate."""


# --- Gemini ------------------------------------------------------------------------------------


async def gemini_part(out: dict[str, Any]) -> None:
    llm = LLM()
    models = llm.list_models()
    save("gemini/models_list.json", models)
    names = {m["name"] for m in models}
    cfg = config("models")
    out["gemini_models"] = {
        m: {"listed": f"models/{m}" in names, **next((x for x in models if x["name"] == f"models/{m}"), {})}
        for m in (cfg["primary"], cfg["fallback"])
    }
    out["gemini_schema_verifier"] = gemini_schema(SpikeVerifierOut)
    out["gemini_schema_procedure_ok"] = bool(gemini_schema(Procedure))

    runs = [
        ("generate_content", "spike", None),
        ("interactions", "spike", None),
        ("generate_content", "verifier", None),  # thinking medium (verifier default)
        ("generate_content", "spike", cfg["fallback"]),  # fallback model direct
    ]
    results = []
    for style, role, model_override in runs:
        c = json.loads(json.dumps(cfg))
        if model_override:
            c["roles"][role]["model"] = model_override
        runner = LLM(client=llm.client, models_cfg=c)
        label = f"{style}/{role}/{model_override or c['roles'][role]['model']}"
        t0 = time.perf_counter()
        try:
            r = await runner.call(
                role, VERIFY_PROMPT, SpikeVerifierOut, "spike-v1", call_style=style, case_id="SPIKE"
            )
            results.append(
                dict(
                    label=label,
                    ok=True,
                    model=r.model,
                    latency_ms=r.latency_ms,
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                    thinking_tokens=r.thinking_tokens,
                    parsed=r.parsed.model_dump(),
                )
            )
            save(f"gemini/{style}_{role}_{r.model}.json", {"raw": r.raw, "parsed": r.parsed.model_dump()})
        except LLMUnavailable as e:
            results.append(
                dict(label=label, ok=False, error=str(e), wall_ms=int((time.perf_counter() - t0) * 1000))
            )
        print("gemini", label, "ok" if results[-1]["ok"] else results[-1]["error"])
        await asyncio.sleep(15)  # spike pacing only; limits.yaml holds the real RPM once supplied
    out["gemini_calls"] = results

    # extraction cache check: the second identical call must be a cache hit and cost no request
    before = llm.limiter.requests_today(cfg["primary"])
    r1 = await llm.call("spike", VERIFY_PROMPT, SpikeVerifierOut, "spike-cache-v1", cache_key="SPIKE-CACHE")
    r2 = await llm.call("spike", VERIFY_PROMPT, SpikeVerifierOut, "spike-cache-v1", cache_key="SPIKE-CACHE")
    out["gemini_cache"] = {
        "first_hit": r1.cache_hit,
        "second_hit": r2.cache_hit,
        "requests_used": llm.limiter.requests_today(cfg["primary"]) - before,
    }

    with Session(ledger.engine()) as s:
        rows = s.exec(select(ledger.LlmCall).where(ledger.LlmCall.case_id.in_(["SPIKE", ""]))).all()
        out["gemini_llm_calls_logged"] = len(rows)


# --- Hindsight ----------------------------------------------------------------------------------


async def wait_consolidation(hs, bank: str, t_start: float, limit_s: float = 900) -> dict[str, Any]:
    """Poll consolidation operations and observation count until settled."""
    polls, delay = [], 2.0
    first_obs_at = None
    while True:
        elapsed = time.perf_counter() - t_start
        ops = await hs.operations.list_operations(bank, type="consolidation")
        od = dump(ops)
        items = od.get("operations") or od.get("items") or []
        pending = [o for o in items if o.get("status") in ("pending", "processing")]
        obs = await hs.alist_memories(bank, type="observation", limit=100)
        n_obs = len(dump(obs).get("items", []))
        if n_obs and first_obs_at is None:
            first_obs_at = elapsed
        polls.append(
            {
                "t": round(elapsed, 1),
                "consolidation_ops": len(items),
                "pending": len(pending),
                "observations": n_obs,
            }
        )
        if items and not pending and n_obs:
            return {
                "settled_s": round(elapsed, 1),
                "first_observation_s": first_obs_at,
                "polls": polls,
                "operations": items,
            }
        if elapsed > limit_s:
            return {
                "settled_s": None,
                "timed_out_after_s": limit_s,
                "first_observation_s": first_obs_at,
                "polls": polls,
                "operations": items,
            }
        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 20)


def fact_quality(memories: list[dict[str, Any]]) -> dict[str, Any]:
    """Per seed: do the extracted facts keep every step code and the 'why it didn't fit' reason?"""
    per = {}
    for s in SEEDS:
        facts = [m for m in memories if m.get("document_id") == s["case_id"]]
        text = " ".join(m.get("text", "") for m in facts)
        codes_kept = [c for c in s["codes"] if c in text]
        why_words = {w for w in s["why"].lower().replace(",", " ").replace(";", " ").split() if len(w) > 4}
        hit = {w for w in why_words if w in text.lower()}
        per[s["case_id"]] = {
            "facts": len(facts),
            "codes_kept": f"{len(codes_kept)} of {len(s['codes'])}",
            "all_codes_kept": len(codes_kept) == len(s["codes"]),
            "why_keyword_overlap": f"{len(hit)} of {len(why_words)}",
            "fact_texts": [m.get("text") for m in facts],
        }
    return per


async def hindsight_part(out: dict[str, Any], keep: bool) -> None:
    hs = make_client()
    run = uuid.uuid4().hex[:6]
    out["hindsight_version"] = dump(await hs.aget_version())
    hs_calls: dict[str, int] = {}

    def count(op: str) -> None:
        hs_calls[op] = hs_calls.get(op, 0) + 1

    banks = {}
    for mode in ("concise", "verbose"):
        bank = f"kaveri-spike-{mode}-{run}"
        banks[mode] = bank
        t0 = time.perf_counter()
        await hs.acreate_bank(bank, retain_extraction_mode=mode, **MISSIONS)
        count("create_bank")
        cfg = await hs.aupdate_bank_config(
            bank,
            disposition_skepticism=5,
            disposition_literalism=4,
            disposition_empathy=2,
            enable_auto_consolidation=True,
            enable_observations=True,
        )
        count("update_bank_config")
        resolved = await hs.aget_bank_config(bank)
        count("get_bank_config")
        save(f"hindsight/bank_config_{mode}.json", resolved)
        out.setdefault("bank_setup_ms", {})[mode] = int((time.perf_counter() - t0) * 1000)
        conf = resolved.get("config", {})
        out.setdefault("bank_config_checks", {})[mode] = {
            k: conf.get(k)
            for k in (
                "retain_extraction_mode",
                "disposition_skepticism",
                "disposition_literalism",
                "disposition_empathy",
                "enable_auto_consolidation",
                "enable_observations",
            )
        }
        out["bank_config_llm_keys"] = sorted(
            k for k in conf if "llm" in k.lower() or "model" in k.lower() or "provider" in k.lower()
        )
        out["bank_config_all_keys"] = sorted(conf)
        _ = cfg

        for i, (name, text) in enumerate(DIRECTIVES):
            d = await hs.acreate_directive(bank, name=name, content=text, priority=10 - i)
            count("create_directive")
            if mode == "concise" and i == 0:
                save("hindsight/directive_create.json", d)
        save(f"hindsight/directives_{mode}.json", await hs.alist_directives(bank))
        count("list_directives")

    # Retain the 5 seeds in both banks (per_tag observation scopes), one call per seed to time it.
    retain_stats: dict[str, list[dict[str, Any]]] = {}
    t_last: dict[str, float] = {}
    for mode, bank in banks.items():
        for s in SEEDS:
            t0 = time.perf_counter()
            r = await hs.aretain_batch(bank, [seed_item(s, "per_tag")])
            count("retain")
            ms = int((time.perf_counter() - t0) * 1000)
            rd = dump(r)
            retain_stats.setdefault(mode, []).append(
                {"case_id": s["case_id"], "ms": ms, "usage": rd.get("usage")}
            )
            if mode == "concise" and s["case_id"] == "PR-2026-0417":
                save("hindsight/retain_response.json", rd)
        t_last[mode] = time.perf_counter()
        print("retained", mode)
    out["retain"] = retain_stats

    # Consolidation delay (measured from the last retain returning).
    out["consolidation"] = {}
    for mode, bank in banks.items():
        c = await wait_consolidation(hs, bank, t_last[mode])
        out["consolidation"][mode] = {k: v for k, v in c.items() if k != "operations"}
        save(f"hindsight/consolidation_ops_{mode}.json", c["operations"])
        print("consolidation", mode, c.get("settled_s"))

    # Extraction-mode comparison on the raw facts.
    out["extraction_mode"] = {}
    for mode, bank in banks.items():
        mems = dump(await hs.alist_memories(bank, limit=200))
        count("list_memories")
        save(f"hindsight/list_memories_{mode}.json", mems)
        out["extraction_mode"][mode] = fact_quality(
            [m for m in mems.get("items", []) if m.get("fact_type", m.get("type")) != "observation"]
        )

    bank = banks["concise"]
    q_ts = "2026-09-20T10:00:00+05:30"

    # Per-violation recall (SPEC §8.4).
    t0 = time.perf_counter()
    rec = await hs.arecall(
        bank,
        "vendor check failed (cert_expired): ISO 9001 certificate expired 6 days ago. Rs 60,000 indirect "
        "MRO order from vendor V-044, otherwise in good standing.",
        types=["experience", "observation", "world"],
        prefer_observations=True,
        include_source_facts=True,
        budget="mid",
        max_tokens=2048,
        tags=["step:vendor"],
        tags_match="any_strict",
        query_timestamp=q_ts,
    )
    count("recall")
    out["recall_violation_ms"] = int((time.perf_counter() - t0) * 1000)
    save("hindsight/recall_violation_vendor.json", rec)
    rd = dump(rec)
    out["recall_violation_summary"] = [
        {
            "type": r.get("type"),
            "document_id": r.get("document_id"),
            "tags": r.get("tags"),
            "source_fact_ids": r.get("source_fact_ids"),
            "metadata": r.get("metadata"),
        }
        for r in rd.get("results", [])
    ]
    sf = rd.get("source_facts") or {}
    out["recall_source_facts_docs"] = {k: v.get("document_id") for k, v in sf.items()}

    # Tag isolation: the bank-change recall must not return step:vendor or interaction memories.
    rec_bank = dump(
        await hs.arecall(
            bank,
            "bank check failed: vendor changed bank account last week",
            types=["experience", "observation"],
            tags=["step:bank"],
            tags_match="any_strict",
            include_source_facts=True,
            budget="mid",
            max_tokens=2048,
        )
    )
    count("recall")
    save("hindsight/recall_violation_bank.json", rec_bank)
    out["recall_bank_tags_seen"] = sorted(
        {t for r in rec_bank.get("results", []) for t in (r.get("tags") or [])}
    )

    # Interaction recall.
    t0 = time.perf_counter()
    rec_i = await hs.arecall(
        bank,
        "bank details changed and budget overrun at the same time, production line down",
        types=["experience", "observation"],
        tags=["interaction"],
        tags_match="any_strict",
        include_source_facts=True,
        budget="mid",
        max_tokens=2048,
        query_timestamp=q_ts,
    )
    count("recall")
    out["recall_interaction_ms"] = int((time.perf_counter() - t0) * 1000)
    save("hindsight/recall_interaction.json", rec_i)

    # Observation-only recall per tag (snapshot path, SPEC §8.9).
    rec_o = await hs.arecall(
        bank,
        "lesson for expired vendor certificate",
        types=["observation"],
        tags=["step:vendor"],
        tags_match="any_strict",
        include_source_facts=True,
    )
    count("recall")
    save("hindsight/recall_observations_vendor.json", rec_o)
    obs_ids = [r.id for r in rec_o.results]
    out["observations_step_vendor"] = len(obs_ids)
    if obs_ids:
        hist = await hs.memory.get_observation_history(bank, obs_ids[0])
        count("get_observation_history")
        save("hindsight/observation_history.json", hist)
        out["observation_history_ok"] = True
    scopes = await hs.memory.list_observation_scopes(bank)
    count("list_observation_scopes")
    save("hindsight/observation_scopes.json", scopes)
    out["observation_scopes"] = dump(scopes)

    # Reflect with a response schema (SPEC §8.5), facts via include_facts.
    reflect_q = (
        "SYNTHETIC DATA. New request: Rs 4,80,000 direct material, line 3 down, vendor V-031 changed bank details "
        "12 days ago, cost centre 6% over budget. Failed checks: bank, budget. Plain union U: VERIFY_BANK_CALLBACK "
        "(PR-2026-0233), HOLD_PAYMENT (PR-2026-0233), HOLD_PO (PR-2026-0233). Interaction precedent candidates are "
        "in memory under tag interaction. Start from U. Apply each interaction precedent's changes. Give a reason "
        "and a cited case ID for every step, and for every step you remove from U."
    )
    reflect_tags = ["step:bank", "step:budget", "interaction", "combo:bank+budget"]
    schema = Procedure.model_json_schema()
    out["reflect"] = []
    for budget in ("low", "mid"):
        t0 = time.perf_counter()
        try:
            rf = await hs.areflect(
                bank,
                reflect_q,
                budget=budget,
                response_schema=schema,
                tags=reflect_tags,
                tags_match="any",
                include_facts=True,
                max_tokens=4096,
            )
            count("reflect")
            ms = int((time.perf_counter() - t0) * 1000)
            rfd = dump(rf)
            save(f"hindsight/reflect_{budget}.json", rfd)
            so = rfd.get("structured_output")
            valid = None
            if so is not None:
                try:
                    Procedure.model_validate(so)
                    valid = True
                except Exception as e:  # noqa: BLE001
                    valid = f"invalid: {str(e)[:200]}"
            out["reflect"].append(
                {
                    "budget": budget,
                    "ms": ms,
                    "structured_output_present": so is not None,
                    "structured_output_valid": valid,
                    "structured_output_error": rfd.get("structured_output_error"),
                    "usage": rfd.get("usage"),
                    "based_on_memories": len((rfd.get("based_on") or {}).get("memories") or []),
                    "based_on_directives": len((rfd.get("based_on") or {}).get("directives") or []),
                }
            )
        except Exception as e:  # noqa: BLE001
            out["reflect"].append(
                {
                    "budget": budget,
                    "error": f"{type(e).__name__}: {str(e)[:300]}",
                    "ms": int((time.perf_counter() - t0) * 1000),
                }
            )
        print("reflect", budget, out["reflect"][-1].get("ms"))

    out["hindsight_calls"] = hs_calls
    if keep:
        out["scratch_banks_kept"] = list(banks.values())
    else:
        for b in banks.values():
            await hs.adelete_bank(b)
        out["scratch_banks_deleted"] = list(banks.values())
    await hs.aclose()


def big_verify_prompt(n_candidates: int = 15) -> str:
    """Verifier prompt at a realistic per-case size: 3 violations x 5 candidates."""
    blocks = []
    for i in range(n_candidates):
        blocks.append(
            f"C{i + 1} (case PR-2026-{300 + i:04d}, violation {i // 5 + 1}): Rs {1 + i % 7},{20 + i}0,000 "
            f"{'direct material' if i % 2 else 'indirect MRO'}; vendor V-0{10 + i} in good standing; "
            "certificate expired 4 days before; renewal booked; steps REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, "
            "HOLD_PO; resolved by R. Menon; outcome: renewed certificate received, PO released."
        )
    return (
        VERIFY_PROMPT.split("Candidates:")[0]
        + "Candidates:\n"
        + "\n".join(blocks)
        + "\n\nReturn one verdict per candidate."
    )


async def groq_part(out: dict[str, Any]) -> None:
    """Groq gpt-oss-120b: models, strict structured output, reasoning effort, headers, TPM behaviour."""
    import os

    import httpx

    from api.llm import GROQ_URL, strict_schema

    llm = LLM()
    model = config("models")["roles"]["spike"]["model"]
    models = llm.list_groq_models()
    save("groq/models_list.json", models)
    out["groq_model"] = next((m for m in models if m["id"] == model), None)
    print("groq model listed:", bool(out["groq_model"]))

    # One raw request to record the full response shape and the rate-limit headers.
    key = os.environ["GROQ_API_KEY"]
    body = {
        "model": model,
        "messages": [{"role": "user", "content": VERIFY_PROMPT}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "output",
                "strict": True,
                "schema": strict_schema(gemini_schema(SpikeVerifierOut)),
            },
        },
        "reasoning_effort": "low",
        "max_completion_tokens": 4096,
    }
    raw_runs = []
    for label, extra in (("default", {}), ("include_reasoning_false", {"include_reasoning": False})):
        async with httpx.AsyncClient(timeout=120) as http:
            t0 = time.perf_counter()
            r = await http.post(
                f"{GROQ_URL}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body | extra
            )
        hdr = {k: v for k, v in r.headers.items() if k.lower().startswith(("x-ratelimit", "retry", "x-groq"))}
        payload = r.json()
        save(f"groq/chat_raw_{label}.json", {"status": r.status_code, "headers": hdr, "body": payload})
        msg = (payload.get("choices") or [{}])[0].get("message") or {}
        raw_runs.append(
            {
                "label": label,
                "status": r.status_code,
                "ms": int((time.perf_counter() - t0) * 1000),
                "headers": hdr,
                "usage": payload.get("usage"),
                "message_keys": sorted(msg),
                "error": payload.get("error"),
            }
        )
        print("groq raw", label, r.status_code)
        await asyncio.sleep(3)
    out["groq_raw"] = raw_runs

    # Does a max_completion_tokens above the 8,000 TPM get refused?
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(
            f"{GROQ_URL}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=body | {"max_completion_tokens": 9000},
        )
    out["groq_max_completion_9000"] = {"status": r.status_code, "body": r.text[:600]}
    print("groq max_completion 9000:", r.status_code)

    # Through llm.py: small prompt at low and medium, and a realistic per-case verifier prompt.
    runs = [
        ("spike", VERIFY_PROMPT, "small"),
        ("verifier", VERIFY_PROMPT, "small"),
        ("spike", big_verify_prompt(), "15 candidates"),
        ("verifier", big_verify_prompt(), "15 candidates"),
    ]
    results = []
    for role, prompt, size in runs:
        try:
            res = await llm.call(role, prompt, SpikeVerifierOut, "spike-groq-v1", case_id="SPIKE-GROQ")
            results.append(
                {
                    "role": role,
                    "effort": config("models")["roles"][role]["effort"],
                    "size": size,
                    "ok": True,
                    "model": res.model,
                    "ms": res.latency_ms,
                    "in": res.input_tokens,
                    "out": res.output_tokens,
                    "reasoning": res.thinking_tokens,
                    "verdicts": [(v.candidate_id, v.verdict) for v in res.parsed.verdicts][:4],
                    "n_verdicts": len(res.parsed.verdicts),
                }
            )
            save(f"groq/{role}_{size.replace(' ', '_')}.json", {"raw": res.raw})
        except LLMUnavailable as e:
            results.append({"role": role, "size": size, "ok": False, "error": str(e)})
        print("groq", role, size, results[-1].get("ok"), results[-1].get("ms"))
    out["groq_calls"] = results


NEW_E1 = dict(
    case_id="PR-2026-0520",
    kind="experience",
    checks=["vendor"],
    resolved="2026-04-20",
    vendor="V-029",
    approver="E-107",
    reviewer="R. Menon",
    outcome="renewed certificate in 4 days",
    codes=["REQUEST_RENEWED_CERT", "KEEP_VENDOR_ACTIVE", "HOLD_PO"],
    why="the vendor was otherwise in good standing",
    body="""Failed checks: vendor (cause: cert_expired).
Request: ₹2,40,000 direct material, turned shafts, vendor V-029 (in good standing, 3 years on-time delivery).
What happened: IATF 16949 certificate expired 9 days before the request; surveillance audit completed, certificate awaited.
Why the standard process did not fit: the vendor check blocks the vendor outright, but the vendor was otherwise in good standing.
Steps approved (codes): REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, HOLD_PO.
Outcome: renewed certificate received in 4 days; PO released.
Lesson: a recently expired certificate is a hold, not a rejection, when the vendor is otherwise in good standing.""",
)


async def observation_docs(hs, bank: str, tag: str) -> list[dict[str, Any]]:
    rec = dump(
        await hs.arecall(
            bank,
            f"lesson for {tag}",
            types=["observation"],
            tags=[tag],
            tags_match="any_strict",
            include_source_facts=True,
            max_source_facts_tokens=-1,
        )
    )
    sf = rec.get("source_facts") or {}
    return [
        {
            "id": r["id"],
            "text": r["text"],
            "cases": sorted(
                {(sf.get(i) or {}).get("document_id") for i in r.get("source_fact_ids") or []} - {None}
            ),
        }
        for r in rec.get("results", [])
    ]


async def followup_part(out: dict[str, Any], bank: str, keep: bool) -> None:
    """Reflect with the inlined schema; clean consolidation timing on one retain; observation revision."""
    hs = make_client()
    fu: dict[str, Any] = {"bank": bank}

    reflect_q = (
        "SYNTHETIC DATA. New request: Rs 4,80,000 direct material, line 3 down, vendor V-031 changed bank details "
        "12 days ago, cost centre 6% over budget. Failed checks: bank, budget. Plain union U: VERIFY_BANK_CALLBACK "
        "(PR-2026-0233), HOLD_PAYMENT (PR-2026-0233), HOLD_PO (PR-2026-0233). Start from U. Apply each interaction "
        "precedent's changes. Give a reason and a cited case ID for every step, and for every step you remove from U."
    )
    t0 = time.perf_counter()
    rf = dump(
        await hs.areflect(
            bank,
            reflect_q,
            budget="low",
            response_schema=gemini_schema(Procedure),
            tags=["step:bank", "step:budget", "interaction", "combo:bank+budget"],
            tags_match="any",
            include_facts=True,
            max_tokens=4096,
        )
    )
    save("hindsight/reflect_inlined_schema.json", rf)
    so = rf.get("structured_output")
    try:
        Procedure.model_validate(so)
        valid: Any = True
    except Exception as e:  # noqa: BLE001
        valid = f"invalid: {str(e)[:300]}"
    fu["reflect_inlined"] = {
        "ms": int((time.perf_counter() - t0) * 1000),
        "valid": valid,
        "structured_output_error": rf.get("structured_output_error"),
        "usage": rf.get("usage"),
    }
    print("reflect inlined valid:", valid)

    before = await observation_docs(hs, bank, "step:vendor")
    fu["observation_before"] = before
    t0 = time.perf_counter()
    r = dump(await hs.aretain_batch(bank, [seed_item(NEW_E1, "per_tag")]))
    retain_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    polls = []
    after = before
    while time.perf_counter() - t1 < 600:
        after = await observation_docs(hs, bank, "step:vendor")
        ops = dump(await hs.operations.list_operations(bank, type="consolidation", status="pending"))
        pending = len(ops.get("operations") or ops.get("items") or [])
        el = round(time.perf_counter() - t1, 1)
        polls.append({"t": el, "pending": pending, "cases": [o["cases"] for o in after]})
        if any(NEW_E1["case_id"] in o["cases"] for o in after):
            break
        await asyncio.sleep(1.0)
    fu["revision"] = {
        "retain_ms": retain_ms,
        "retain_usage": r.get("usage"),
        "observation_includes_new_case_after_s": polls[-1]["t"]
        if any(NEW_E1["case_id"] in o["cases"] for o in after)
        else None,
        "polls": polls,
        "observation_after": after,
        "same_observation_id": bool(before and after and before[0]["id"] == after[0]["id"]),
    }
    if after:
        hist = await hs.memory.get_observation_history(bank, after[0]["id"])
        save("hindsight/observation_history_after_revision.json", hist)
        fu["history_entries"] = (
            len(hist) if isinstance(hist, list) else len(dump(hist).get("history", []) or [])
        )
    print("revision:", fu["revision"]["observation_includes_new_case_after_s"])

    out["followup"] = fu
    if not keep:
        for b in out.get("scratch_banks_kept") or [bank]:
            await hs.adelete_bank(b)
        out["scratch_banks_deleted"] = out.pop("scratch_banks_kept", [bank])
    await hs.aclose()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["gemini", "groq", "hindsight", "followup", "all"], default="all")
    ap.add_argument("--keep", action="store_true", help="keep the scratch banks")
    ap.add_argument("--bank", help="kept concise bank for --part followup")
    args = ap.parse_args()
    if args.part == "followup":
        out = json.loads(RESULTS.read_text(encoding="utf-8"))
        await followup_part(out, args.bank or out["scratch_banks_kept"][0], args.keep)
        RESULTS.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return
    out: dict[str, Any] = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    out["ran_at"] = datetime.now(UTC).isoformat()
    if args.part in ("gemini", "all"):
        await gemini_part(out)
    if args.part in ("groq", "all"):
        await groq_part(out)
    if args.part in ("hindsight", "all"):
        await hindsight_part(out, args.keep)
    RESULTS.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", RESULTS.relative_to(ROOT))


if __name__ == "__main__":
    asyncio.run(main())
