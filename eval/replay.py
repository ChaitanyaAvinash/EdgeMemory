"""Learning curve (SPEC §14.4): replay seeds and test cases in date order from an empty memory.

Owns: for one backend (hindsight = arm C, vector = arm D), starting from an empty bank, walking seeds and cases
in date order. A seed is retained as history. A case goes through pipeline.run_case, and then the simulated
reviewer retains the ground-truth resolution through the same decision path as the UI. It records one row
per case and computes four curves: the rolling share of one-click reviews, review effort (M8), false
confidence (M1, which should stay 0) and maturity per family over time.
- Only labelled cases are replayed (the reduced test set, SPEC §14.6, labels 24 of 40).
- The ground truth's `uncovered_checks` are relative to the seed history. In a replay, a check stops being
  uncovered once an earlier replayed case with the same check and cause has been resolved and retained, so
  using that precedent is not counted as false confidence (`still_uncovered`).
- `--run ID --resume` continues a replay across quota days: it keeps the bank and ledger, skips processed
  events, saves after every event, and stops cleanly when the primary model's quota runs low.
Never: tunes anything, or runs without the quota guard (`make budget` first).

Usage: python -m eval.replay --backend hindsight|vector --split test [--limit N] [--force] [--run ID [--resume]]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, date, datetime
from typing import Any

from sqlmodel import Session

from api import ledger
from api.engine.pipeline import load_master_json, run_case
from api.engine.retain import retain_decision
from api.llm import LLM, LLMUnavailable
from api.memory.hindsight_backend import HindsightBackend
from api.memory.vector_backend import VectorBackend
from api.metrics import escalated, reviewer_cost
from api.settings import ROOT, config
from eval.run_arms import CASE_MARGIN_TOKENS, RESULTS, RUNS, form_of, load_dataset, quota_check
from scripts.import_history import import_to_ledger, import_to_memory

WINDOW = 10  # exception cases in the rolling one-click share


def curves(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """The four SPEC §14.4 series from per-case rows (pure; unit-tested)."""
    exc = [r for r in rows if r["gt_class"] != "normal"]
    one_click, effort, fc, maturity = [], [], [], []
    cum_effort = cum_fc = 0
    for i, r in enumerate(exc):
        win = exc[max(0, i - WINDOW + 1) : i + 1]
        one_click.append(
            {
                "i": i + 1,
                "date": r["date"],
                "share": sum(x["review_mode"] == "one_click" for x in win),
                "of": len(win),
            }
        )
        cum_effort += r["effort"]
        effort.append({"i": i + 1, "date": r["date"], "per_case": round(cum_effort / (i + 1), 2)})
        cum_fc += int(r["false_confidence"])
        fc.append({"i": i + 1, "date": r["date"], "false_confidence": cum_fc})
        maturity.append({"i": i + 1, "date": r["date"], "family": r["family"], "maturity": r["maturity"]})
    return {
        "one_click_share": one_click,
        "review_effort": effort,
        "false_confidence": fc,
        "maturity": maturity,
    }


def still_uncovered(gt: dict, resolved: set[tuple[str, str]]) -> list[str]:
    """The ground truth's uncovered checks that no earlier replayed resolution has since covered (pure)."""
    causes = gt.get("causes", {})
    return [c for c in gt.get("uncovered_checks", []) if (c, causes.get(c, "")) not in resolved]


