"""Case-spec checker (SPEC §13): confirms each benchmark spec builds the scenario it describes.

Owns: for every spec in data/cases/specs.json, rebuilding the request facts from the spec's form fields (amount
parsed and vendor matched in code, the spec's `text_signals` injected as given), running the six ledger checks
(rules.py) against data/master/master.json plus the other requests of the same split, and comparing the result
with the spec's `scenario_checks`. Also checks the SPEC §13 family mix, dates, form fields and the `ledger`
summary each spec carries for the labeller (which must match the master data it was written from).
Never: calls an LLM or memory, verifies precedents, classifies or composes, or reads data/ground_truth/. It
checks how each scenario was built, not what the system answers. Synthetic data only.

Spec fields beyond the generator's own (scripts/generate_cases.py), all never sent to the LLM:
  vendor_id, amount (integer rupees), category, urgency: the scenario's facts (SPEC §13 step 1).
  text_signals: [{name, source}] signals the narrative must carry (bank_change_claimed, related_party).
  scenario_checks: {check: cause} the checks the scenario is built to fail, in the rule engine's vocabulary.
  ledger: plain-words master-data facts on the request date, which the narrative needn't mention.

Usage: python -m scripts.check_specs [data/cases/specs.json] [--show ID]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from api.engine.normalise import match_vendor, parse_amount
from api.engine.rules import (
    BANK_WINDOW_DAYS,
    DUPLICATE_WINDOW_DAYS,
    QUOTES_REQUIRED,
    QUOTES_THRESHOLD,
    approver_for,
    inr,
    run_checks,
)
from api.engine.types import (
    ApprovalLimitRec,
    BudgetRec,
    DelegationRec,
    EmployeeRec,
    MasterData,
    PriorRequestRec,
    RequestFacts,
    Signal,
    VendorRec,
    fiscal_year,
)
from api.settings import ROOT

SPECS = ROOT / "data" / "cases" / "specs.json"
MASTER = ROOT / "data" / "master" / "master.json"

SPLITS = {"dev": 20, "test": 40}
FIRST_DAY = date(2026, 8, 26)  # after the last seed resolution (2026-08-25), so replay order is seeds first
LAST_DAY = date(2027, 3, 31)  # FY 2026-27 is the only budget year in the master data
CATEGORIES = {"direct_material", "indirect_mro", "capex", "services"}
URGENCIES = {"line_down", "urgent", "normal"}
SIGNALS = {"bank_change_claimed": "bank", "related_party": "related_party"}
SOURCES = {"justification", "email_thread", "attachment_text"}
POLICY_DAY = date(2026, 7, 1)
# SPEC §13 benchmark mix, as fixed family counts (the rest is E1-E6 singles and pairs).
FAMILY_COUNTS = {"normal": 10, "adversarial": 6, "I1": 2, "I2": 4, "I3": 2, "U1": 4, "U2": 3}
IN_TEST_ONLY = {"I1", "I2", "I3"}  # all 8 interaction cases are scored on test (SPEC §10 M5, §14.6)
# Words that would leak a label to the narrative LLM if they appeared in a story.
LABEL_WORDS = ("known", "generalized", "generalised", "composed", "unknown", "adversarial")
REQUIRED = {
    "case_id": str,
    "split": str,
    "family": str,
    "submitted_at": str,
    "requester_id": str,
    "cost_centre": str,
    "vendor_name": str,
    "vendor_id": str,
    "amount": int,
    "amount_raw": str,
    "quotes_attached": int,
    "category": str,
    "urgency": str,
    "story": str,
    "must_mention": list,
    "email_messages": int,
    "certificate_snippet": bool,
    "hinglish": bool,
    "text_signals": list,
    "scenario_checks": dict,
    "ledger": list,
}


def load(specs_path: Path = SPECS, master_path: Path = MASTER) -> tuple[list[dict], dict]:
    specs = json.loads(specs_path.read_text(encoding="utf-8"))["specs"]
    return specs, json.loads(master_path.read_text(encoding="utf-8"))


def day(spec: dict) -> date:
    return datetime.fromisoformat(spec["submitted_at"]).date()


def master_data(master: dict, split_specs: list[dict]) -> MasterData:
    """The ledger a run of one split sees: master data plus that split's other requests as priors."""
    d = date.fromisoformat

    def opt(x: str | None) -> date | None:
        return d(x) if x else None

    priors = [
        PriorRequestRec(p["id"], p["vendor_id"], p["amount"], d(p["submitted_on"]))
        for p in master["prior_requests"]
    ]
    priors += [PriorRequestRec(s["case_id"], s["vendor_id"], s["amount"], day(s)) for s in split_specs]
    return MasterData(
        vendors={
            v["id"]: VendorRec(
                v["id"],
                v["name"],
                v["gstin"],
                v["gst_status"],
                v["status"],
                v["cert_name"],
                opt(v["cert_expiry"]),
                opt(v["bank_changed_at"]),
                v["sole_source"],
                v["category"],
            )
            for v in master["vendors"]
        },
        employees={
            e["id"]: EmployeeRec(
                e["id"], e["name"], e["role"], e["cost_centre"], opt(e["leave_from"]), opt(e["leave_to"])
            )
            for e in master["employees"]
        },
        approval_limits=[
            ApprovalLimitRec(a["cost_centre"], a["max_amount"], a["approver_id"])
            for a in master["approval_limits"]
        ],
        delegations=[
            DelegationRec(
                x["approver_id"], x["delegate_id"], x["max_amount"], d(x["valid_from"]), d(x["valid_to"])
            )
            for x in master["delegations"]
        ],
        budgets={
            (b["cost_centre"], b["fiscal_year"]): BudgetRec(
                b["cost_centre"], b["fiscal_year"], b["allocated"], b["spent"]
            )
            for b in master["budgets"]
        },
        prior_requests=priors,
    )


