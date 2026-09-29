"""eval/replay.py: the learning-curve series and the simulated reviewer's action (SPEC §14.4)."""

from eval.replay import action_for, curves


def row(i, mode, fc=False, effort=3, cls="known", family="E1", maturity="tentative"):
    return {
        "case_id": f"C{i}",
        "date": f"2026-10-{i:02d}",
        "family": family,
        "gt_class": cls,
        "predicted_class": cls,
        "review_mode": mode,
        "maturity": maturity,
        "false_confidence": fc,
        "effort": effort,
    }


def test_curves_rolling_one_click_share_effort_and_false_confidence():
    rows = [
        row(1, "step_by_step", effort=4),
        row(2, "step_by_step", effort=4),
        row(3, "one_click", effort=1, maturity="established"),
        row(4, "one_click", cls="normal"),
        row(5, "escalate", fc=False, effort=1),
    ]
    c = curves(rows)
    assert [p["share"] for p in c["one_click_share"]] == [0, 0, 1, 1]  # the normal case is excluded
    assert [p["per_case"] for p in c["review_effort"]] == [4.0, 4.0, 3.0, 2.5]
    assert c["false_confidence"][-1]["false_confidence"] == 0
    assert [p["maturity"] for p in c["maturity"]] == ["tentative", "tentative", "established", "tentative"]


def test_simulated_reviewer_action():
    gt = {"steps": ["HOLD_PO", "KEEP_VENDOR_ACTIVE"]}
    assert action_for(["KEEP_VENDOR_ACTIVE", "HOLD_PO"], gt, "one_click") == "approve"
    assert action_for(["KEEP_VENDOR_ACTIVE", "HOLD_PO"], gt, "step_by_step") == "confirm"
    assert action_for(["HOLD_PO"], gt, "step_by_step") == "edit"
    assert action_for([], gt, "escalate") == "resolve"


def test_still_uncovered_is_relative_to_earlier_replayed_resolutions():
    from eval.replay import still_uncovered

    gt = {"uncovered_checks": ["related_party"], "causes": {"related_party": "related_party"}}
    assert still_uncovered(gt, set()) == ["related_party"]
    # An earlier replayed related-party resolution covers it; a different cause on the same check does not.
    assert still_uncovered(gt, {("related_party", "related_party")}) == []
    gst = {"uncovered_checks": ["vendor"], "causes": {"vendor": "gst_cancelled"}}
    assert still_uncovered(gst, {("vendor", "cert_expired")}) == ["vendor"]
