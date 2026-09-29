"""composer.py: lessons, union, reasoning validation (rules 5 and 6), fallback, arm E, maturity and review mode."""

from __future__ import annotations

import asyncio
from datetime import date

from api.engine.composer import (
    Procedure,
    ProcStep,
    case_maturity,
    compose,
    review_mode,
    single_lesson,
)
from api.engine.detector import Candidate, CitationStats, Detection, LedgerCase, VerdictRow
from api.engine.precedence import FloorContext
from api.engine.types import Classification, Coverage, InteractionCoverage, RequestFacts, Violation
from api.memory.backend import Hit

E5 = ("VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "HOLD_PO")
E2 = ("ALLOW_BUDGET_OVERRUN", "ATTACH_LINE_DOWN_EVIDENCE", "ADD_CONTROLLER_SIGNOFF", "EXPEDITE_PO")
I3 = (
    "EXPEDITE_PO",
    "VERIFY_BANK_CALLBACK",
    "HOLD_PAYMENT",
    "ALLOW_BUDGET_OVERRUN",
    "ATTACH_LINE_DOWN_EVIDENCE",
    "ADD_CONTROLLER_SIGNOFF",
)


def lc(cid, steps, kind="experience", status="active", checks=("bank",)):
    return LedgerCase(
        cid,
        kind,
        checks,
        {c: "x" for c in checks},
        steps,
        date(2026, 3, 1),
        status,
        1_50_000,
        "direct_material",
        "line_down",
    )


CASES = {
    "B1": lc("B1", E5),
    "B2": lc("B2", E5),
    "G1": lc("G1", E2, checks=("budget",)),
    "G2": lc("G2", E2[:3], checks=("budget",)),  # one precedent without EXPEDITE_PO
    "I3": lc("I3", I3, kind="interaction", checks=("bank", "budget")),
}
REQ = RequestFacts(
    "PR-N",
    date(2026, 9, 24),
    "V-107",
    "Nizam",
    1_90_000,
    "CC-MACH",
    "direct_material",
    "line_down",
    "E-402",
    1,
)
VIOL = [
    Violation("bank", "bank_details_changed", "d", "ledger"),
    Violation("budget", "overrun", "d", "ledger"),
]
CTX = FloorContext(date(2026, 9, 24), 1_90_000, bank_change=True, related_party=False, gst_cancelled=False)


def cand(cid, cases, violation, combo=""):
    return Candidate(cid, Hit(cid, "t", "world"), cases, violation, combo)


def detection(interaction=True, statuses=("yes", "yes")):
    cands = [cand("V1-C1", ["B1", "B2"], 0), cand("V2-C1", ["G1", "G2"], 1)]
    icands = [cand("I-C1", ["I3"], None, "bank+budget")] if interaction else []
    verdicts = {
        "V1-C1": VerdictRow("V1-C1", statuses[0], [], ""),
        "V2-C1": VerdictRow("V2-C1", statuses[1], [], ""),
    }
    if interaction:
        verdicts["I-C1"] = VerdictRow("I-C1", "yes", [], "")
    cov = [Coverage("bank", statuses[0], ["B1", "B2"], 2), Coverage("budget", statuses[1], ["G1", "G2"], 2)]
    inter = InteractionCoverage("yes", "bank+budget", ["I3"]) if interaction else None
    return Detection(cov, inter, cands, icands, verdicts, CitationStats(), [])


def reasoner_returning(proc):
    async def r(prompt, tags):
        r.prompt, r.tags = prompt, tags
        return proc, "raw", []

    return r


def run(coro):
    return asyncio.run(coro)


def codes(comp):
    return {s.code for s in comp.steps}


def ps(code, cites, reason="r"):
    return ProcStep(code=code, reason=reason, cited_case_ids=cites)


I3_ANSWER = Procedure(
    steps=[ps(c, ["I3"]) for c in I3],
    removed_from_union=[ps("HOLD_PO", ["I3"], "a PO is not a payment")],
    open_questions=[],
)


def test_single_lesson_majority_and_strength():
    les = single_lesson("budget", ["G1", "G2"], CASES)
    assert set(les.steps) == set(E2)  # all four appear in at least half of the two cases (library order)
    assert les.supporting == ["G1"] and les.maturity == "tentative"  # G2 lacks EXPEDITE_PO
    assert single_lesson("bank", ["B1", "B2"], CASES).maturity == "established"


def test_i3_precedent_removes_hold_po_and_floor_holds():
    r = reasoner_returning(I3_ANSWER)
    comp = run(compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, r))
    assert "HOLD_PO" not in codes(comp) and {"EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"} <= codes(
        comp
    )
    assert (
        comp.removed_from_union[0]["code"] == "HOLD_PO"
        and "I3" in comp.removed_from_union[0]["cited_case_ids"]
    )
    assert comp.diff_text.startswith("Changed from the plain combination: -HOLD_PO")
    assert "combo:bank+budget" in r.tags and "HOLD_PO" in r.prompt


