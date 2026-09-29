"""classify.py (SPEC §5.3): all five classes and the novel-combination flag."""

from api.engine.classify import classify
from api.engine.types import Coverage, InteractionCoverage, Violation


def v(check):
    return Violation(check, "c", "d", "ledger")


def cov(check, status):
    return Coverage(check, status)


def test_normal():
    assert classify([], [], None).cls == "normal"


def test_known_and_generalized():
    assert classify([v("vendor")], [cov("vendor", "yes")], None).cls == "known"
    assert classify([v("vendor")], [cov("vendor", "partial")], None).cls == "generalized"


def test_any_uncovered_violation_makes_it_unknown():
    c = classify([v("vendor"), v("approver")], [cov("vendor", "no"), cov("approver", "yes")], None)
    assert c.cls == "unknown" and [u.check for u in c.uncovered] == ["vendor"]


def test_composed_with_verified_interaction_is_not_novel():
    c = classify(
        [v("bank"), v("budget")],
        [cov("bank", "yes"), cov("budget", "yes")],
        InteractionCoverage("yes", "bank+budget"),
    )
    assert c.cls == "composed" and not c.novel_combination


def test_composed_without_or_with_partial_interaction_is_novel():
    vs, cs = [v("vendor"), v("quotes")], [cov("vendor", "yes"), cov("quotes", "partial")]
    assert classify(vs, cs, None).novel_combination
    assert classify(vs, cs, InteractionCoverage("partial", "quotes+vendor")).novel_combination


def test_coverage_must_match_violations():
    import pytest

    with pytest.raises(ValueError):
        classify([v("vendor")], [], None)