def facts_for(spec: dict, md: MasterData) -> RequestFacts:
    """Request facts as the pipeline would build them, with the spec's text signals standing in for extraction."""
    return RequestFacts(
        id=spec["case_id"],
        submitted_on=day(spec),
        vendor_id=match_vendor(spec["vendor_name"], md.vendors),
        vendor_name_raw=spec["vendor_name"],
        amount=parse_amount(spec["amount_raw"]),
        cost_centre=spec["cost_centre"],
        category=spec["category"],
        urgency=spec["urgency"],
        requester_id=spec["requester_id"],
        quotes_count=spec["quotes_attached"],
        signals=[Signal(s["name"], s["source"], "(from the narrative)") for s in spec["text_signals"]],
    )


def ledger_view(spec: dict, md: MasterData) -> list[str]:
    """Master-data facts on the request date, in plain words, for the labeller (the text needn't state them)."""
    d, amount, cc = day(spec), spec["amount"], spec["cost_centre"]
    lines = []
    v = md.vendors.get(spec["vendor_id"])
    if v is None:
        lines.append(f"Vendor '{spec['vendor_name']}' is not in the vendor master.")
    else:
        parts = [f"Vendor {v.id} {v.name}: {v.status}", f"GST registration {v.gst_status}"]
        if v.cert_expiry and v.cert_expiry < d:
            parts.append(
                f"{v.cert_name} certificate expired {v.cert_expiry} ({(d - v.cert_expiry).days} days before the request)"
            )
        elif v.cert_expiry:
            parts.append(f"{v.cert_name} certificate valid until {v.cert_expiry}")
        age = (d - v.bank_changed_at).days if v.bank_changed_at else None
        if age is not None and 0 <= age <= BANK_WINDOW_DAYS:
            parts.append(f"bank details changed {v.bank_changed_at} ({age} days before the request)")
        else:
            parts.append(f"bank details not changed in the {BANK_WINDOW_DAYS} days before the request")
        parts.append("flagged sole-source" if v.sole_source else "not flagged sole-source")
        lines.append("; ".join(parts) + ".")
    fy = fiscal_year(d)
    b = md.budgets.get((cc, fy))
    if b is None:
        lines.append(f"No FY {fy} budget for {cc}.")
    else:
        left = b.allocated - b.spent
        s = f"Budget {cc} FY {fy}: {inr(max(left, 0))} left of {inr(b.allocated)}"
        if amount > left:
            s += f"; this request would take it {(b.spent + amount - b.allocated) / b.allocated * 100:.1f}% over"
        lines.append(s + ".")
    rule = approver_for(facts_for(spec, md), md)
    e = md.employees.get(rule.approver_id) if rule else None
    if e is None:
        lines.append(f"No approver configured for {cc} at {inr(amount)}.")
    elif e.on_leave(d):
        dels = [x for x in md.delegations if x.approver_id == e.id]
        who = "; ".join(
            f"delegate {x.delegate_id} ({md.employees[x.delegate_id].name}) up to {inr(x.max_amount)}, valid {x.valid_from} to {x.valid_to}"
            for x in dels
        )
        lines.append(
            f"Approver for {inr(amount)} in {cc}: {e.id} ({e.name}, {e.role}), on leave {e.leave_from} to {e.leave_to}; {who or 'no delegation on file'}."
        )
    else:
        lines.append(f"Approver for {inr(amount)} in {cc}: {e.id} ({e.name}, {e.role}), available.")
    lo = d - timedelta(days=DUPLICATE_WINDOW_DAYS)
    for p in sorted(md.prior_requests, key=lambda p: (p.submitted_on, p.id)):
        if p.vendor_id == spec["vendor_id"] and p.id != spec["case_id"] and lo <= p.submitted_on <= d:
            lines.append(
                f"Earlier request {p.id} to this vendor on {p.submitted_on} for {inr(p.amount)} "
                f"({(amount - p.amount) / p.amount * 100:+.1f}% against it)."
            )
    need = (
        f"{QUOTES_REQUIRED} needed above {inr(QUOTES_THRESHOLD)}"
        if amount > QUOTES_THRESHOLD
        else f"not required at or below {inr(QUOTES_THRESHOLD)}"
    )
    lines.append(f"Quotes: {spec['quotes_attached']} attached; {need}.")
    return lines


