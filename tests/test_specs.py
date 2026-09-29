"""check_specs.py: the 60 benchmark specs build the scenarios they describe against the master data (SPEC §13).

No LLM, memory, verifier or classifier runs here; only the six ledger checks on each spec's own facts.
"""

import copy

from scripts.check_specs import check, load

SPECS, MASTER = load()


def by_id(specs: list[dict], case_id: str) -> dict:
    return next(s for s in specs if s["case_id"] == case_id)


def test_every_spec_fires_exactly_its_scenario_checks():
    assert check(SPECS, MASTER) == []


def test_a_master_data_edit_that_breaks_a_scenario_is_caught():
    master = copy.deepcopy(MASTER)
    for e in master["employees"]:
        if e["id"] == "E-110":
            e["leave_from"] = e["leave_to"] = None  # the CC-ASSY capex approver-away case no longer fires
    problems = check(SPECS, master)
    assert any("ledger checks give {}" in p for p in problems)
    assert any("post-July capex approver-away" in p for p in problems)


def test_an_accidental_duplicate_is_caught():
    specs = copy.deepcopy(SPECS)
    lure = next(s for s in specs if s["family"] == "adversarial" and "PR-2026-0934" in s["must_mention"])
    lure.update(amount=105000, amount_raw="1,05,000")  # 5% off the earlier order: a duplicate after all
    assert any(lure["case_id"] in p and "possible_duplicate" in p for p in check(specs, MASTER))


def test_label_words_never_reach_the_story():
    specs = copy.deepcopy(SPECS)
    s = specs[0]
    s["story"] += " This one is composed."
    assert any(s["case_id"] in p and "label word" in p for p in check(specs, MASTER))
