"""Composer (SPEC §7.1) plus maturity and review mode (SPEC §5.4, §5.5).

Owns: single-check lessons from the ledger, the plain union U, the reasoning step (reflect in arm C, one LLM
call in arm D, both behind the same `Reasoner` callable), code validation of the result (library codes,
citations, the removal rule), conflicts and the risk floor (precedence.py), the diff against U, and the
fallback when reasoning fails.
Never: lets reasoning remove a risk-control or compliance step without a verified interaction precedent
(rule 5), keeps an uncited step (rule 6), goes below the floor (rule 4), or releases money (rule 2).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from api.engine.detector import Detection, LedgerCase, VerdictRow
from api.engine.precedence import (
    ConflictRecord,
    FloorContext,
    Step,
    apply_floor,
    library,
    resolve_conflicts,
)
from api.engine.rules import inr
from api.engine.types import Classification, RequestFacts, Violation, amount_band
from api.settings import config

GUARDED_CLASSES = ("risk_control", "compliance")
STEP_CODES = tuple(config("step_library")["steps"])
StepCode = Literal[STEP_CODES]  # type: ignore[valid-type]


# --- the reasoning schema (shared by reflect and arm D) ------------------------------------------


class ProcStep(BaseModel):
    code: StepCode
    reason: str = Field(description="at most 25 words")
    cited_case_ids: list[str]


class Procedure(BaseModel):
    steps: list[ProcStep]
    removed_from_union: list[ProcStep]
    open_questions: list[str]


# (prompt, tags) -> (Procedure or None, raw text, memory IDs the answer was based on)
Reasoner = Callable[[str, list[str]], Awaitable[tuple[Procedure | None, str, list[str]]]]


# --- lessons, union, precedents ------------------------------------------------------------------


@dataclass
class Lesson:
    check: str
    steps: list[str]
    supporting: list[str]  # cases whose final steps contain every lesson step (SPEC §5.4)
    strength: int

    @property
    def maturity(self) -> str:
        return "established" if self.strength >= 2 else "tentative"


@dataclass
class InteractionPrecedent:
    case_ids: list[str]
    combo: str
    steps: list[str]  # final steps of the precedent case(s)
    strength: int


def verified_cases(
    det: Detection, violation: int, statuses=("yes", "partial"), cases: dict[str, LedgerCase] | None = None
) -> list[str]:
    """Cases the verifier accepted for this violation.

    An override case consolidated *inside* a standard lesson is not support for that lesson's opposite
    context: it counts only when the verifier judged a candidate made of override cases alone.
    """
    out: list[str] = []
    for c in det.candidates:
        if (
            c.violation == violation
            and det.verdicts.get(c.id, VerdictRow(c.id, "no", [], "")).verdict in statuses
        ):
            ids = list(c.case_ids)
            if cases is not None:
                kinds = {cases[x].kind for x in ids if x in cases}
                if kinds != {"override"}:
                    ids = [x for x in ids if x not in cases or cases[x].kind != "override"]
                elif det.verdicts[c.id].verdict != "yes":
                    # An override's context is its condition: unless the verifier confirmed it ("yes"), it
                    # must not change the procedure.
                    ids = []
            out += [x for x in ids if x not in out]
    return out


def single_lesson(check: str, supporting: list[str], cases: dict[str, LedgerCase]) -> Lesson:
    """SPEC §7.1 step 1: steps in at least half of the supporting experience/confirmation cases.

    A verified override (it reaches here only when the verifier judged the override itself "yes") revises the
    lesson in its context (SPEC §8.7), so when one is present the lesson comes from the overrides alone."""
    overrides = [cases[c] for c in supporting if cases[c].kind == "override"]
    usable = overrides or [cases[c] for c in supporting if cases[c].kind in ("experience", "confirmation")]
    counts: dict[str, int] = {}
    for c in usable:
        for s in c.steps:
            counts[s] = counts.get(s, 0) + 1
    steps = [s for s in STEP_CODES if counts.get(s, 0) * 2 >= len(usable) and counts.get(s, 0) > 0]
    backing = [c.case_id for c in usable if c.status != "overridden" and set(steps) <= set(c.steps)]
    return Lesson(check, steps, backing, len(backing))


def interaction_precedents(det: Detection, cases: dict[str, LedgerCase]) -> list[InteractionPrecedent]:
    """Verified (verdict yes) interaction candidates. More than one may apply (e.g. I1 and I3)."""
    out = []
    for c in det.interaction_candidates:
        if det.verdicts.get(c.id) and det.verdicts[c.id].verdict == "yes":
            steps: list[str] = []
            for cid in c.case_ids:
                steps += [s for s in cases[cid].steps if s not in steps]
            live = [cid for cid in c.case_ids if cases[cid].status != "overridden"]
            out.append(InteractionPrecedent(list(c.case_ids), c.combo, steps, len(live)))
    return out


def union(lessons: list[Lesson]) -> list[Step]:
    """SPEC §7.1 step 2: U, each step tagged with its source cases, in library order."""
    src: dict[str, list[str]] = {}
    for les in lessons:
        for s in les.steps:
            src.setdefault(s, [])
            src[s] += [c for c in les.supporting if c not in src[s]]
    return [
        Step(code, "in the plain combination of single-check lessons", src[code], "union")
        for code in STEP_CODES
        if code in src
    ]


# --- the reasoning prompt ------------------------------------------------------------------------


def reasoning_prompt(
    req: RequestFacts,
    violations: list[Violation],
    det: Detection,
    covered: list[int],
    u: list[Step],
    precedents: list[InteractionPrecedent],
) -> str:
    amt = f"{inr(req.amount)} ({amount_band(req.amount)})" if req.amount is not None else "unknown amount"
    lines = [
        "SYNTHETIC DATA. Compose the procedure for a purchase request that broke the standard process.",
        f"Request {req.id}: {amt}, {req.category}, urgency {req.urgency}, vendor {req.vendor_id}, "
        f"cost centre {req.cost_centre}.",
        "Failed checks and how their precedents were verified:",
    ]
    for i in covered:
        v, cov = violations[i], det.coverage[i]
        diff = f"; differences: {'; '.join(cov.differences)}" if cov.differences else ""
        lines.append(f"- {v.check} ({v.cause}): {cov.status}, cases {', '.join(cov.case_ids)}{diff}")
    lines.append("Plain combination U (start from this):")
    lines += [f"- {s.code} (cases {', '.join(s.cited_case_ids)})" for s in u] or ["- (empty)"]
    if precedents:
        lines.append("Verified interaction precedents (several checks failed together):")
        lines += [
            f"- combination {p.combo}, cases {', '.join(p.case_ids)}: final steps {', '.join(p.steps)}"
            for p in precedents
        ]
    lines += [
        "Step library (use only these codes): " + ", ".join(STEP_CODES) + ".",
        "Start from U. Adapt for listed differences. Apply each interaction precedent's changes. Give a reason "
        "and a cited case ID for every step, and for every step you remove from U. Cite only the case IDs above. "
        "Never recommend releasing a payment.",
    ]
    return "\n".join(lines)


# --- validation ----------------------------------------------------------------------------------


@dataclass
class Composition:
    steps: list[Step]
    union_steps: list[Step]
    removed_from_union: list[dict]
    added_to_union: list[str]
    conflicts: list[ConflictRecord]
    flags: list[str]
    lessons: list[Lesson]
    precedents: list[InteractionPrecedent]
    open_questions: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    reasoning_raw: str = ""
    based_on: list[str] = field(default_factory=list)
    diff_text: str = ""


def validate(
    proc: Procedure,
    u: list[Step],
    verified: set[str],
    precedent_cases: set[str],
    cases: dict[str, LedgerCase] | None = None,
) -> tuple[list[Step], list[dict], list[str]]:
    """SPEC §7.1 step 5 (rules 5 and 6). Returns (steps, removals kept, flags)."""
    lib = library()
    flags: list[str] = []
    steps: list[Step] = []
    u_codes = {x.code for x in u}
    for s in proc.steps:
        cites = [c for c in s.cited_case_ids if c in verified]
        # A step added beyond the plain union must cite a verified case that actually took that step.
        supported = (
            s.code in u_codes or cases is None or any(s.code in cases[c].steps for c in cites if c in cases)
        )
        if s.code not in lib:
            flags.append(f"dropped_unknown_step:{s.code}")
        elif not cites:
            flags.append(f"dropped_uncited_step:{s.code}")
        elif not supported:
            flags.append(f"dropped_unsupported_step:{s.code}")
        elif s.code not in {x.code for x in steps}:
            steps.append(Step(s.code, s.reason, cites, "memory"))
    removal_notes = {r.code: r for r in proc.removed_from_union}
    kept_codes = {s.code for s in steps}
    removals: list[dict] = []
    for us in u:
        if us.code in kept_codes:
            continue
        note = removal_notes.get(us.code)
        guarded = lib[us.code] in GUARDED_CLASSES
        cites = [c for c in (note.cited_case_ids if note else []) if c in precedent_cases]
        verified_cites = [c for c in (note.cited_case_ids if note else []) if c in verified]
        if guarded and not cites:
            steps.append(
                Step(
                    us.code,
                    "restored: removing a risk-control or compliance step needs a verified "
                    "interaction precedent",
                    us.cited_case_ids,
                    "union",
                )
            )
            flags.append(f"restored_removed_step:{us.code}")
        elif not guarded and not (note and note.reason.strip() and verified_cites):
            # SPEC §7.1: a removal needs a reason, and every cited case must be verified for this request.
            steps.append(
                Step(
                    us.code,
                    "restored: removal gave no reason or no verified case",
                    us.cited_case_ids,
                    "union",
                )
            )
            flags.append(f"restored_removed_step:{us.code}")
        else:
            removals.append(
                {
                    "code": us.code,
                    "reason": note.reason if note else "",
                    "cited_case_ids": cites or verified_cites,
                }
            )
    return steps, removals, flags


def diff_text(removals: list[dict], added: list[str], steps: list[Step]) -> str:
    if not removals and not added:
        return ""
    parts = [f"-{r['code']}" for r in removals] + [f"+{a}" for a in added]
    why = "; ".join(f"{r['code']}: {r['reason']} ({', '.join(r['cited_case_ids'])})" for r in removals)
    return "Changed from the plain combination: " + ", ".join(parts) + (f" ({why})" if why else "")


async def compose(
    req: RequestFacts,
    violations: list[Violation],
    det: Detection,
    cls: Classification,
    cases: dict[str, LedgerCase],
    ctx: FloorContext,
    reasoner: Reasoner | None,
) -> Composition:
    """The whole of SPEC §7.1 for one request. `reasoner=None` gives arm E (U + default conflicts + floor)."""
    covered = [i for i, c in enumerate(det.coverage) if c.status != "no"]
    lessons = [
        single_lesson(violations[i].check, verified_cases(det, i, cases=cases), cases) for i in covered
    ]
    u = union(lessons)
    precedents = interaction_precedents(det, cases) if len(violations) >= 2 else []
    flags: list[str] = []
    steps, removals, open_q, raw, based_on = list(u), [], [], "", []
    if reasoner is not None and u:
        verified = {c for i in covered for c in verified_cases(det, i, cases=cases)} | {
            c for p in precedents for c in p.case_ids
        }
        # 2. Interaction memories only when a verified interaction precedent applies; otherwise reflect pulls
        # in combination lessons (and their unverified cases) for a single-check case.
        tags = sorted({violations[i].tag for i in covered}) + (
            ["interaction"] + [f"combo:{p.combo}" for p in precedents] if precedents else []
        )
        try:
            proc, raw, based_on = await reasoner(
                reasoning_prompt(req, violations, det, covered, u, precedents), tags
            )
        except Exception as e:  # noqa: BLE001 - any reasoning failure takes the documented fallback
            proc, raw = None, f"{type(e).__name__}: {e}"
        if proc is None:
            flags.append("composed_without_memory_reasoning")
        else:
            steps, removals, vflags = validate(
                proc, u, verified, {c for p in precedents for c in p.case_ids}, cases
            )
            flags += vflags
            open_q = list(proc.open_questions)
    elif reasoner is None and u:
        flags.append("union_only")
    use_precedents = reasoner is not None and "composed_without_memory_reasoning" not in flags
    steps, conflicts = resolve_conflicts(
        steps, [(p.case_ids[0], p.steps) for p in precedents], ctx, use_precedents=use_precedents
    )
    floor = apply_floor(steps, ctx)
    flags += floor.flags
    final = floor.steps
    u_codes = {s.code for s in u}
    added = [s.code for s in final if s.code not in u_codes and s.origin != "floor"]
    for c in conflicts + floor.conflicts:
        if c.dropped in u_codes and not any(r["code"] == c.dropped for r in removals):
            removals.append(
                {"code": c.dropped, "reason": f"conflict with {c.kept} ({c.reason})", "cited_case_ids": []}
            )
    uncovered = [violations[i].check for i, c in enumerate(det.coverage) if c.status == "no"]
    if not final and covered:
        # Fail visibly (rule 11): a check with a verified precedent must never yield an empty procedure. (With
        # nothing covered the case is already unknown and escalated; there is no precedent to flag.)
        flags.append("empty_procedure")
    return Composition(
        final,
        u,
        removals,
        added,
        conflicts + floor.conflicts,
        flags,
        lessons,
        precedents,
        open_q,
        uncovered,
        raw,
        based_on,
        diff_text(removals, added, final),
    )


# --- maturity and review mode --------------------------------------------------------------------


def case_maturity(comp: Composition) -> str:
    """SPEC §5.4: the lowest maturity among the lessons used, including any interaction precedent."""
    levels = [les.maturity for les in comp.lessons] + [
        "established" if p.strength >= 2 else "tentative" for p in comp.precedents
    ]
    if not levels:
        return ""
    return "tentative" if "tentative" in levels else "established"


def review_mode(cls: Classification, comp: Composition | None, policy_flags: list[str]) -> str:
    """SPEC §5.5, plus: F3 is never one-click and composing without memory reasoning is step by step."""
    if cls.cls == "unknown" or (comp is not None and "empty_procedure" in comp.flags):
        return "escalate"
    if cls.cls == "normal":
        return "one_click"
    risky = (
        cls.cls == "generalized"
        or cls.novel_combination
        or bool(policy_flags)
        or comp is None
        or case_maturity(comp) == "tentative"
        or any(
            f in comp.flags for f in ("F3:no_one_click", "composed_without_memory_reasoning", "union_only")
        )
    )
    return "step_by_step" if risky else "one_click"