def test_removal_of_compliance_step_without_precedent_is_restored():
    proc = Procedure(
        steps=[ps(c, ["B1"]) for c in ("VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "EXPEDITE_PO")]
        + [ps(c, ["G1"]) for c in E2[:3]],
        removed_from_union=[ps("HOLD_PO", ["B1"], "faster")],
        open_questions=[],
    )
    comp = run(
        compose(
            REQ,
            VIOL,
            detection(interaction=False),
            Classification("composed", novel_combination=True),
            CASES,
            CTX,
            reasoner_returning(proc),
        )
    )
    assert "restored_removed_step:HOLD_PO" in comp.flags
    # restored HOLD_PO then beats EXPEDITE_PO by default priority (no precedent)
    assert "HOLD_PO" in codes(comp) and "EXPEDITE_PO" not in codes(comp)


def test_uncited_and_invented_citations_are_dropped():
    proc = Procedure(
        steps=[ps(c, ["I3"]) for c in I3] + [ps("ESCALATE_AUDIT", ["PR-NOT-VERIFIED"])],
        removed_from_union=[ps("HOLD_PO", ["I3"], "PO is not payment")],
        open_questions=[],
    )
    comp = run(
        compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, reasoner_returning(proc))
    )
    assert "dropped_uncited_step:ESCALATE_AUDIT" in comp.flags and "ESCALATE_AUDIT" not in codes(comp)


def test_routing_removal_needs_a_reason():
    u_lessons = {"A1": lc("A1", ("ROUTE_DELEGATE",), checks=("approver",))}
    cases = CASES | u_lessons
    det = Detection(
        [Coverage("approver", "yes", ["A1"], 1)],
        None,
        [cand("V1-C1", ["A1"], 0)],
        [],
        {"V1-C1": VerdictRow("V1-C1", "yes", [], "")},
        CitationStats(),
        [],
    )
    proc = Procedure(steps=[], removed_from_union=[ps("ROUTE_DELEGATE", ["A1"], "  ")], open_questions=[])
    comp = run(
        compose(
            REQ,
            [Violation("approver", "approver_on_leave", "d", "ledger")],
            det,
            Classification("known"),
            cases,
            CTX,
            reasoner_returning(proc),
        )
    )
    assert "restored_removed_step:ROUTE_DELEGATE" in comp.flags


def test_reasoning_failure_falls_back_to_union_default_conflicts_and_floor():
    async def broken(prompt, tags):
        raise RuntimeError("reflect 500")

    comp = run(compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, broken))
    assert "composed_without_memory_reasoning" in comp.flags
    assert "HOLD_PO" in codes(comp) and "EXPEDITE_PO" not in codes(comp)  # default priority, no precedent
    assert comp.conflicts[0].reason == "default priority"


def test_arm_e_is_union_plus_default_conflicts_plus_floor():
    comp = run(compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, None))
    assert "union_only" in comp.flags and "HOLD_PO" in codes(comp) and "EXPEDITE_PO" not in codes(comp)


def test_unknown_composes_covered_checks_only():
    det = detection(interaction=False, statuses=("yes", "no"))
    comp = run(compose(REQ, VIOL, det, Classification("unknown"), CASES, CTX, None))
    assert comp.uncovered == ["budget"] and "ALLOW_BUDGET_OVERRUN" not in codes(comp)


def test_maturity_and_review_mode():
    comp = run(
        compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, reasoner_returning(I3_ANSWER))
    )
    assert case_maturity(comp) == "tentative"  # budget lesson backed by 1 case; I3 by 1
    assert review_mode(Classification("composed"), comp, []) == "step_by_step"
    assert review_mode(Classification("unknown"), comp, []) == "escalate"
    assert review_mode(Classification("normal"), None, []) == "one_click"


def test_override_merged_into_a_standard_lesson_is_not_verified_support():
    from api.engine.composer import verified_cases

    cases = CASES | {"OV": lc("OV", ("COLLECT_QUOTES",), kind="override")}
    det = Detection(
        [Coverage("bank", "yes", ["B1", "OV"], 1)],
        None,
        [cand("V1-C1", ["B1", "OV"], 0)],
        [],
        {"V1-C1": VerdictRow("V1-C1", "yes", [], "")},
        CitationStats(),
        [],
    )
    assert verified_cases(det, 0, cases=cases) == ["B1"]
    det.candidates = [cand("V1-C1", ["OV"], 0)]  # the override memory judged on its own
    assert verified_cases(det, 0, cases=cases) == ["OV"]


