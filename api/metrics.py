"""Benchmark metrics M1-M11 (SPEC §10), computed in code from predictions and ground truth.

Owns: every number the benchmark reports, as counts ("x of n") where the SPEC asks for counts. Pure functions
over plain dicts: a prediction row as eval/run_arms.py writes it, and a ground-truth case as
docs/ground_truth_format.md defines it.
Never: calls an LLM, reads files, or lets any model compute a number (CLAUDE.md rule 3). The engine never
imports this module (rule 10: ground truth stays out of api/engine and api/memory).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

CLASSES = ("normal", "known", "generalized", "composed", "unknown")
EXCEPTION_CLASSES = ("known", "generalized", "composed", "unknown")


@dataclass
class Count:
    x: int
    n: int
    cases: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.x} of {self.n}"


def _pairs(preds: list[dict], gts: dict[str, dict]) -> list[tuple[dict, dict]]:
    return [(p, gts[p["case_id"]]) for p in preds if p["case_id"] in gts]


def f1(pred: set[str], gold: set[str]) -> float:
    if not pred and not gold:
        return 1.0
    tp = len(pred & gold)
    if tp == 0:
        return 0.0
    precision, recall = tp / len(pred), tp / len(gold)
    return 2 * precision * recall / (precision + recall)


def escalated(p: dict) -> bool:
    return p.get("review_mode") == "escalate" or p.get("predicted_class") == "unknown"


def floor_required(gt: dict) -> set[str]:
    """SPEC §6.3 F1, F3, F4 from the ground truth's failed checks and causes."""
    req: set[str] = set()
    checks = set(gt.get("failed_checks", []))
    if "bank" in checks:
        req |= {"VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"}
    if "related_party" in checks:
        req |= {"DECLARE_CONFLICT_OF_INTEREST"}
    if gt.get("causes", {}).get("vendor") == "gst_cancelled":
        req |= {"VERIFY_GST_STATUS", "HOLD_PO"}
    return req


def m1_false_confidence(preds: list[dict], gts: dict[str, dict]) -> Count:
    """Some failed check has no valid precedent, yet the system marked everything covered and didn't escalate."""
    rows = [(p, g) for p, g in _pairs(preds, gts) if g.get("uncovered_checks") or g["class"] == "unknown"]
    bad = [p["case_id"] for p, _ in rows if not escalated(p)]
    return Count(len(bad), len(rows), bad)


def m2_floor_violations(preds: list[dict], gts: dict[str, dict]) -> Count:
    rows = [(p, g) for p, g in _pairs(preds, gts) if floor_required(g)]
    bad = [p["case_id"] for p, g in rows if not floor_required(g) <= set(p.get("predicted_steps", []))]
    return Count(len(bad), len(rows), bad)


def m3_confusion(preds: list[dict], gts: dict[str, dict]) -> dict[str, Any]:
    matrix = {gold: {pred: 0 for pred in CLASSES} for gold in CLASSES}
    pairs = _pairs(preds, gts)
    for p, g in pairs:
        matrix[g["class"]][p["predicted_class"] if p["predicted_class"] in CLASSES else "unknown"] += 1
    right = [p["case_id"] for p, g in pairs if p["predicted_class"] == g["class"]]
    wrong = [p["case_id"] for p, g in pairs if p["predicted_class"] != g["class"]]
    # Like every Count, `cases` lists the cases counted in x; the misclassified ones are listed separately.
    return {"matrix": matrix, "correct": Count(len(right), len(pairs), right), "misclassified": wrong}


NO_EXCEPTION_DEFAULT = {"STANDARD_APPROVAL"}  # SPEC §9's normal-case step; ground truth writes [] for it


def steps_for_f1(steps: list[str]) -> set[str]:
    return set(steps) - NO_EXCEPTION_DEFAULT


def m4_procedure_f1(preds: list[dict], gts: dict[str, dict]) -> dict[str, float | None]:
    """Mean step-set F1 per ground-truth class, and the mean of those class means. STANDARD_APPROVAL is
    ignored on both sides for every arm (a convention difference, not a procedure difference)."""
    by: dict[str, list[float]] = {c: [] for c in CLASSES}
    for p, g in _pairs(preds, gts):
        by[g["class"]].append(
            f1(steps_for_f1(p.get("predicted_steps", [])), steps_for_f1(g.get("steps", [])))
        )
    out: dict[str, float | None] = {c: round(mean(v), 3) if v else None for c, v in by.items()}
    present = [v for v in out.values() if v is not None]
    out["macro"] = round(mean(present), 3) if present else None
    return out


def m5_interaction(preds: list[dict], gts: dict[str, dict]) -> dict[str, Any]:
    rows = [(p, g) for p, g in _pairs(preds, gts) if g.get("interaction")]
    exact = [p["case_id"] for p, g in rows if set(p.get("predicted_steps", [])) == set(g.get("steps", []))]
    novel = [(p, g) for p, g in rows if g.get("novel_combination")]
    flagged = [p["case_id"] for p, _ in novel if p.get("novel_combination")]
    return {
        "exact_match": Count(len(exact), len(rows), exact),
        "mean_f1": round(
            mean(f1(set(p.get("predicted_steps", [])), set(g.get("steps", []))) for p, g in rows), 3
        )
        if rows
        else None,
        "novel_flagged": Count(len(flagged), len(novel), flagged),
    }


def m6_outdated_lesson_use(preds: list[dict], gts: dict[str, dict]) -> Count:
    rows = [(p, g) for p, g in _pairs(preds, gts) if g.get("post_july_capex_approver")]
    bad = [p["case_id"] for p, _ in rows if "ADD_CONTROLLER_SIGNOFF" not in p.get("predicted_steps", [])]
    return Count(len(bad), len(rows), bad)


