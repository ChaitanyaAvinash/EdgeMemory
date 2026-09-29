"""metrics.py (SPEC §10) on a small synthetic ground truth."""

from api.metrics import all_metrics, f1, floor_required, m1_false_confidence, m8_review_effort, m9_minutes

A = {
    "research_unfamiliar_exception_min": 40,
    "step_by_step_review_min": 6,
    "one_click_review_min": 1,
    "edit_min": 2,
    "escalation_min": 40,
}

GT = {
    "K1": {
        "class": "known",
        "failed_checks": ["vendor"],
        "causes": {"vendor": "cert_expired"},
        "steps": ["HOLD_PO", "REQUEST_RENEWED_CERT"],
    },
    "C1": {
        "class": "composed",
        "failed_checks": ["bank", "budget"],
        "causes": {},
        "interaction": True,
        "steps": ["EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"],
    },
    "N1": {
        "class": "composed",
        "failed_checks": ["vendor", "quotes"],
        "causes": {},
        "interaction": True,
        "novel_combination": True,
        "steps": ["SOLE_SOURCE_FORM"],
    },
    "U1": {
        "class": "unknown",
        "failed_checks": ["vendor"],
        "causes": {"vendor": "gst_cancelled"},
        "uncovered_checks": ["vendor"],
        "steps": ["VERIFY_GST_STATUS", "HOLD_PO", "REQUEST_MORE_INFO"],
    },
    "U2": {
        "class": "unknown",
        "failed_checks": ["related_party"],
        "causes": {},
        "uncovered_checks": ["related_party"],
        "steps": ["DECLARE_CONFLICT_OF_INTEREST"],
    },
    "P1": {
        "class": "known",
        "failed_checks": ["approver"],
        "causes": {},
        "post_july_capex_approver": True,
        "after_override": True,
        "steps": ["ROUTE_DELEGATE", "ADD_CONTROLLER_SIGNOFF"],
    },
}
PRED = [
    {
        "case_id": "K1",
        "predicted_class": "known",
        "predicted_steps": ["HOLD_PO", "REQUEST_RENEWED_CERT"],
        "review_mode": "one_click",
        "tokens": 2000,
        "latency_ms": 4000,
    },
    {
        "case_id": "C1",
        "predicted_class": "composed",
        "predicted_steps": ["EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"],
        "review_mode": "step_by_step",
        "tokens": 3000,
        "latency_ms": 9000,
    },
    {
        "case_id": "N1",
        "predicted_class": "composed",
        "predicted_steps": ["SOLE_SOURCE_FORM", "HOLD_PO"],
        "review_mode": "step_by_step",
        "novel_combination": True,
        "tokens": 3000,
        "latency_ms": 8000,
    },
    {
        "case_id": "U1",
        "predicted_class": "unknown",
        "predicted_steps": ["VERIFY_GST_STATUS", "HOLD_PO"],
        "review_mode": "escalate",
        "tokens": 1000,
        "latency_ms": 3000,
    },
    {
        "case_id": "U2",
        "predicted_class": "normal",
        "predicted_steps": ["STANDARD_APPROVAL"],
        "review_mode": "",
        "tokens": 900,
        "latency_ms": 2000,
    },  # false confidence, and a floor violation
    {
        "case_id": "P1",
        "predicted_class": "known",
        "predicted_steps": ["ROUTE_DELEGATE"],
        "review_mode": "one_click",
        "tokens": 1500,
        "latency_ms": 5000,
    },  # outdated lesson use
]


def test_f1_edges():
    assert f1(set(), set()) == 1.0 and f1({"A"}, {"B"}) == 0.0 and round(f1({"A", "B"}, {"A"}), 3) == 0.667


def test_floor_requirements_from_ground_truth():
    assert floor_required(GT["C1"]) == {"VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"}
    assert floor_required(GT["U1"]) == {"VERIFY_GST_STATUS", "HOLD_PO"}
    assert floor_required(GT["U2"]) == {"DECLARE_CONFLICT_OF_INTEREST"}


def test_false_confidence_counts_unescalated_unknowns():
    c = m1_false_confidence(PRED, GT)
    assert (c.x, c.n, c.cases) == (1, 2, ["U2"]) and str(c) == "1 of 2"


def test_all_metrics_counts():
    m = all_metrics(PRED, GT, A)
    assert m["M2_floor_violations"]["text"] == "1 of 3"  # U2 lacks the COI declaration
    assert m["M3_classification"]["correct"]["text"] == "5 of 6"
    assert m["M3_classification"]["matrix"]["unknown"]["normal"] == 1
    assert m["M5_interaction"]["exact_match"]["text"] == "1 of 2"
    assert m["M5_interaction"]["novel_flagged"]["text"] == "1 of 1"
    assert m["M6_outdated_lesson_use"]["text"] == "1 of 1"
    assert m["M7_post_override_correctness"]["text"] == "0 of 1"
    assert m["M10_unnecessary_escalations"]["text"] == "0 of 4"
    assert m["M11_cost_latency"]["tokens_per_case"] == 1900 and m["M11_cost_latency"]["p95_s"] == 9.0


def test_review_effort_and_minutes():
    e = m8_review_effort(PRED, GT)
    # K1: 1 click; C1: 3 confirmations; N1: 2 confirmations + 1 edit; U1: 1 escalation;
    # U2 (no review mode -> step by step): 1 confirmation + 2 edits; P1: 1 click + 1 edit
    assert (e["escalations"], e["edits"], e["confirmations"]) == (1, 4, 8) and e["per_10_cases"] == 21.7
    mins = m9_minutes(PRED, GT, A)
    # K1 1, C1 6, N1 6+2, U1 40, U2 6+4, P1 1+2 = 68 over 6 exception cases
    assert mins["per_10_exception_cases"] == 113.3 and mins["baseline_per_10"] == 400


def test_replay_summary_counts_exception_cases_only():
    from api.metrics import replay_summary

    rows = [
        {
            "gt_class": "normal",
            "predicted_class": "normal",
            "review_mode": "one_click",
            "false_confidence": False,
            "effort": 1,
        },
        {
            "gt_class": "known",
            "predicted_class": "known",
            "review_mode": "one_click",
            "false_confidence": False,
            "effort": 1,
        },
        {
            "gt_class": "unknown",
            "predicted_class": "unknown",
            "review_mode": "escalate",
            "false_confidence": False,
            "effort": 3,
        },
    ]
    s = replay_summary(rows)
    assert s["exception_cases"] == 2
    assert s["one_click"] == "1 of 2" and s["escalations"] == "1 of 2" and s["false_confidence"] == "0 of 2"
    assert s["classes_correct"] == "3 of 3" and s["mean_effort"] == 2.0
