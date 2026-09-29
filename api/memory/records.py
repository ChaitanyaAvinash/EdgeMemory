"""Memory records (SPEC §8.3): the one template that turns a resolved case into a memory item.

Owns: tags per memory kind, the content template (step codes appear literally), document IDs (overrides get
`<case ID>-override-<n>`), and MemoryItem construction. Used by the seed/cold-start import and by the live
retain after a human decision, so seeded and learned memories look the same.
Never: talks to a memory service or an LLM.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from api.engine.rules import inr
from api.engine.types import tag_for
from api.memory.backend import MemoryItem
from api.settings import IST

IST_NOON = time(12, 0, tzinfo=IST)


def document_id(rec: dict[str, Any]) -> str:
    """Overrides get `<case ID>-override-<n>` (SPEC §8.3); citations strip the suffix and mark them."""
    return f"{rec['case_id']}-override-1" if rec["kind"] == "override" else rec["case_id"]


def tags_for(rec: dict[str, Any]) -> list[str]:
    """SPEC §8.3 tags. Interactions get only `interaction` + `combo:`, so they don't pollute single-check lessons.
    Overrides carry the overridden lesson's tags."""
    if rec["kind"] == "interaction":
        return ["interaction", "combo:" + "+".join(sorted(rec["checks"]))]
    if rec["kind"] == "policy_change":
        return [rec["tag"], "policy"]
    return [tag_for(c) for c in rec["checks"]]


def render_content(rec: dict[str, Any]) -> str:
    """SPEC §8.3 content template; step codes appear literally so extracted facts keep them."""
    if rec["kind"] == "policy_change":
        return f"SYNTHETIC DATA. {rec['text']}"
    resolved = date.fromisoformat(rec["resolved_at"]).strftime("%d %b %Y")
    failed = " + ".join(f"{c} (cause: {rec['causes'][c]})" for c in rec["checks"])
    head = (
        f"SYNTHETIC DATA. Case {rec['case_id']}, resolved {resolved} by {rec['reviewer']} (Procurement Ops). "
        f"Kind: {rec['kind']}."
    )
    request = (
        f"Request: {inr(rec['amount'])} {rec['category'].replace('_', ' ')}, {rec['request']}, vendor "
        f"{rec['vendor_id']}, urgency {rec['urgency']}."
    )
    if rec["kind"] == "override":
        return "\n".join(
            [
                head,
                f"Override of: {rec.get('overrides', 'an earlier lesson')}.",
                f"Failed checks: {failed}.",
                request,
                f"What the lesson recommended, and the context: {rec['what_happened']}",
                f"Why the reviewer overrode it: {rec['why']}",
                f"Steps the reviewer approved instead (codes): {', '.join(rec['steps'])}.",
                f"Outcome: {rec['outcome']}",
                f"Revised lesson: {rec['lesson']}",
            ]
        )
    lines = [
        head,
        f"Failed checks: {failed}.",
        request,
        f"What happened: {rec['what_happened']}",
        f"Why the standard process did not fit: {rec['why']}",
    ]
    if rec.get("plain_union"):
        lines.append(f"Plain combination would have been: {', '.join(rec['plain_union'])}.")
    lines.append(f"Steps approved (codes): {', '.join(rec['steps'])}.")
    if rec.get("removed"):
        lines.append(f"Removed from the plain combination: {rec['removed']}")
    lines += [f"Outcome: {rec['outcome']}", f"Lesson: {rec['lesson']}"]
    return "\n".join(lines)


def memory_item(rec: dict[str, Any]) -> MemoryItem:
    when = rec.get("resolved_at") or rec["effective_date"]
    meta = {"case_id": rec["case_id"], "kind": rec["kind"]}
    if rec["kind"] != "policy_change":
        meta |= {
            "outcome": rec["outcome"],
            "reviewer": rec["reviewer"],
            "combo": "+".join(sorted(rec["checks"])),
            "overrides": rec.get("overrides", ""),
        }
    entities = [
        {"text": rec[k], "type": k.removesuffix("_id")} for k in ("vendor_id", "approver_id") if rec.get(k)
    ]
    return MemoryItem(
        case_id=rec["case_id"],
        kind=rec["kind"],
        content=render_content(rec),
        timestamp=datetime.combine(date.fromisoformat(when), IST_NOON),
        tags=tags_for(rec),
        document_id=document_id(rec),
        metadata=meta,
        entities=entities,
    )
