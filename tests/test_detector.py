"""detector.py: candidate selection, code guards and aggregation (SPEC §5.1, §5.2), offline."""

from __future__ import annotations

from datetime import date

from api.engine.detector import (
    Candidate,
    CandidateVerdict,
    CitationStats,
    LedgerCase,
    PolicyRec,
    VerdictRow,
    aggregate,
    apply_guards,
    build_prompt,
    combos_for,
    select_candidates,
)
from api.engine.types import RequestFacts, Violation
from api.memory.backend import Hit, RecallResult


def case(
    cid,
    check="vendor",
    cause="cert_expired",
    amount=1_40_000,
    category="direct_material",
    resolved=date(2026, 3, 14),
    status="active",
    **kw,
):
    causes = kw.pop("causes", {check: cause})
    return LedgerCase(
        cid,
        kw.pop("kind", "experience"),
        tuple(causes),
        causes,
        ("HOLD_PO",),
        resolved,
        status,
        amount,
        category,
        "normal",
        **kw,
    )


CASES = {
    c.case_id: c
    for c in [
        case("PR-1"),
        case("PR-2", amount=85_000, category="indirect_mro", resolved=date(2026, 4, 2)),
        case("PR-3", check="vendor", cause="gst_cancelled"),
        case("PR-4", check="approver", cause="approver_on_leave", resolved=date(2026, 3, 5)),
        case(
            "PR-9",
            kind="interaction",
            causes={"bank": "bank_details_changed", "budget": "overrun"},
            combo="bank+budget",
        ),
    ]
}
POL = [PolicyRec("POLICY-2026-07-01", date(2026, 7, 1), "step:approver", "capex delegate needs controller")]


def req(amount=1_20_000, category="direct_material"):
    return RequestFacts(
        "PR-N", date(2026, 9, 23), "V-101", "Deccan", amount, "CC-ASSY", category, "normal", "E-4", 1
    )


def fact(fid, doc, tags=("step:vendor",), **kw):
    return Hit(fid, f"fact {fid}", kw.pop("type", "world"), list(tags), doc, **kw)


def test_candidates_dedupe_by_case_and_separate_policy_memos():
    obs = Hit("o1", "lesson", "observation", ["step:vendor"], source_fact_ids=["a", "b"])
    r = RecallResult(
        hits=[
            obs,
            fact("a", "PR-1"),
            fact("p", "POLICY-2026-07-01"),
            fact("x", "PR-UNKNOWN"),
            fact("c", "PR-2"),
        ],
        source_facts={"a": fact("a", "PR-1"), "b": fact("b", "PR-2")},
    )
    stats = CitationStats()
    chosen, policy = select_candidates(r, set(CASES), {"POLICY-2026-07-01"}, stats, "V1-C", 0, 5)
    assert [(c.id, c.case_ids) for c in chosen] == [("V1-C1", ["PR-1", "PR-2"])]  # facts of PR-1/PR-2 deduped
    assert [h.id for h in policy] == ["p"]
    assert stats.unresolved == ["PR-UNKNOWN"] and stats.total == stats.resolved + 1


def test_top_n_limit():
    r = RecallResult(hits=[fact("a", "PR-1"), fact("b", "PR-2"), fact("c", "PR-3")])
    chosen, _ = select_candidates(r, set(CASES), set(), CitationStats(), "V1-C", 0, 2)
    assert [c.case_ids for c in chosen] == [["PR-1"], ["PR-2"]]


def test_interaction_candidates_keep_only_allowed_combos():
    r = RecallResult(
        hits=[
            fact("i", "PR-9", tags=("interaction", "combo:bank+budget")),
            fact("j", "PR-1", tags=("combo:quotes+vendor",)),
        ]
    )
    chosen, _ = select_candidates(r, set(CASES), set(), CitationStats(), "I-C", None, 5, {"bank+budget"})
    assert [(c.case_ids, c.combo) for c in chosen] == [(["PR-9"], "bank+budget")]


def test_combos_are_all_subsets_of_two_or_more():
    vs = [Violation(c, "x", "d", "ledger") for c in ("bank", "budget", "approver")]
    assert combos_for(vs) == ["approver+bank", "approver+budget", "bank+budget", "approver+bank+budget"]


def cand(cid, case_ids, violation=0, combo=""):
    return Candidate(cid, Hit(cid, "t", "world"), case_ids, violation, combo)


V_CERT = [Violation("vendor", "cert_expired", "expired", "ledger")]


def test_missing_verdict_becomes_no():
    rows = apply_guards([], req(), V_CERT, [cand("V1-C1", ["PR-1"])], CASES)
    assert (rows["V1-C1"].verdict, rows["V1-C1"].guard) == ("no", "missing_verdict")


