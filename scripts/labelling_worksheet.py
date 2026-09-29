"""Labelling worksheet: one page per case for the data owner, with the blanks to fill (SPEC §13 step 2).

Owns: rendering each spec's generated request text, its `ledger` facts and its `scenario_checks` (how the case
was built) into data/labelling/<split>_worksheet.md, plus a JSON skeleton in the ground-truth format with every
answer field blank. The data owner fills the skeleton, then saves it as data/ground_truth/<split>.json.
Never: suggests a class, steps or coverage, runs the engine, or writes to data/ground_truth/.

Usage: python -m scripts.labelling_worksheet --split dev
"""

from __future__ import annotations

import argparse
import json

from api.settings import ROOT

OUT = ROOT / "data" / "labelling"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    args = ap.parse_args()
    specs = [
        s
        for s in json.loads((ROOT / "data" / "cases" / "specs.json").read_text(encoding="utf-8"))["specs"]
        if s["split"] == args.split
    ]
    lines = [
        f"# Labelling worksheet: {args.split} ({len(specs)} cases). SYNTHETIC DATA.",
        "",
        "Label blind: don't look at any system output. Use `config/verdict_guide.md` (copy it into",
        "`data/ground_truth/LABELLING_GUIDE.md` with the family rules), `data/seed/history.csv` for the",
        "precedents, and `data/seed/policy.md` for uncovered cases. The format is `docs/ground_truth_format.md`.",
        f"Fill `data/labelling/{args.split}_skeleton.json`, then save it as `data/ground_truth/{args.split}.json`.",
        "",
    ]
    skeleton = {"labeller": "", "second_labeller": "", "frozen_at": "", "cases": {}}
    for s in specs:
        form_path = ROOT / "data" / "cases" / args.split / f"{s['case_id']}.json"
        form = json.loads(form_path.read_text(encoding="utf-8")) if form_path.exists() else {}
        lines += [
            f"## {s['case_id']} · {s['submitted_at'][:10]} · {s['vendor_name']} · {s['amount_raw']} · "
            f"{s['cost_centre']} · {s['quotes_attached']} quote(s)",
            "",
            f"**Justification:** {form.get('justification', '(not generated yet)')}",
            "",
            f"**Email thread:** {form.get('email_thread') or '(none)'}",
            "",
            f"**Attachment:** {form.get('attachment_text') or '(none)'}",
            "",
            "**Ledger on that date:**",
            "",
            *[f"- {fact}" for fact in (s["ledger"] if isinstance(s["ledger"], list) else [s["ledger"]])],
            "",
            f"**Built to fail:** {', '.join(f'{k} ({v})' for k, v in s['scenario_checks'].items()) or 'nothing'}",
            "",
            "**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · "
            "novel_combination · post_july_capex_approver · after_override · adversarial",
            "",
        ]
        skeleton["cases"][s["case_id"]] = {
            "class": "",
            "failed_checks": [],
            "causes": {},
            "uncovered_checks": [],
            "steps": [],
            "family": s["family"],
            "interaction": None,
            "novel_combination": None,
            "post_july_capex_approver": None,
            "after_override": None,
            "adversarial": None,
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.split}_worksheet.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / f"{args.split}_skeleton.json").write_text(json.dumps(skeleton, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote data/labelling/{args.split}_worksheet.md and {args.split}_skeleton.json ({len(specs)} cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