def action_for(pred_steps: list[str], gt: dict, review_mode: str) -> str:
    """What the simulated reviewer does: approve/confirm when the recommendation matches, else edit or resolve."""
    if review_mode == "escalate":
        return "resolve"
    if set(pred_steps) == set(gt["steps"]):
        return "approve" if review_mode == "one_click" else "confirm"
    return "edit"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=["hindsight", "vector"])
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--run", help="run id (default: timestamp)")
    ap.add_argument(
        "--resume", action="store_true", help="continue --run ID: keep its bank, skip done events"
    )
    args = ap.parse_args()
    if args.resume and not args.run:
        raise SystemExit("--resume needs --run ID")
    gt_path = ROOT / "data" / "ground_truth" / f"{args.split}.json"
    if not gt_path.exists():
        print("No ground truth yet; the replay's simulated reviewer needs it (docs/ground_truth_format.md).")
        return 2
    gts = json.loads(gt_path.read_text(encoding="utf-8"))["cases"]
    master, history, cases, _ = load_dataset("bench", args.split)
    cases = [c for c in cases if gts.get(c["request_id"], {}).get("class")]  # labelled cases only
    cases = cases[: args.limit] if args.limit else cases
    llm = LLM()
    primary = config("models")["roles"]["verifier"]["model"]

    run_id = args.run or datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    bank = f"kaveri-replay-{args.backend}-{run_id}".lower()
    backend = HindsightBackend(bank) if args.backend == "hindsight" else VectorBackend(bank)
    arm = "C" if args.backend == "hindsight" else "D"
    RUNS.mkdir(parents=True, exist_ok=True)
    db = RUNS / f"replay-{args.backend}-{run_id}.db"
    if not args.resume:
        db.unlink(missing_ok=True)
    eng = ledger.engine(f"sqlite:///{db}")
    out_path = RESULTS / f"replay-{args.backend}-{args.split}-{run_id}.json"

    rows: list[dict[str, Any]] = []
    done: list[str] = []
    resolved: set[tuple[str, str]] = set()
    if args.resume and out_path.exists():
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        rows, done = prev["rows"], prev["done_events"]
        resolved = {(c, k) for c, k in prev["resolved"]}
        print(f"resuming {run_id}: {len(done)} events done, {len(rows)} cases scored", flush=True)
    todo = sum(1 for c in cases if f"case:{c['request_id']}" not in done)
    quota_check(arm, todo, llm, args.force)

    def save() -> None:
        RESULTS.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "backend": args.backend,
                    "bank": bank,
                    "run_id": run_id,
                    "rows": rows,
                    "curves": curves(rows),
                    "done_events": done,
                    "resolved": sorted(resolved),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    events = [(r.get("resolved_at") or r.get("effective_date"), "seed", r) for r in history]
    events += [(c["submitted_at"][:10], "case", c) for c in cases]
    events.sort(key=lambda e: (e[0], e[1] == "case"))
    with Session(eng) as s:
        if not done:
            load_master_json(s, master)
            await backend.ensure_bank()
        for when, kind, item in events:
            key = f"{kind}:{item['case_id'] if kind == 'seed' else item['request_id']}"
            if key in done:
                continue
            if kind == "seed":
                import_to_ledger([item], s)
                await import_to_memory([item], backend, s)
                done.append(key)
                save()
                continue
            left = llm.limiter.tokens_remaining_today(primary)
            if left is not None and left < CASE_MARGIN_TOKENS:
                print(f"stopping before {item['request_id']}: {left} tokens left on {primary}; resume later")
                break
            form = form_of(item)
            gt = gts[form.request_id]
            try:
                out = await run_case(form, s, backend, llm, arm=arm)
            except LLMUnavailable as e:
                if "quota" in str(e) or "429" in str(e):
                    print(
                        f"stopping at {form.request_id} on quota ({str(e)[:160]}); resume later", flush=True
                    )
                    break
                raise
            cls = out.detection.classification.cls
            steps = [x.code for x in out.composition.steps] if out.composition else []
            pred = {
                "case_id": form.request_id,
                "predicted_class": cls,
                "predicted_steps": steps,
                "review_mode": out.review_mode,
            }
            open_checks = still_uncovered(gt, resolved)
            rows.append(
                {
                    "case_id": form.request_id,
                    "date": when,
                    "family": gt.get("family", ""),
                    "gt_class": gt["class"],
                    "predicted_class": cls,
                    "review_mode": out.review_mode,
                    "maturity": out.maturity,
                    "uncovered_in_replay": open_checks,
                    "false_confidence": bool(open_checks) and not escalated(pred),
                    "effort": sum(reviewer_cost(pred, gt).values()),
                }
            )
            if gt["class"] != "normal":
                await retain_decision(
                    s,
                    backend,
                    form.request_id,
                    action_for(steps, gt, out.review_mode),
                    gt["steps"],
                    "simulated reviewer: ground-truth resolution",
                    "replay",
                    "",
                    date.fromisoformat(when),
                    arm=arm,
                )
                resolved |= {(c, gt.get("causes", {}).get(c, "")) for c in gt.get("failed_checks", [])}
            done.append(key)
            save()
            print(
                f"{when} {form.request_id:<10} replayed", flush=True
            )  # predictions stay in the results file
    if hasattr(backend, "aclose"):
        await backend.aclose()
    save()
    print(f"wrote {out_path.relative_to(ROOT)} ({len(rows)} of {len(cases)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
