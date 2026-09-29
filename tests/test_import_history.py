"""import_history.py: the seed CSV (SPEC §13 counts), tags (§8.3), the content template and overrides."""

from collections import Counter
from pathlib import Path

from scripts.import_history import document_id, ledger_rows, memory_item, read_csv, render_content, tags_for

SEED = Path(__file__).parents[1] / "data" / "seed" / "history.csv"


def records():
    return read_csv(SEED)


def test_seed_counts_match_spec_13():
    recs = records()
    assert len(recs) == 45 and len({r["case_id"] for r in recs}) == 45
    kinds = Counter(r["kind"] for r in recs)
    assert kinds == {"experience": 35, "interaction": 6, "override": 3, "policy_change": 1}
    fam = Counter(r["family"] for r in recs if r["kind"] == "experience")
    assert fam == {"E1": 7, "E2": 6, "E3": 6, "E4": 5, "E5": 6, "E6": 5}
    assert Counter(r["family"] for r in recs if r["kind"] == "interaction") == {"I1": 3, "I3": 3}


def test_demo_bank_excludes_e1_and_the_e4_override():
    excluded = {r["case_id"] for r in records() if not r["demo_bank"]}
    e1 = {r["case_id"] for r in records() if r["family"] == "E1"}
    assert excluded == e1 | {"PR-2026-0735"} and len(excluded) == 8


def test_post_july_capex_approver_seeds_carry_controller_signoff():
    capex = [r for r in records() if r["family"] == "E3" and r["category"] == "capex"]
    assert len(capex) == 2 and all("ADD_CONTROLLER_SIGNOFF" in r["steps"] for r in capex)
    assert all(r["resolved_at"] >= "2026-07-01" for r in capex)


def test_tags_follow_spec_8_3():
    by_id = {r["case_id"]: r for r in records()}
    assert tags_for(by_id["PR-2026-0312"]) == ["interaction", "combo:bank+budget"]
    assert tags_for(by_id["PR-2026-0360"]) == ["interaction", "combo:approver+budget"]
    assert tags_for(by_id["PR-2026-0417"]) == ["step:vendor"]
    assert tags_for(by_id["POLICY-2026-07-01"]) == ["step:approver", "policy"]
    assert tags_for(by_id["PR-2026-0735"]) == ["step:duplicate"]  # override keeps the lesson's tags


def test_content_keeps_step_codes_literally():
    rec = {r["case_id"]: r for r in records()}["PR-2026-0312"]
    text = render_content(rec)
    assert "Steps approved (codes): EXPEDITE_PO, VERIFY_BANK_CALLBACK" in text
    assert "Removed from the plain combination: HOLD_PO" in text and text.startswith("SYNTHETIC DATA.")


def test_override_document_id_and_ledger_row():
    rec = {r["case_id"]: r for r in records()}["PR-2026-0735"]
    assert document_id(rec) == "PR-2026-0735-override-1"
    item = memory_item(rec)
    assert item.document_id == "PR-2026-0735-override-1" and "Why the reviewer overrode it" in item.content
    lesson = ledger_rows(rec)[0]
    assert (lesson.kind, lesson.steps) == ("override", ["REJECT_REQUEST", "ESCALATE_AUDIT"])


def test_seeded_override_marks_the_overridden_lessons_with_context():
    from sqlmodel import Session

    from api import ledger
    from scripts.import_history import import_to_ledger

    with Session(ledger.engine("sqlite://")) as s:
        import_to_ledger(records(), s)
        e4 = s.get(ledger.Lesson, "PR-2026-0266")
        assert "PR-2026-0735 on 2026-08-12" in e4.overridden_by and "REJECT_REQUEST" in e4.overridden_by
        assert e4.status == "active"  # context-specific: the lesson still holds elsewhere
        assert s.get(ledger.Lesson, "PR-2026-0477").overridden_by == ""  # not named by the override
