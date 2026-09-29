"""generate_cases.py: required phrases are checked in code, and labels never reach the LLM."""

import json
from pathlib import Path

from scripts.generate_cases import Narrative, intake, missing_phrases, prompt_for

SPECS = json.loads(
    (Path(__file__).parents[1] / "data" / "cases" / "specs.example.json").read_text(encoding="utf-8")
)
SPEC = SPECS["specs"][0]


def test_missing_phrases_are_case_insensitive_across_all_fields():
    n = Narrative(
        justification="LINE 3 IS DOWN, cost centre Over Budget",
        email_thread="From: a / our New Bank Account is",
        attachment_text="",
    )
    assert missing_phrases(SPEC, n) == []
    short = Narrative(justification="line 3 is down, over budget", email_thread="", attachment_text="")
    assert missing_phrases(SPEC, short) == ["new bank account"]


def test_prompt_never_contains_the_family_label():
    p = prompt_for(SPEC)
    assert "I3" not in p.split() and "family" not in p.lower()
    assert "line 3 is down | over budget | new bank account" in p


def test_feedback_is_added_on_retry():
    assert "Fix your previous answer: include exactly: x" in prompt_for(SPEC, "include exactly: x")


def test_intake_has_form_fields_and_text():
    n = Narrative(justification="j", email_thread="e", attachment_text="")
    form = intake(SPEC, n)
    assert form["request_id"] == "EX-001" and form["amount_raw"] == "4.8L" and "family" not in form


def test_invented_answer_changing_facts_are_caught():
    from scripts.generate_cases import unsupported_facts

    spec = SPECS["specs"][1]  # routine E1 order: no line down, no urgency, no bank change
    bad = Narrative(justification="Need it asap, line 3 band hai.", email_thread="", attachment_text="")
    assert set(unsupported_facts(spec, bad)) == {"a stopped production line", "urgency"}
    ok = Narrative(
        justification="Routine order, ISO 9001 renewal awaited.", email_thread="", attachment_text=""
    )
    assert unsupported_facts(spec, ok) == []
    # the I3 example's story does mention the line and the bank change
    assert (
        unsupported_facts(
            SPEC,
            Narrative(justification="line 3 band hai, new bank account", email_thread="", attachment_text=""),
        )
        == []
    )


def test_deadline_does_not_count_as_a_stopped_line():
    from scripts.generate_cases import unsupported_facts

    spec = {"story": "Routine order; the customer deadline is Friday.", "must_mention": []}
    bad = Narrative(
        justification="Line 2 band hai, stopped since morning.", email_thread="", attachment_text=""
    )
    assert "a stopped production line" in unsupported_facts(spec, bad)
