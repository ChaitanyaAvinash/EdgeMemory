"""Conflicts and the risk floor (SPEC §6.2, §6.3). Runs after composition, in every pipeline arm.

Owns: resolving conflicting step pairs (default priority, or a verified interaction precedent's choice when
the floor still holds) and enforcing the floor invariants F1-F5. Pure and deterministic.
Never: removes a floor step, lets a learned lesson go below the floor, releases a payment, or changes the
case's class (CLAUDE.md rule 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from api.settings import config

ORIGINS = ("memory", "union", "floor", "default")


@dataclass
class Step:
    code: str
    reason: str
    cited_case_ids: list[str] = field(default_factory=list)
    origin: str = "memory"  # memory | union | floor | default


@dataclass
class ConflictRecord:
    pair: tuple[str, str]
    kept: str
    dropped: str
    reason: str  # "default priority" | "precedent PR-..." | "floor F4"


@dataclass
class FloorContext:
    """What the floor needs to know about the request (from the ledger, rules and extractor)."""

    submitted_on: date
    amount: int
    bank_change: bool  # ledger change in the last 30 days, or claimed in the text (F1)
    related_party: bool  # F3
    gst_cancelled: bool  # F4
    # F2: delegations of the approver on leave, as (delegate_id, max_amount, valid_from, valid_to)
    delegations: list[tuple[str, int, date, date]] = field(default_factory=list)


@dataclass
class FloorResult:
    steps: list[Step]
    added: list[str]
    replaced: list[tuple[str, str]]
    dropped: list[str]
    flags: list[str]
    conflicts: list[ConflictRecord]


def library() -> dict[str, str]:
    """Step code → class."""
    return {code: v["class"] for code, v in config("step_library")["steps"].items()}


def class_priority() -> dict[str, int]:
    """Lower number = higher priority (SPEC §6.1 order)."""
    return {c: i for i, c in enumerate(config("step_library")["classes"])}


def _pairs() -> list[tuple[str, str]]:
    return [tuple(p) for p in config("conflicts")["pairs"]]


def _conservative() -> dict[frozenset, str]:
    return {
        frozenset(x["pair"]): x["winner"] for x in config("conflicts").get("conservative_within_class", [])
    }


def default_winner(a: str, b: str) -> str:
    lib, prio = library(), class_priority()
    pa, pb = prio[lib[a]], prio[lib[b]]
    if pa != pb:
        return a if pa < pb else b
    winner = _conservative().get(frozenset((a, b)))
    if winner is None:
        raise ValueError(f"no conservative winner configured for same-class pair {a}/{b}")
    return winner


def floor_required(ctx: FloorContext) -> dict[str, str]:
    """Steps the floor requires, with the rule that requires each."""
    req: dict[str, str] = {}
    if ctx.bank_change:
        req |= {"VERIFY_BANK_CALLBACK": "F1", "HOLD_PAYMENT": "F1"}
    if ctx.related_party:
        req |= {"DECLARE_CONFLICT_OF_INTEREST": "F3"}
    if ctx.gst_cancelled:
        req |= {"VERIFY_GST_STATUS": "F4", "HOLD_PO": "F4"}
    return req


def resolve_conflicts(
    steps: list[Step],
    precedents: list[tuple[str, list[str]]],
    ctx: FloorContext,
    use_precedents: bool = True,
) -> tuple[list[Step], list[ConflictRecord]]:
    """SPEC §6.2. `precedents` are verified interaction precedents as (case_id, final steps).

    A precedent that chose the lower-priority step keeps it, unless the floor requires the other step.
    """
    required = floor_required(ctx)
    codes = {s.code for s in steps}
    drop: set[str] = set()
    records: list[ConflictRecord] = []
    for a, b in _pairs():
        if a not in codes or b not in codes or a in drop or b in drop:
            continue
        win = default_winner(a, b)
        lose = b if win == a else a
        reason = "default priority"
        if use_precedents and lose not in required:
            for case_id, final in precedents:
                if lose in final and win not in final and win not in required:
                    win, lose, reason = lose, win, f"precedent {case_id}"
                    break
        drop.add(lose)
        records.append(ConflictRecord((a, b), win, lose, reason))
    return [s for s in steps if s.code not in drop], records


def _delegation_ok(ctx: FloorContext) -> bool:
    return any(vf <= ctx.submitted_on <= vt and mx >= ctx.amount for _, mx, vf, vt in ctx.delegations)


def apply_floor(steps: list[Step], ctx: FloorContext) -> FloorResult:
    """SPEC §6.3 F1-F5. Floor steps are labelled origin="floor" and are never presented as learned."""
    lib = library()
    out: list[Step] = []
    dropped, added, replaced, flags = [], [], [], []
    conflicts: list[ConflictRecord] = []
    # F5: anything outside the library is dropped and flagged.
    for s in steps:
        if s.code in lib:
            out.append(s)
        else:
            dropped.append(s.code)
            flags.append(f"F5:dropped_unknown_step:{s.code}")
    # F2: a delegate route that can't legally approve becomes next-level routing.
    if any(s.code == "ROUTE_DELEGATE" for s in out) and not _delegation_ok(ctx):
        out = [s for s in out if s.code != "ROUTE_DELEGATE"]
        replaced.append(("ROUTE_DELEGATE", "ROUTE_NEXT_LEVEL_APPROVER"))
        flags.append("F2:delegate_cannot_approve")
        if not any(s.code == "ROUTE_NEXT_LEVEL_APPROVER" for s in out):
            out.append(
                Step(
                    "ROUTE_NEXT_LEVEL_APPROVER",
                    "Added by safety floor (F2): the delegation doesn't cover this amount or date",
                    [],
                    "floor",
                )
            )
    # F1, F3, F4: required steps.
    have = {s.code for s in out}
    for code, rule in floor_required(ctx).items():
        if code not in have:
            out.append(Step(code, f"Added by safety floor ({rule})", [], "floor"))
            added.append(code)
            have.add(code)
    # A floor step wins any conflict it is part of.
    required = floor_required(ctx)
    for a, b in _pairs():
        for keep, lose in ((a, b), (b, a)):
            if keep in required and keep in have and lose in have:
                out = [s for s in out if s.code != lose]
                have.discard(lose)
                conflicts.append(ConflictRecord((a, b), keep, lose, f"floor {required[keep]}"))
    if ctx.related_party:
        flags.append("F3:no_one_click")
    return FloorResult(out, added, replaced, dropped, flags, conflicts)
