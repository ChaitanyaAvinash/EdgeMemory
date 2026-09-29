"""Pipeline (SPEC §9): orchestrates one request for any arm.

Owns: running the stages in order and writing each one to the ledger, so a case's full trace can be rendered.
Stages 1-6 (`run_detection`): intake, extraction, checks, the normal short-cut, coverage (recall +
verification) and classification. Stage 7 (`run_case`): composition, conflicts, the floor, maturity and
review mode. Review and retain (stages 8-9) arrive with the API in Phase 3 and memory dynamics in Phase 4.
Never: reads ground truth, releases money, or shows a result it couldn't ground; if memory or the LLM
fails, the case escalates to a human (rule 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from sqlmodel import Session, select

from api import ledger
from api.engine.classify import classify
from api.engine.composer import Composition, Procedure, Reasoner, case_maturity, compose, review_mode
from api.engine.detector import Detection, LedgerCase, PolicyRec, detect
from api.engine.extractor import Extraction, IntakeForm, extract
from api.engine.precedence import FloorContext
from api.engine.rules import approver_for, run_checks
from api.engine.types import (
    ApprovalLimitRec,
    BudgetRec,
    Classification,
    Coverage,
    DelegationRec,
    EmployeeRec,
    MasterData,
    PriorRequestRec,
    RequestFacts,
    VendorRec,
    Violation,
)
from api.llm import LLM, LLMUnavailable, gemini_schema, normalise_enums
from api.memory.backend import MemoryBackend, MemoryUnavailable
from api.settings import IST

ESCALATION_MESSAGE = "Memory unavailable, escalating to a human"


# --- ledger → engine snapshots -------------------------------------------------------------------


def master_snapshot(s: Session) -> MasterData:
    return MasterData(
        vendors={
            v.id: VendorRec(
                v.id,
                v.name,
                v.gstin,
                v.gst_status,
                v.status,
                v.cert_name,
                v.cert_expiry,
                v.bank_changed_at,
                v.sole_source,
                v.category,
            )
            for v in s.exec(select(ledger.Vendor)).all()
        },
        employees={
            e.id: EmployeeRec(e.id, e.name, e.role, e.cost_centre, e.leave_from, e.leave_to)
            for e in s.exec(select(ledger.Employee)).all()
        },
        approval_limits=[
            ApprovalLimitRec(a.cost_centre, a.max_amount, a.approver_id)
            for a in s.exec(select(ledger.ApprovalLimit)).all()
        ],
        delegations=[
            DelegationRec(d.approver_id, d.delegate_id, d.max_amount, d.valid_from, d.valid_to)
            for d in s.exec(select(ledger.Delegation)).all()
        ],
        budgets={
            (b.cost_centre, b.fiscal_year): BudgetRec(b.cost_centre, b.fiscal_year, b.allocated, b.spent)
            for b in s.exec(select(ledger.Budget)).all()
        },
        prior_requests=[
            PriorRequestRec(r.id, r.vendor_id, r.amount, r.submitted_at.date())
            for r in s.exec(select(ledger.Request)).all()
            if r.vendor_id and r.amount is not None
        ],
    )


def ledger_cases(s: Session) -> dict[str, LedgerCase]:
    return {
        x.case_id: LedgerCase(
            x.case_id,
            x.kind,
            tuple(x.checks),
            dict(x.causes),
            tuple(x.steps),
            x.resolved_at,
            x.status,
            x.amount,
            x.category,
            x.urgency,
            x.combo,
            x.overridden_by,
        )
        for x in s.exec(select(ledger.Lesson)).all()
    }


def ledger_policies(s: Session) -> list[PolicyRec]:
    return [
        PolicyRec(p.id, p.effective_date, p.tag, p.text) for p in s.exec(select(ledger.PolicyChange)).all()
    ]


def load_master_json(s: Session, data: dict[str, Any]) -> None:
    """Load a master-data document (vendors, employees, approval limits, delegations, budgets, prior requests)."""
    d = date.fromisoformat

    def dates(row: dict, *keys: str) -> dict:
        return row | {k: d(row[k]) if row.get(k) else None for k in keys}

    for v in data["vendors"]:
        s.merge(ledger.Vendor(**dates(v, "cert_expiry", "bank_changed_at")))
    for e in data["employees"]:
        s.merge(ledger.Employee(**dates(e, "leave_from", "leave_to")))
    for model, key in (
        (ledger.ApprovalLimit, "approval_limits"),
        (ledger.Delegation, "delegations"),
        (ledger.Budget, "budgets"),
    ):
        for old in s.exec(select(model)).all():
            s.delete(old)
        for row in data[key]:
            s.add(model(**dates(row, "valid_from", "valid_to") if key == "delegations" else row))
    for p in data.get("prior_requests", []):
        s.merge(
            ledger.Request(
                id=p["id"],
                submitted_at=datetime.combine(d(p["submitted_on"]), time(10, 0), IST),
                vendor_id=p["vendor_id"],
                amount=p["amount"],
                cost_centre=p.get("cost_centre", ""),
                status="closed",
            )
        )
    s.commit()


# --- one case ------------------------------------------------------------------------------------


@dataclass
class CaseResult:
    request_id: str
    extraction: Extraction | None
    violations: list[Violation]
    detection: Detection | None
    classification: Classification
    escalated: str = ""  # set when memory or the LLM failed (rule 11)
    flags: list[str] = field(default_factory=list)


def request_text(form: IntakeForm) -> str:
    """What the requester wrote, for the verifier to confirm a precedent's conditions against (SPEC §5.1)."""
    parts = [
        ("justification", form.justification),
        ("email thread", form.email_thread),
        ("attachment", form.attachment_text),
    ]
    return "\n".join(f"{name}: {text.strip()}" for name, text in parts if text and text.strip())