def test_cause_mismatch_forces_no():
    v = [Violation("vendor", "gst_cancelled", "gst", "ledger")]
    rows = apply_guards(
        [CandidateVerdict(candidate_id="V1-C1", verdict="yes", differences=[], reason="r")],
        req(),
        v,
        [cand("V1-C1", ["PR-1"])],
        CASES,
    )
    assert (rows["V1-C1"].verdict, rows["V1-C1"].guard) == ("no", "cause_mismatch")


def test_yes_needs_same_band_and_category_in_ledger():
    verdict = [CandidateVerdict(candidate_id="V1-C1", verdict="yes", differences=[], reason="r")]
    rows = apply_guards(verdict, req(amount=3_00_000), V_CERT, [cand("V1-C1", ["PR-1"])], CASES)
    assert (rows["V1-C1"].verdict, rows["V1-C1"].guard) == ("partial", "band_or_category")
    rows = apply_guards(verdict, req(), V_CERT, [cand("V1-C1", ["PR-1"])], CASES)
    assert (rows["V1-C1"].verdict, rows["V1-C1"].guard) == ("yes", "")


def test_guards_never_raise_a_verdict():
    rows = apply_guards(
        [CandidateVerdict(candidate_id="V1-C1", verdict="no", differences=[], reason="r")],
        req(),
        V_CERT,
        [cand("V1-C1", ["PR-1"])],
        CASES,
    )
    assert rows["V1-C1"].verdict == "no"


def test_interaction_cause_guard_checks_every_check_in_combo():
    vs = [
        Violation("bank", "bank_details_changed", "d", "ledger"),
        Violation("budget", "overrun", "d", "ledger"),
    ]
    ok = [CandidateVerdict(candidate_id="I-C1", verdict="yes", differences=[], reason="r")]
    rows = apply_guards(ok, req(), vs, [cand("I-C1", ["PR-9"], None, "bank+budget")], CASES)
    assert rows["I-C1"].verdict == "yes"


def test_aggregate_best_verdict_then_strength_then_recency():
    cands = [cand("V1-C1", ["PR-1"]), cand("V1-C2", ["PR-2"]), cand("V1-C3", ["PR-1", "PR-2"])]
    rows = {c.id: VerdictRow(c.id, "partial", [], "") for c in cands}
    cov, inter = aggregate(V_CERT, cands, [], rows, CASES, [])
    assert cov[0].status == "partial" and cov[0].case_ids == ["PR-1", "PR-2"] and cov[0].strength == 2
    rows["V1-C1"] = VerdictRow("V1-C1", "yes", [], "")
    cov, _ = aggregate(V_CERT, cands, [], rows, CASES, [])
    assert (cov[0].status, cov[0].case_ids) == ("yes", ["PR-1"]) and inter is None


def test_violation_without_candidates_is_uncovered():
    cov, _ = aggregate(V_CERT, [], [], {}, CASES, [])
    assert cov[0].status == "no"


def test_lesson_before_policy_change_is_flagged():
    v = [Violation("approver", "approver_on_leave", "d", "ledger")]
    c = [cand("V1-C1", ["PR-4"])]
    cov, _ = aggregate(v, c, [], {"V1-C1": VerdictRow("V1-C1", "yes", [], "")}, CASES, POL)
    assert cov[0].flags == ["predates_policy:POLICY-2026-07-01"]


def test_prompt_lists_every_candidate_and_ledger_facts():
    p = build_prompt(req(), None, V_CERT, [cand("V1-C1", ["PR-1"])], [], CASES, POL, [])
    assert "V1 vendor (cause: cert_expired)" in p and "PR-1: ₹1,40,000 (up to 2L)" in p
    assert p.rstrip().endswith("Return exactly one verdict for each of: V1-C1.")


def test_override_context_is_shown_to_the_verifier():
    from api.engine.detector import _case_line

    c = case("PR-7", overridden_by="PR-2026-0735 on 2026-08-12: vendor had a duplicate-invoice incident")
    line = _case_line(c, [])
    assert "OVERRIDDEN IN CONTEXT: PR-2026-0735" in line and "status active" in line


