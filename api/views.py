"""Read models for the API (SPEC §12, §15): case view, queue, memory trace, audit rows.

Owns: assembling ledger rows into what the UI renders, including the plain-language summary line. Every
count in it is computed here from SQLite (CLAUDE.md rule 3); no LLM text is used for numbers.
Never: writes to the ledger, calls memory or an LLM, or reads ground truth.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from api import ledger
from api.engine.precedence import library
from api.engine.rules import inr
from api.engine.types import amount_band, tag_for


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def summary_line(violations: list[dict], interactions_applied: int, steps: list[dict], cls: str) -> str:
    """e.g. "3 of 3 problems have precedents · 2 interaction precedents apply · payment held by safety floor"."""
    if cls == "normal":
        return "Every check passed · standard approval"
    n = len(violations)
    covered = sum(1 for v in violations if v["coverage"]["status"] in ("yes", "partial"))
    parts = [f"{covered} of {_plural(n, 'problem')} {'has' if n == 1 else 'have'} precedents"]
    if interactions_applied:
        parts.append(
            f"{_plural(interactions_applied, 'interaction precedent')} "
            f"{'applies' if interactions_applied == 1 else 'apply'}"
        )
    floor = [s["code"] for s in steps if s.get("origin") == "floor"]
    codes = {s["code"] for s in steps}
    if "HOLD_PAYMENT" in codes and any(v["check"] == "bank" for v in violations):
        parts.append("payment held until the bank callback")
    if floor:
        parts.append(f"{_plural(len(floor), 'step')} added by safety floor")
    if cls == "unknown":
        parts.append(f"{_plural(n - covered, 'problem')} escalated to a human")
    return " · ".join(parts)


def case_view(s: Session, request_id: str, arm: str = "C") -> dict[str, Any] | None:
    req = s.get(ledger.Request, request_id)
    if req is None:
        return None
    lib = library()
    vrows = s.exec(select(ledger.ViolationRow).where(ledger.ViolationRow.request_id == request_id)).all()
    cov = s.exec(select(ledger.CoverageRow).where(ledger.CoverageRow.request_id == request_id)).all()
    proc = s.exec(
        select(ledger.Procedure).where(ledger.Procedure.request_id == request_id, ledger.Procedure.arm == arm)
    ).first()
    lessons = {x.case_id: x for x in s.exec(select(ledger.Lesson)).all()}

    def cand(row: ledger.CoverageRow) -> dict[str, Any]:
        return {
            "candidate_id": row.candidate_id,
            "memory_type": row.memory_type,
            "memory_text": row.memory_text,
            "case_ids": row.case_ids,
            "verdict": row.verdict,
            "differences": row.differences,
            "reason": row.reason,
            "guard": row.guard,
            "combo": row.combo,
            "cases": [
                {
                    "case_id": c,
                    "amount": lessons[c].amount,
                    "amount_text": inr(lessons[c].amount),
                    "band": amount_band(lessons[c].amount),
                    "category": lessons[c].category,
                    "resolved_at": lessons[c].resolved_at.isoformat(),
                    "status": lessons[c].status,
                    "steps": lessons[c].steps,
                    "kind": lessons[c].kind,
                }
                for c in row.case_ids
                if c in lessons
            ],
        }

    rank = {"yes": 2, "partial": 1, "no": 0, "": -1}
    violations = []
    for v in vrows:
        cands = [cand(r) for r in cov if r.violation_id == v.id]
        # Same rule as the detector (SPEC §5.2): best verdict, then precedent strength, then most recent case.
        best = max(
            cands,
            key=lambda c: (
                rank[c["verdict"]],
                len({x["case_id"] for x in c["cases"] if x["status"] != "overridden"}),
                max((x["resolved_at"] for x in c["cases"]), default=""),
            ),
            default=None,
        )
        status = best["verdict"] if best and best["verdict"] else "no"
        strength = len({c["case_id"] for c in (best["cases"] if best else []) if c["status"] != "overridden"})
        violations.append(
            {
                "check": v.check,
                "tag": tag_for(v.check),
                "cause": v.cause,
                "detail": v.detail,
                "source": v.source,
                "source_span": v.source_span,
                "coverage": {
                    "status": status,
                    "case_ids": best["case_ids"] if best and status != "no" else [],
                    "strength": strength if status != "no" else 0,
                    "maturity": ("established" if strength >= 2 else "tentative") if status != "no" else "",
                    "differences": best["differences"] if best else [],
                    "reason": best["reason"] if best else "",
                },
                "candidates": cands,
            }
        )
    interactions = [cand(r) for r in cov if r.is_interaction]
    applied = sum(1 for c in interactions if c["verdict"] == "yes")
    steps = [dict(x) | {"class": lib.get(x["code"], "")} for x in (proc.steps if proc else [])]
    decisions = s.exec(select(ledger.Decision).where(ledger.Decision.request_id == request_id)).all()
    return {
        "request": {
            "id": req.id,
            "submitted_at": req.submitted_at.isoformat(),
            "vendor_id": req.vendor_id,
            "vendor_name": req.vendor_name_raw,
            "amount": req.amount,
            "amount_text": inr(req.amount) if req.amount is not None else req.amount_raw,
            "band": amount_band(req.amount) if req.amount is not None else "",
            "cost_centre": req.cost_centre,
            "category": req.category,
            "urgency": req.urgency,
            "requester_id": req.requester_id,
            "quotes_count": req.quotes_count,
            "justification": req.justification,
            "email_thread": req.email_thread,
            "attachment_text": req.attachment_text,
            "signals": req.signals,
            "dropped_signals": req.dropped_signals,
            "status": req.status,
        },
        "class": req.case_class,
        "novel_combination": req.novel_combination,
        "maturity": req.maturity,
        "review_mode": req.review_mode,
        "summary": summary_line(violations, applied, steps, req.case_class),
        "violations": violations,
        "interactions": interactions,
        "procedure": {
            "steps": steps,
            "union_steps": proc.union_steps if proc else [],
            "removed_from_union": proc.removed_from_union if proc else [],
            "conflicts": proc.conflicts if proc else [],
            "flags": proc.flags if proc else [],
            "floor_added": [x["code"] for x in steps if x.get("origin") == "floor"],
        },
        "decisions": [
            {
                "reviewer": d.reviewer,
                "action": d.action,
                "final_steps": d.final_steps,
                "rationale": d.rationale,
                "decided_at": d.decided_at.isoformat(),
            }
            for d in decisions
        ],
        "synthetic": True,
    }


def queue(s: Session) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {
        k: [] for k in ("unknown", "composed", "generalized", "known", "normal")
    }
    for r in s.exec(select(ledger.Request).where(ledger.Request.status.in_(["open", "escalated"]))).all():
        if not r.case_class:
            continue
        out.setdefault(r.case_class, []).append(
            {
                "id": r.id,
                "vendor_name": r.vendor_name_raw,
                "amount_text": inr(r.amount) if r.amount else r.amount_raw,
                "submitted_at": r.submitted_at.isoformat(),
                "maturity": r.maturity,
                "review_mode": r.review_mode,
                "novel_combination": r.novel_combination,
                "status": r.status,
            }
        )
    return out


def audit_rows(s: Session) -> list[dict[str, Any]]:
    """Every recommendation, citation, verdict, floor addition and human decision, with timestamps (SPEC §12)."""
    rows: list[dict[str, Any]] = []
    for r in s.exec(select(ledger.Request)).all():
        base = {
            "request_id": r.id,
            "submitted_at": r.submitted_at.isoformat(),
            "class": r.case_class,
            "review_mode": r.review_mode,
        }
        for c in s.exec(select(ledger.CoverageRow).where(ledger.CoverageRow.request_id == r.id)).all():
            rows.append(
                base
                | {
                    "record": "verdict",
                    "item": c.candidate_id,
                    "detail": c.verdict,
                    "citations": " ".join(c.case_ids),
                    "note": c.reason,
                    "guard": c.guard,
                }
            )
        for p in s.exec(select(ledger.Procedure).where(ledger.Procedure.request_id == r.id)).all():
            for st in p.steps:
                rows.append(
                    base
                    | {
                        "record": f"step ({p.arm})",
                        "item": st["code"],
                        "detail": st.get("origin", ""),
                        "citations": " ".join(st.get("cited_case_ids", [])),
                        "note": st.get("reason", ""),
                        "guard": "",
                    }
                )
        for d in s.exec(select(ledger.Decision).where(ledger.Decision.request_id == r.id)).all():
            rows.append(
                base
                | {
                    "record": "decision",
                    "item": d.action,
                    "detail": d.reviewer,
                    "citations": " ".join(d.final_steps),
                    "note": d.rationale,
                    "guard": d.decided_at.isoformat(),
                }
            )
    return rows