def _persist(s: Session, form: IntakeForm, r: CaseResult) -> None:
    f = r.extraction.facts if r.extraction else None
    s.merge(
        ledger.Request(
            id=form.request_id,
            submitted_at=form.submitted_at,
            vendor_id=f.vendor_id if f else None,
            vendor_name_raw=form.vendor_name,
            amount=f.amount if f else None,
            amount_raw=form.amount_raw,
            cost_centre=form.cost_centre,
            category=f.category if f else "",
            urgency=f.urgency if f else "",
            requester_id=form.requester_id,
            quotes_count=form.quotes_attached,
            signals=[{"name": x.name, "source": x.source, "span": x.span} for x in f.signals] if f else [],
            dropped_signals=r.extraction.dropped_signals if r.extraction else [],
            justification=form.justification,
            email_thread=form.email_thread,
            attachment_text=form.attachment_text,
            case_class=r.classification.cls,
            novel_combination=r.classification.novel_combination,
            status="escalated" if r.escalated else "open",
        )
    )
    for old in s.exec(
        select(ledger.ViolationRow).where(ledger.ViolationRow.request_id == form.request_id)
    ).all():
        s.delete(old)
    for old in s.exec(
        select(ledger.CoverageRow).where(ledger.CoverageRow.request_id == form.request_id)
    ).all():
        s.delete(old)
    s.flush()
    vrows = []
    for v in r.violations:
        row = ledger.ViolationRow(
            request_id=form.request_id,
            check=v.check,
            cause=v.cause,
            detail=v.detail,
            source=v.source,
            source_span=v.source_span,
        )
        s.add(row)
        vrows.append(row)
    s.flush()
    det = r.detection
    if det:
        for c in det.candidates + det.interaction_candidates:
            vr = det.verdicts.get(c.id)
            s.add(
                ledger.CoverageRow(
                    violation_id=vrows[c.violation].id if c.violation is not None else None,
                    request_id=form.request_id,
                    candidate_id=c.id,
                    memory_id=c.hit.id,
                    memory_type=c.hit.type,
                    memory_text=c.hit.text,
                    case_ids=c.case_ids,
                    verdict=vr.verdict if vr else "",
                    differences=vr.differences if vr else [],
                    reason=vr.reason if vr else "",
                    guard=vr.guard if vr else "",
                    is_interaction=c.violation is None,
                    combo=c.combo,
                )
            )
    s.commit()


async def run_detection(
    form: IntakeForm, s: Session, backend: MemoryBackend, llm: LLM, use_cache: bool = True
) -> CaseResult:
    md = master_snapshot(s)
    try:
        ext = await extract(form, md.vendors, llm)
    except LLMUnavailable as e:
        r = CaseResult(form.request_id, None, [], None, Classification("unknown"), f"extraction failed: {e}")
        _persist(s, form, r)
        return r
    violations = run_checks(ext.facts, md)
    flags = [f"signal_dropped:{d['name']}" for d in ext.dropped_signals]
    if not violations:
        r = CaseResult(form.request_id, ext, [], None, Classification("normal"), flags=flags)
        _persist(s, form, r)
        return r
    try:
        det = await detect(
            ext.facts,
            md.vendors.get(ext.facts.vendor_id or ""),
            violations,
            backend,
            llm,
            ledger_cases(s),
            ledger_policies(s),
            use_cache=use_cache,
            request_text=request_text(form),
        )
    except (MemoryUnavailable, LLMUnavailable) as e:
        # Never show a confident procedure we couldn't ground: every check is uncovered, and a human decides.
        cov = [Coverage(v.check, "no", reason=ESCALATION_MESSAGE) for v in violations]
        r = CaseResult(
            form.request_id,
            ext,
            violations,
            None,
            classify(violations, cov, None),
            f"{ESCALATION_MESSAGE}: {e}",
            flags,
        )
        _persist(s, form, r)
        return r
    for c in det.coverage:
        flags += c.flags
    if det.trimmed:
        flags.append(f"verifier_candidates_trimmed:{','.join(det.trimmed)}")
    r = CaseResult(
        form.request_id,
        ext,
        violations,
        det,
        classify(violations, det.coverage, det.interaction),
        flags=flags,
    )
    _persist(s, form, r)
    return r


