"""Benchmark report (SPEC §14.2, §10): scores each arm's latest run on a split against the frozen ground truth.

Owns: loading run files (eval/results/run-bench-<split>-<arm>-*.json; arm C's file also holds arm E) and
data/ground_truth/<split>.json, computing M1-M11 with api/metrics.py, and writing
eval/results/report-<split>-<time>.json. Numbers come only from api/metrics.py (CLAUDE.md rule 3).
Never: runs the engine or changes a prediction. Reading ground truth here is allowed; the engine never does.

Usage: python -m eval.report --split dev
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime

from api.metrics import all_metrics
from api.settings import ROOT, config

RESULTS = ROOT / "eval" / "results"


def latest_runs(split: str) -> dict[str, list[dict]]:
    by_arm: dict[str, list[dict]] = {}
    for f in sorted(RESULTS.glob(f"run-bench-{split}-*.json")):  # sorted by name: later timestamps win
        for row in json.loads(f.read_text(encoding="utf-8"))["rows"]:
            by_arm.setdefault(row["arm"], {})[row["case_id"]] = row  # type: ignore[index]
    return {arm: list(rows.values()) for arm, rows in by_arm.items()}  # type: ignore[union-attr]


def frozen_hash(split: str) -> str | None:
    """The ground truth's hash recorded at Gate G2 (data/labelling/FROZEN.json), if frozen."""
    manifest = ROOT / "data" / "labelling" / "FROZEN.json"
    if not manifest.exists():
        return None
    return json.loads(manifest.read_text(encoding="utf-8")).get(split, {}).get("sha256")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    args = ap.parse_args()
    gt_path = ROOT / "data" / "ground_truth" / f"{args.split}.json"
    if not gt_path.exists():
        print(
            f"No ground truth at {gt_path.relative_to(ROOT)}; the data owner writes it (docs/ground_truth_format.md)."
        )
        return 2
    frozen = frozen_hash(args.split)
    actual = hashlib.sha256(gt_path.read_bytes()).hexdigest()
    if frozen is None:
        print(
            f"Ground truth for {args.split} is not frozen (data/labelling/FROZEN.json); freeze it at Gate G2 first."
        )
        return 2
    if frozen != actual:
        print(
            f"REFUSING: {gt_path.relative_to(ROOT)} changed after it was frozen (hash {actual[:12]} != {frozen[:12]})."
        )
        return 3
    gts = json.loads(gt_path.read_text(encoding="utf-8"))["cases"]
    runs = latest_runs(args.split)
    if not runs:
        print(f"No runs for split {args.split} in {RESULTS.relative_to(ROOT)}.")
        return 2
    assumptions = config("assumptions")
    report = {arm: all_metrics(rows, gts, assumptions) for arm, rows in sorted(runs.items())}
    out = RESULTS / f"report-{args.split}-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    out.write_text(
        json.dumps({"split": args.split, "arms": report, "assumptions": assumptions}, indent=2),
        encoding="utf-8",
    )
    print(
        f"{'arm':<4} {'false conf.':<12} {'floor viol.':<12} {'classes':<10} {'proc. F1':<9} {'effort/10':<10} "
        f"{'min/10 exc.':<11} tokens/case"
    )
    for arm, m in report.items():
        print(
            f"{arm:<4} {m['M1_false_confidence']['text']:<12} {m['M2_floor_violations']['text']:<12} "
            f"{m['M3_classification']['correct']['text']:<10} {str(m['M4_procedure_f1']['macro']):<9} "
            f"{str(m['M8_review_effort']['per_10_cases']):<10} {str(m['M9_minutes']['per_10_exception_cases']):<11} "
            f"{m['M11_cost_latency']['tokens_per_case']}"
        )
    print(f"Minutes use ASSUMPTIONS (config/assumptions.yaml): {assumptions}")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
