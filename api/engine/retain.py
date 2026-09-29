"""Retain after a human decision (SPEC §9 stage 9, §8.3, first two steps of §8.7).

Owns: turning a reviewer's decision into memory kinds and ledger lessons:
  - resolve (an unknown case)                         → experience
  - approve/confirm a single-check case unchanged     → confirmation
  - approve/confirm a multi-check case               → interaction if the steps differ from the plain union,
                                                        else experience
  - edit or reject a recommendation that used lessons → override (of the cited lessons) + the reviewer's
                                                        decision as its own experience/interaction
The human decides; this module only records what they decided (CLAUDE.md rule 1).
Never: decides anything, releases money, or reads ground truth. Marking the overridden lesson in context
(§8.7 step 3) and observation snapshots (§8.9) arrive in Phase 4.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlmodel import Session, select

from api import ledger
from api.memory.backend import MemoryBackend, MemoryUnavailable
from api.memory.records import memory_item
from api.settings import config

ACTIONS = ("approve", "confirm", "edit", "reject", "resolve")


@dataclass
class RetainPlan:
    records: list[dict[str, Any]]  # memory records in the import_history format
    lessons: list[ledger.Lesson]


def plan_retain(
    req: ledger.Request,
    violations: list[ledger.ViolationRow],
    procedure: ledger.Procedure | None,
    cited_case_ids: list[str],
    action: str,
    final_steps: list[str],
    rationale: str,
    reviewer: str,
    outcome: str,
    decided_on: date,
) -> RetainPlan:
    """Pure: what to retain for this decision (unit-tested)."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action}")
    checks = sorted({v.check for v in violations})
    if not checks:
        return RetainPlan([], [])  # normal cases teach nothing new
    recommended = [s["code"] for s in (procedure.steps if procedure else [])]
    union = [s["code"] for s in (procedure.union_steps if procedure else [])]
    base = {
        "case_id": req.id,
        "checks": checks,
        "causes": {v.check: v.cause for v in violations},
        "resolved_at": decided_on.isoformat(),
        "reviewer": reviewer,
        "vendor_id": req.vendor_id or "",
        "approver_id": "",
        "amount": req.amount or 0,
        "category": req.category,
        "urgency": req.urgency,
        "request": (req.justification or "purchase request")[:120],
        "what_happened": "; ".join(v.detail for v in violations),
        "why": rationale or "reviewer decision",
        "steps": list(final_steps),
        "outcome": outcome or f"reviewer chose to {action}",
        "lesson": rationale or "as decided by the reviewer",
    }
    multi = len(checks) > 1
    differs_from_union = set(final_steps) != set(union)
    if action == "resolve" or not recommended:
        own_kind = "interaction" if multi and differs_from_union and union else "experience"
    elif action in ("approve", "confirm") and set(final_steps) == set(recommended):
        own_kind = (
            "interaction" if multi and differs_from_union else ("confirmation" if not multi else "experience")
        )
    else:
        own_kind = "interaction" if multi and differs_from_union else "experience"
    own = base | {"kind": own_kind}
    if own_kind == "interaction":
        own |= {"plain_union": union, "removed": ", ".join(sorted(set(union) - set(final_steps)))}
    records = [own]
    if action in ("edit", "reject") and recommended and cited_case_ids:
        records.append(
            base
            | {
                "kind": "override",
                "what_happened": f"the lesson recommended {', '.join(recommended)}; context: {base['what_happened']}",
                "why": rationale or "reviewer override",
                "overrides": f"lessons from {', '.join(cited_case_ids)}",
            }
        )
    lessons = [
        ledger.Lesson(
            case_id=req.id,
            kind=own_kind,
            tags=[],
            combo="+".join(checks) if own_kind == "interaction" else "",
            checks=checks,
            causes=base["causes"],
            steps=list(final_steps),
            resolved_at=decided_on,
            amount=base["amount"],
            category=req.category,
            urgency=req.urgency,
            vendor_id=base["vendor_id"],
        )
    ]
    return RetainPlan(records, lessons)