# --- stage 7: compose, conflicts, floor (SPEC §7, §6) ---------------------------------------------


def floor_context(facts: RequestFacts, violations: list[Violation], md: MasterData) -> FloorContext:
    """What the risk floor needs, from the rules' findings and the ledger (never from the LLM alone)."""
    vendor = md.vendors.get(facts.vendor_id or "")
    rule = approver_for(facts, md)
    dels = [
        (d.delegate_id, d.max_amount, d.valid_from, d.valid_to)
        for d in md.delegations
        if rule is not None and d.approver_id == rule.approver_id
    ]
    return FloorContext(
        submitted_on=facts.submitted_on,
        amount=facts.amount or 0,
        bank_change=any(v.check == "bank" for v in violations),
        related_party=any(v.check == "related_party" for v in violations),
        gst_cancelled=bool(vendor and vendor.gst_status != "active"),
        delegations=dels,
    )


def hindsight_reasoner(backend: MemoryBackend) -> Reasoner:
    """Arm C: Hindsight reflect with the Procedure schema (inlined, api-notes D7)."""
    schema = gemini_schema(Procedure)

    async def reason(prompt: str, tags: list[str]) -> tuple[Procedure | None, str, list[str]]:
        res = await backend.reflect(prompt, tags, schema)
        if res.structured is None:
            return None, res.error, []
        return Procedure.model_validate(normalise_enums(schema, res.structured)), res.text, res.based_on_ids

    return reason


def llm_reasoner(llm: LLM, case_id: str) -> Reasoner:
    """Arm D: one LLM call with the same prompt and schema as reflect."""

    async def reason(prompt: str, tags: list[str]) -> tuple[Procedure | None, str, list[str]]:
        r = await llm.call("composer_d", prompt, Procedure, "composer-v1", case_id=case_id)
        return r.parsed, r.raw, []

    return reason


@dataclass
class CaseOutcome:
    detection: CaseResult
    composition: Composition | None
    maturity: str
    review_mode: str


def _persist_procedure(
    s: Session, request_id: str, arm: str, comp: Composition | None, standard: bool
) -> None:
    for old in s.exec(
        select(ledger.Procedure).where(ledger.Procedure.request_id == request_id, ledger.Procedure.arm == arm)
    ).all():
        s.delete(old)
    if standard:
        steps = [
            {
                "code": "STANDARD_APPROVAL",
                "reason": "every check passed",
                "cited_case_ids": [],
                "origin": "default",
            }
        ]
        s.add(ledger.Procedure(request_id=request_id, arm=arm, steps=steps))
    elif comp is not None:
        s.add(
            ledger.Procedure(
                request_id=request_id,
                arm=arm,
                steps=[
                    {
                        "code": x.code,
                        "reason": x.reason,
                        "cited_case_ids": x.cited_case_ids,
                        "origin": x.origin,
                    }
                    for x in comp.steps
                ],
                union_steps=[{"code": x.code, "cited_case_ids": x.cited_case_ids} for x in comp.union_steps],
                removed_from_union=comp.removed_from_union,
                conflicts=[
                    {"pair": list(c.pair), "kept": c.kept, "dropped": c.dropped, "reason": c.reason}
                    for c in comp.conflicts
                ],
                flags=comp.flags + [f"uncovered:{u}" for u in comp.uncovered],
                raw_output=comp.reasoning_raw,
            )
        )
    s.commit()


async def run_case(
    form: IntakeForm, s: Session, backend: MemoryBackend, llm: LLM, arm: str = "C", use_cache: bool = True
) -> CaseOutcome:
    """SPEC §9 stages 1-7 for one request. Arm C reasons with reflect, D with one LLM call, E with none."""
    r = await run_detection(form, s, backend, llm, use_cache=use_cache)
    comp: Composition | None = None
    if r.classification.cls == "normal":
        mode, maturity = "one_click", ""
    elif r.detection is None:
        mode, maturity = "escalate", ""
    else:
        md = master_snapshot(s)
        facts = r.extraction.facts
        reasoner = {"C": hindsight_reasoner(backend), "D": llm_reasoner(llm, form.request_id)}.get(arm)
        comp = await compose(
            facts,
            r.violations,
            r.detection,
            r.classification,
            ledger_cases(s),
            floor_context(facts, r.violations, md),
            reasoner,
        )
        policy_flags = [f for c in r.detection.coverage for f in c.flags]
        mode, maturity = review_mode(r.classification, comp, policy_flags), case_maturity(comp)
    _persist_procedure(s, form.request_id, arm, comp, standard=r.classification.cls == "normal")
    req = s.get(ledger.Request, form.request_id)
    if req is not None:
        req.maturity, req.review_mode = maturity, mode
        s.add(req)
        s.commit()
    return CaseOutcome(r, comp, maturity, mode)