def m7_post_override(preds: list[dict], gts: dict[str, dict]) -> Count:
    rows = [(p, g) for p, g in _pairs(preds, gts) if g.get("after_override")]
    ok = [p["case_id"] for p, g in rows if set(p.get("predicted_steps", [])) == set(g.get("steps", []))]
    return Count(len(ok), len(rows), ok)


def reviewer_cost(p: dict, g: dict) -> dict[str, int]:
    """The simulated reviewer (SPEC §10 M8): ground truth is the reviewer's answer.

    Escalated: 1 escalation (the human researches and resolves it). Otherwise: edits = the symmetric difference
    with the ground-truth steps, plus confirmations (one per step step-by-step, one per case one-click). Arms
    without a review mode (A and B) are reviewed step by step.
    """
    if escalated(p):
        return {"escalations": 1, "edits": 0, "confirmations": 0}
    pred, gold = set(p.get("predicted_steps", [])), set(g.get("steps", []))
    confirmations = 1 if p.get("review_mode") == "one_click" else len(pred)
    return {"escalations": 0, "edits": len(pred ^ gold), "confirmations": confirmations}


def m8_review_effort(preds: list[dict], gts: dict[str, dict]) -> dict[str, Any]:
    pairs = _pairs(preds, gts)
    costs = [reviewer_cost(p, g) for p, g in pairs]
    total = {k: sum(c[k] for c in costs) for k in ("escalations", "edits", "confirmations")}
    effort = sum(total.values())
    return {
        "per_10_cases": round(effort * 10 / len(pairs), 1) if pairs else None,
        **total,
        "cases": len(pairs),
    }


def m9_minutes(preds: list[dict], gts: dict[str, dict], a: dict[str, float]) -> dict[str, Any]:
    """Estimated analyst minutes per 10 exception cases vs researching every exception from scratch.
    ASSUMPTIONS from config/assumptions.yaml, shown next to the figure wherever it appears."""
    rows = [(p, g) for p, g in _pairs(preds, gts) if g["class"] in EXCEPTION_CLASSES]
    minutes = 0.0
    for p, g in rows:
        c = reviewer_cost(p, g)
        if c["escalations"]:
            minutes += a["escalation_min"]
        else:
            review = (
                a["one_click_review_min"]
                if p.get("review_mode") == "one_click"
                else a["step_by_step_review_min"]
            )
            minutes += review + c["edits"] * a["edit_min"]
    n = len(rows)
    return {
        "per_10_exception_cases": round(minutes * 10 / n, 1) if n else None,
        "baseline_per_10": round(a["research_unfamiliar_exception_min"] * 10, 1),
        "exception_cases": n,
        "assumptions": a,
    }


def m10_unnecessary_escalations(preds: list[dict], gts: dict[str, dict]) -> Count:
    rows = [(p, g) for p, g in _pairs(preds, gts) if g["class"] in ("known", "generalized", "composed")]
    bad = [p["case_id"] for p, _ in rows if p.get("predicted_class") == "unknown"]
    return Count(len(bad), len(rows), bad)


def _pct(values: list[int], q: float) -> int | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def m11_cost(preds: list[dict]) -> dict[str, Any]:
    tokens = [int(p.get("tokens", 0)) for p in preds]
    lat = [int(p.get("latency_ms", 0)) for p in preds]
    models = sorted({m for p in preds for m in p.get("models", [])})
    return {
        "cases": len(preds),
        "tokens_per_case": round(mean(tokens)) if tokens else None,
        "p50_s": round(_pct(lat, 0.5) / 1000, 1) if lat else None,
        "p95_s": round(_pct(lat, 0.95) / 1000, 1) if lat else None,
        "models_used": models,  # a Gemini fallback here must be reported (SPEC §14.1)
    }


def replay_summary(rows: list[dict]) -> dict[str, Any]:
    """Totals for one learning-curve replay (eval/replay.py rows), over its exception cases."""
    exc = [r for r in rows if r["gt_class"] != "normal"]
    n = len(exc)
    return {
        "exception_cases": n,
        "one_click": str(Count(sum(r["review_mode"] == "one_click" for r in exc), n)),
        "escalations": str(Count(sum(r["review_mode"] == "escalate" for r in exc), n)),
        "false_confidence": str(Count(sum(bool(r["false_confidence"]) for r in exc), n)),
        "classes_correct": str(Count(sum(r["gt_class"] == r["predicted_class"] for r in rows), len(rows))),
        "mean_effort": round(mean(r["effort"] for r in exc), 2) if exc else None,
    }


def all_metrics(preds: list[dict], gts: dict[str, dict], assumptions: dict[str, float]) -> dict[str, Any]:
    def plain(v: Any) -> Any:
        if isinstance(v, Count):
            return asdict(v) | {"text": str(v)}
        if isinstance(v, dict):
            return {k: plain(x) for k, x in v.items()}
        return v

    return plain(
        {
            "M1_false_confidence": m1_false_confidence(preds, gts),
            "M2_floor_violations": m2_floor_violations(preds, gts),
            "M3_classification": m3_confusion(preds, gts),
            "M4_procedure_f1": m4_procedure_f1(preds, gts),
            "M5_interaction": m5_interaction(preds, gts),
            "M6_outdated_lesson_use": m6_outdated_lesson_use(preds, gts),
            "M7_post_override_correctness": m7_post_override(preds, gts),
            "M8_review_effort": m8_review_effort(preds, gts),
            "M9_minutes": m9_minutes(preds, gts, assumptions),
            "M10_unnecessary_escalations": m10_unnecessary_escalations(preds, gts),
            "M11_cost_latency": m11_cost(preds),
        }
    )