def test_removal_citing_only_unverified_cases_is_restored():
    proc = Procedure(
        steps=[ps(c, ["B1"]) for c in ("VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "HOLD_PO")]
        + [ps(c, ["G1"]) for c in E2[:3]],
        removed_from_union=[ps("EXPEDITE_PO", ["PR-UNVERIFIED"], "not needed")],
        open_questions=[],
    )
    comp = run(
        compose(
            REQ,
            VIOL,
            detection(interaction=False),
            Classification("composed", novel_combination=True),
            CASES,
            CTX,
            reasoner_returning(proc),
        )
    )
    assert "restored_removed_step:EXPEDITE_PO" in comp.flags


def test_reflect_skips_interaction_tags_without_a_verified_precedent():
    r = reasoner_returning(I3_ANSWER)
    run(
        compose(
            REQ,
            VIOL,
            detection(interaction=False),
            Classification("composed", novel_combination=True),
            CASES,
            CTX,
            r,
        )
    )
    assert "interaction" not in r.tags and not any(t.startswith("combo:") for t in r.tags)


def test_override_alone_needs_a_yes_verdict_to_count():
    from api.engine.composer import verified_cases

    cases = CASES | {"OV": lc("OV", ("ESCALATE_AUDIT",), kind="override")}
    det = Detection(
        [Coverage("bank", "partial", ["OV"], 1)],
        None,
        [cand("V1-C1", ["OV"], 0)],
        [],
        {"V1-C1": VerdictRow("V1-C1", "partial", [], "context unclear")},
        CitationStats(),
        [],
    )
    assert verified_cases(det, 0, cases=cases) == []


def test_added_step_must_be_taken_by_a_cited_case():
    proc = Procedure(
        steps=[ps(c, ["I3"]) for c in I3] + [ps("ESCALATE_AUDIT", ["I3"])],
        removed_from_union=[ps("HOLD_PO", ["I3"], "a PO is not a payment")],
        open_questions=[],
    )
    comp = run(
        compose(REQ, VIOL, detection(), Classification("composed"), CASES, CTX, reasoner_returning(proc))
    )
    assert "dropped_unsupported_step:ESCALATE_AUDIT" in comp.flags and "ESCALATE_AUDIT" not in codes(comp)
    assert "EXPEDITE_PO" in codes(comp)  # I3 did take EXPEDITE_PO, so that addition stands


NO_FLOOR = FloorContext(
    date(2026, 9, 24), 1_90_000, bank_change=False, related_party=False, gst_cancelled=False
)
BUDGET = [Violation("budget", "overrun", "d", "ledger")]


def single_check_detection(case_ids, verdict="yes"):
    return Detection(
        [Coverage("budget", verdict, case_ids, 1)],
        None,
        [cand("V1-C1", case_ids, 0)],
        [],
        {"V1-C1": VerdictRow("V1-C1", verdict, [], "")},
        CitationStats(),
        [],
    )


def test_a_verified_override_gives_its_own_steps():
    # Test-split TEST-020: an override judged "yes" on its own used to give an empty lesson and procedure.
    cases = CASES | {
        "OV": lc("OV", ("REJECT_REQUEST", "ESCALATE_AUDIT"), kind="override", checks=("budget",))
    }
    comp = run(
        compose(REQ, BUDGET, single_check_detection(["OV"]), Classification("known"), cases, NO_FLOOR, None)
    )
    assert codes(comp) == {"REJECT_REQUEST", "ESCALATE_AUDIT"}
    assert "empty_procedure" not in comp.flags
    assert review_mode(Classification("known"), comp, []) == "step_by_step"  # one override case: tentative


def test_a_verified_override_takes_precedence_over_the_lesson_it_revised():
    cases = CASES | {"OV": lc("OV", ("REQUEST_MORE_INFO",), kind="override", checks=("budget",))}
    lesson = single_lesson("budget", ["G1", "G2", "OV"], cases)
    assert lesson.steps == ["REQUEST_MORE_INFO"] and lesson.supporting == ["OV"]


def test_an_empty_procedure_is_flagged_and_escalated():
    cases = CASES | {"G0": lc("G0", (), checks=("budget",))}
    comp = run(
        compose(REQ, BUDGET, single_check_detection(["G0"]), Classification("known"), cases, NO_FLOOR, None)
    )
    assert comp.steps == [] and "empty_procedure" in comp.flags
    assert review_mode(Classification("known"), comp, []) == "escalate"


def test_nothing_covered_is_not_flagged_as_an_empty_procedure():
    det = single_check_detection(["G1"], verdict="no")
    comp = run(compose(REQ, BUDGET, det, Classification("unknown"), CASES, NO_FLOOR, None))
    assert comp.steps == [] and "empty_procedure" not in comp.flags
    assert review_mode(Classification("unknown"), comp, []) == "escalate"
