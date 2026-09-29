"""precedence.py: conflict resolution (SPEC §6.2) and the risk floor F1-F5 (SPEC §6.3)."""

from datetime import date

from api.engine.precedence import FloorContext, Step, apply_floor, default_winner, resolve_conflicts

D = date(2026, 9, 24)


def ctx(**kw):
    base = dict(
        submitted_on=D,
        amount=1_50_000,
        bank_change=False,
        related_party=False,
        gst_cancelled=False,
        delegations=[("E-112", 2_00_000, date(2026, 4, 1), date(2027, 3, 31))],
    )
    return FloorContext(**(base | kw))


def steps(*codes, origin="memory"):
    return [Step(c, "r", ["PR-1"], origin) for c in codes]


def codes(ss):
    return [s.code for s in ss]


def test_default_priority_between_classes_and_within_class():
    assert default_winner("HOLD_PO", "EXPEDITE_PO") == "HOLD_PO"  # compliance beats convenience
    assert default_winner("HOLD_PO", "CONDITIONAL_PO_WITH_QC") == "HOLD_PO"  # same class: conservative
    assert default_winner("ROUTE_DELEGATE", "ROUTE_NEXT_LEVEL_APPROVER") == "ROUTE_NEXT_LEVEL_APPROVER"


def test_conflict_default_keeps_hold_po():
    out, rec = resolve_conflicts(steps("HOLD_PO", "EXPEDITE_PO", "VERIFY_BANK_CALLBACK"), [], ctx())
    assert codes(out) == ["HOLD_PO", "VERIFY_BANK_CALLBACK"]
    assert (rec[0].kept, rec[0].dropped, rec[0].reason) == ("HOLD_PO", "EXPEDITE_PO", "default priority")


def test_interaction_precedent_keeps_lower_priority_choice():
    i3 = ("PR-2026-0312", ["EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"])
    out, rec = resolve_conflicts(steps("HOLD_PO", "EXPEDITE_PO"), [i3], ctx(bank_change=True))
    assert codes(out) == ["EXPEDITE_PO"] and rec[0].reason == "precedent PR-2026-0312"


def test_precedent_cannot_beat_the_floor():
    # GST cancelled: F4 requires HOLD_PO, so a precedent choosing EXPEDITE_PO loses.
    prec = ("PR-X", ["EXPEDITE_PO"])
    out, rec = resolve_conflicts(steps("HOLD_PO", "EXPEDITE_PO"), [prec], ctx(gst_cancelled=True))
    assert codes(out) == ["HOLD_PO"] and rec[0].reason == "default priority"


def test_f1_bank_change_adds_callback_and_payment_hold():
    r = apply_floor(steps("EXPEDITE_PO"), ctx(bank_change=True))
    assert set(codes(r.steps)) == {"EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"}
    assert r.added == ["VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"]
    assert all(s.origin == "floor" for s in r.steps if s.code in r.added)


def test_f1_keeps_existing_memory_steps_as_memory():
    r = apply_floor(steps("VERIFY_BANK_CALLBACK", "HOLD_PAYMENT"), ctx(bank_change=True))
    assert r.added == [] and all(s.origin == "memory" for s in r.steps)


def test_f2_delegate_over_limit_becomes_next_level():
    r = apply_floor(steps("ROUTE_DELEGATE"), ctx(amount=2_50_000))
    assert codes(r.steps) == ["ROUTE_NEXT_LEVEL_APPROVER"] and r.replaced == [
        ("ROUTE_DELEGATE", "ROUTE_NEXT_LEVEL_APPROVER")
    ]


def test_f2_expired_delegation_becomes_next_level():
    r = apply_floor(
        steps("ROUTE_DELEGATE"), ctx(delegations=[("E-112", 2_00_000, date(2025, 4, 1), date(2026, 3, 31))])
    )
    assert codes(r.steps) == ["ROUTE_NEXT_LEVEL_APPROVER"]


def test_f2_valid_delegation_is_kept():
    assert codes(apply_floor(steps("ROUTE_DELEGATE"), ctx()).steps) == ["ROUTE_DELEGATE"]


def test_f3_related_party_declaration_and_never_one_click():
    r = apply_floor([], ctx(related_party=True))
    assert codes(r.steps) == ["DECLARE_CONFLICT_OF_INTEREST"] and "F3:no_one_click" in r.flags


def test_f4_gst_cancelled_requires_gst_check_and_hold_and_wins_conflicts():
    r = apply_floor(steps("EXPEDITE_PO"), ctx(gst_cancelled=True))
    assert set(codes(r.steps)) == {"VERIFY_GST_STATUS", "HOLD_PO"}
    assert r.conflicts[0].reason == "floor F4"


def test_f5_unknown_step_dropped_and_flagged():
    r = apply_floor(steps("RELEASE_PAYMENT", "HOLD_PO"), ctx())
    assert codes(r.steps) == ["HOLD_PO"] and "F5:dropped_unknown_step:RELEASE_PAYMENT" in r.flags