async def retain_decision(
    s: Session,
    backend: MemoryBackend,
    request_id: str,
    action: str,
    final_steps: list[str],
    rationale: str,
    reviewer: str,
    outcome: str,
    decided_on: date,
    arm: str = "C",
) -> dict[str, Any]:
    req = s.get(ledger.Request, request_id)
    if req is None:
        raise KeyError(request_id)
    violations = s.exec(select(ledger.ViolationRow).where(ledger.ViolationRow.request_id == request_id)).all()
    procedure = s.exec(
        select(ledger.Procedure).where(ledger.Procedure.request_id == request_id, ledger.Procedure.arm == arm)
    ).first()
    cov = s.exec(select(ledger.CoverageRow).where(ledger.CoverageRow.request_id == request_id)).all()
    cited = sorted({c for row in cov if row.verdict in ("yes", "partial") for c in row.case_ids})
    plan = plan_retain(
        req, violations, procedure, cited, action, final_steps, rationale, reviewer, outcome, decided_on
    )
    s.add(
        ledger.Decision(
            request_id=request_id,
            reviewer=reviewer,
            action=action,
            final_steps=final_steps,
            rationale=rationale,
        )
    )
    for lesson in plan.lessons:
        lesson.tags = [t for r in plan.records if r["kind"] == lesson.kind for t in memory_item(r).tags]
        s.merge(lesson)
    if action in ("edit", "reject") and cited:
        from scripts.import_history import mark_overridden

        note = (
            f"{request_id} on {decided_on.isoformat()}: {rationale or 'reviewer override'} "
            f"Reviewer did: {', '.join(final_steps)}."
        )
        mark_overridden(s, cited, note)
    retained = []
    for rec in plan.records:
        item = memory_item(rec)
        await backend.retain(item)
        s.add(
            ledger.Experience(
                case_id=item.case_id, document_id=item.document_id, bank_id=backend.bank_id, kind=item.kind
            )
        )
        retained.append({"kind": item.kind, "document_id": item.document_id, "tags": item.tags})
    req.status = "decided"
    s.add(req)
    s.commit()
    snapshots = await take_snapshots(s, backend, sorted({t for r in retained for t in r["tags"]}), request_id)
    return {"retained": retained, "consolidation": snapshots}


async def take_snapshots(
    s: Session, backend: MemoryBackend, tags: list[str], case_id: str | None = None
) -> dict[str, Any]:
    """SPEC §8.9: wait until each tag's observation cites the newly retained case (polling with backoff up to
    the limit measured in Phase 0), then store what the observations say now in `observation_snapshots`.

    "No pending operations" is not used as the signal: in Phase 0 it was true at 0.7 s while the observation
    only took in the new case at 4.1 s.
    """
    if not getattr(backend, "consolidates", True):
        return {"consolidated": None, "snapshots": []}  # arm D: nothing consolidates
    cc = config("memory")["consolidation"]
    deadline = time.monotonic() + float(cc["timeout_s"])
    delay = float(cc["poll_s"])
    latest: dict[str, list[dict[str, Any]]] = {}
    pending = set(tags)
    while True:
        for tag in sorted(pending):
            try:
                latest[tag] = await backend.observations(tag)
            except MemoryUnavailable:
                latest[tag] = []
            if case_id is None or any(case_id in o["case_ids"] for o in latest[tag]):
                pending.discard(tag)
        if not pending or time.monotonic() >= deadline:
            break
        await asyncio.sleep(delay)
        delay = min(delay * 1.5, float(cc["max_poll_s"]))
    snaps = []
    for tag, obs in latest.items():
        for o in obs:
            s.add(
                ledger.ObservationSnapshot(
                    bank_id=backend.bank_id, tag=tag, text=o["text"], source_case_ids=o["case_ids"]
                )
            )
            snaps.append({"tag": tag, "observation_id": o["id"], "cases": len(o["case_ids"])})
    s.commit()
    return {"consolidated": not pending, "pending_tags": sorted(pending), "snapshots": snaps}