def _fields(spec: dict) -> list[str]:
    cid = spec.get("case_id", "?")
    out = [
        f"{cid}: missing or mistyped field '{k}'"
        for k, t in REQUIRED.items()
        if not isinstance(spec.get(k), t)
    ]
    if out:
        return out
    if spec["split"] not in SPLITS:
        out.append(f"{cid}: split '{spec['split']}' is not dev or test")
    if spec["category"] not in CATEGORIES:
        out.append(f"{cid}: category '{spec['category']}'")
    if spec["urgency"] not in URGENCIES:
        out.append(f"{cid}: urgency '{spec['urgency']}'")
    if not FIRST_DAY <= day(spec) <= LAST_DAY:
        out.append(f"{cid}: submitted {day(spec)} is outside {FIRST_DAY} to {LAST_DAY}")
    if parse_amount(spec["amount_raw"]) != spec["amount"]:
        out.append(
            f"{cid}: amount_raw '{spec['amount_raw']}' parses to {parse_amount(spec['amount_raw'])}, not {spec['amount']}"
        )
    if not 0 <= spec["email_messages"] <= 6:
        out.append(f"{cid}: email_messages must be 0-6")
    for s in spec["text_signals"]:
        if s.get("name") not in SIGNALS or s.get("source") not in SOURCES:
            out.append(f"{cid}: bad text signal {s}")
        if s.get("source") == "email_thread" and spec["email_messages"] < 2:
            out.append(f"{cid}: a signal in the email thread needs at least 2 messages")
    if spec["text_signals"] and not spec["must_mention"]:
        out.append(f"{cid}: a text signal needs a must_mention phrase to carry it")
    story = spec["story"].casefold()
    for w in (*LABEL_WORDS, spec["family"].casefold()):
        if f" {w}" in f" {story}" and w not in ("normal",):
            out.append(f"{cid}: story contains the label word '{w}'")
    return out


def check(specs: list[dict], master: dict) -> list[str]:
    """Every problem found, as one line each; empty when every spec builds its scenario."""
    problems = [p for s in specs for p in _fields(s)]
    if problems:
        return problems
    ids = Counter(s["case_id"] for s in specs)
    problems += [f"{cid}: duplicate case_id" for cid, n in ids.items() if n > 1]
    for split, n in SPLITS.items():
        got = sum(s["split"] == split for s in specs)
        if got != n:
            problems.append(f"split {split}: {got} specs, SPEC §13 wants {n}")
    fams = Counter(s["family"] for s in specs)
    problems += [
        f"family {f}: {fams[f]} specs, SPEC §13 wants {n}" for f, n in FAMILY_COUNTS.items() if fams[f] != n
    ]
    problems += [
        f"{s['case_id']}: interaction family {s['family']} belongs in test"
        for s in specs
        if s["family"] in IN_TEST_ONLY and s["split"] != "test"
    ]
    overrides = sum(s["family"].endswith("-override") for s in specs)
    if overrides != 3:
        problems.append(f"{overrides} after-override specs; SPEC §13 wants 3 (M7)")
    for split in SPLITS:
        group = [s for s in specs if s["split"] == split]
        md = master_data(master, group)
        m6 = 0
        for s in group:
            cid = s["case_id"]
            f = facts_for(s, md)
            if f.vendor_id != s["vendor_id"]:
                problems.append(
                    f"{cid}: vendor name '{s['vendor_name']}' matches {f.vendor_id}, not {s['vendor_id']}"
                )
                continue
            if s["requester_id"] not in md.employees:
                problems.append(f"{cid}: requester {s['requester_id']} is not in the employee master")
            fired = {v.check: v.cause for v in run_checks(f, md)}
            if fired != s["scenario_checks"]:
                problems.append(
                    f"{cid}: ledger checks give {fired or '{}'}; scenario_checks says {s['scenario_checks'] or '{}'}"
                )
            for sig in s["text_signals"]:
                if SIGNALS[sig["name"]] not in s["scenario_checks"]:
                    problems.append(f"{cid}: text signal {sig['name']} has no matching scenario check")
            if s["ledger"] != ledger_view(s, md):
                problems.append(
                    f"{cid}: stored ledger summary differs from the master data (re-run the builder or fix master.json)"
                )
            m6 += s["category"] == "capex" and day(s) >= POLICY_DAY and set(fired) == {"approver"}
        if split == "test" and m6 != 3:
            problems.append(f"test: {m6} post-July capex approver-away specs; SPEC §13 wants 3 (M6)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="?", type=Path, default=SPECS)
    ap.add_argument("--show", help="print one spec's form fields, scenario and ledger summary")
    args = ap.parse_args()
    specs, master = load(args.specs)
    if args.show:
        s = next((x for x in specs if x["case_id"] == args.show), None)
        if s is None:
            print(f"no spec {args.show}")
            return 1
        print(json.dumps(s, indent=2, ensure_ascii=False))
        return 0
    problems = check(specs, master)
    for p in problems:
        print(p)
    by_split = Counter(s["split"] for s in specs)
    print(f"{len(specs)} specs ({by_split['dev']} dev, {by_split['test']} test); {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