def test_policy_flag_fires_when_any_cited_case_predates_the_policy():
    post = case(
        "PR-8", check="approver", cause="approver_on_leave", resolved=date(2026, 8, 6), category="capex"
    )
    cases = CASES | {"PR-8": post}
    v = [Violation("approver", "approver_on_leave", "d", "ledger")]
    c = [cand("V1-C1", ["PR-4", "PR-8"])]  # an observation merging a pre-July and a post-July case
    cov, _ = aggregate(v, c, [], {"V1-C1": VerdictRow("V1-C1", "yes", [], "")}, cases, POL)
    assert cov[0].flags == ["predates_policy:POLICY-2026-07-01"]
    only_post = [cand("V1-C1", ["PR-8"])]
    cov, _ = aggregate(v, only_post, [], {"V1-C1": VerdictRow("V1-C1", "yes", [], "")}, cases, POL)
    assert cov[0].flags == []


# --- overrides merged into a standard lesson's memory, and the prompt budget -----------------------------

OV_CASES = CASES | {
    "PR-OV": case("PR-OV", kind="override", resolved=date(2026, 7, 8)),
    "PR-1B": case(
        "PR-1B", overridden_by="PR-OV on 2026-07-08: vendor not in good standing. Reviewer did: HOLD_PO."
    ),
}
KINDS = {k: v.kind for k, v in OV_CASES.items()}


def test_override_merged_into_an_observation_becomes_its_own_candidate():
    obs = Hit("o1", "lesson", "observation", ["step:vendor"], source_fact_ids=["a", "b"])
    r = RecallResult(hits=[obs], source_facts={"a": fact("a", "PR-1B"), "b": fact("b", "PR-OV")})
    chosen, _ = select_candidates(r, set(OV_CASES), set(), CitationStats(), "V1-C", 0, 5, kinds=KINDS)
    assert [(c.id, c.case_ids, c.split_from) for c in chosen] == [
        ("V1-C1", ["PR-1B"], ""),
        ("V1-C2", ["PR-OV"], "V1-C1"),
    ]
    # Interaction candidates are never split.
    chosen, _ = select_candidates(r, set(OV_CASES), set(), CitationStats(), "I-C", None, 5, kinds=KINDS)
    assert [c.case_ids for c in chosen] == [["PR-1B", "PR-OV"]]


def test_prompt_shows_an_override_with_its_recorded_context():
    obs = Hit("o1", "lesson", "observation", ["step:vendor"], source_fact_ids=["a", "b"])
    r = RecallResult(hits=[obs], source_facts={"a": fact("a", "PR-1B"), "b": fact("b", "PR-OV")})
    chosen, _ = select_candidates(r, set(OV_CASES), set(), CitationStats(), "V1-C", 0, 5, kinds=KINDS)
    p = build_prompt(req(), None, V_CERT, chosen, [], OV_CASES, [], [])
    assert "V1-C2 [reviewer override recorded in the same memory as V1-C1" in p
    assert "A REVIEWER OVERRIDE of an earlier lesson" in p and "vendor not in good standing" in p
    assert "OVERRIDDEN IN CONTEXT: PR-OV on 2026-07-08" in p


def test_trim_drops_lowest_ranked_standard_candidates_but_never_overrides():
    from api.engine.detector import trim_one

    cands = [
        cand("V1-C1", ["PR-1"]),
        cand("V1-C2", ["PR-2"]),
        cand("V1-C3", ["PR-OV"]),
        cand("V2-C1", ["PR-4"], 1),
    ]
    icands = [cand("I-C1", ["PR-9"], None), cand("I-C2", ["PR-9"], None)]
    dropped = [trim_one(cands, icands, KINDS) for _ in range(4)]
    assert [d.id if d else None for d in dropped] == ["V1-C2", "I-C2", None, None]
    assert [c.id for c in cands] == ["V1-C1", "V1-C3", "V2-C1"]  # one standard per check, override kept


def test_an_override_already_judged_is_not_split_out_again():
    obs = Hit("o1", "lesson", "observation", ["step:vendor"], source_fact_ids=["a", "b"])
    r = RecallResult(
        hits=[fact("b", "PR-OV"), obs], source_facts={"a": fact("a", "PR-1B"), "b": fact("b", "PR-OV")}
    )
    chosen, _ = select_candidates(r, set(OV_CASES), set(), CitationStats(), "V1-C", 0, 5, kinds=KINDS)
    assert [(c.id, c.case_ids, c.split_from) for c in chosen] == [
        ("V1-C1", ["PR-OV"], ""),
        ("V1-C2", ["PR-1B"], ""),
    ]


def test_a_request_is_never_its_own_precedent():
    # Re-running a demo beat after its decision was remembered used to cite the request itself.
    cases = CASES | {"PR-N": case("PR-N")}
    r = RecallResult(hits=[fact("s", "PR-N"), fact("a", "PR-1")])
    chosen, _ = select_candidates(r, set(cases), set(), CitationStats(), "V1-C", 0, 5, exclude="PR-N")
    assert [c.case_ids for c in chosen] == [["PR-1"]]
