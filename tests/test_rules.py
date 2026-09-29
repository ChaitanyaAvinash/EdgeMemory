"""rules.py and normalise.py: the six checks, signal mapping, boundaries (SPEC §4) and amount parsing."""

from __future__ import annotations

from datetime import date

import pytest

from api.engine import rules
from api.engine.normalise import match_vendor, parse_amount
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
    amount_band,
    fiscal_year,
)

D = date(2026, 9, 24)


def vendor(id="V-001", **kw):
    base = dict(
        id=id,
        name="Deccan Bearings",
        gstin="36AAACD1234E1Z5",
        gst_status="active",
        status="active",
        cert_name="ISO 9001",
        cert_expiry=date(2027, 6, 30),
        bank_changed_at=None,
        sole_source=False,
        category="direct_material",
    )
    return VendorRec(**(base | kw))


def md(vendors=None, budget=(20_00_000, 10_00_000), leave=None, prior=None):
    head = EmployeeRec("E-1", "Head", "cc_head", "CC-A", *(leave or (None, None)))
    return MasterData(
        vendors={v.id: v for v in (vendors or [vendor()])},
        employees={"E-1": head, "E-9": EmployeeRec("E-9", "Plant head", "plant_head", "PLANT", None, None)},
        approval_limits=[
            ApprovalLimitRec("CC-A", 2_00_000, "E-1"),
            ApprovalLimitRec("CC-A", 10_00_000, "E-9"),
        ],
        delegations=[DelegationRec("E-1", "E-2", 2_00_000, date(2026, 4, 1), date(2027, 3, 31))],
        budgets={("CC-A", "2026-27"): BudgetRec("CC-A", "2026-27", *budget)},
        prior_requests=prior or [],
    )


def req(**kw):
    base = dict(
        id="PR-X",
        submitted_on=D,
        vendor_id="V-001",
        vendor_name_raw="Deccan Bearings",
        amount=1_00_000,
        cost_centre="CC-A",
        category="direct_material",
        urgency="normal",
        requester_id="E-5",
        quotes_count=1,
    )
    return RequestFacts(**(base | kw))


def checks(violations):
    return [(v.check, v.cause) for v in violations]


def test_clean_request_has_no_violations():
    assert rules.run_checks(req(), md()) == []


def test_budget_overrun_reports_percent_over_allocation():
    v = rules.check_budget(req(amount=1_50_000), md(budget=(20_00_000, 19_50_000)))
    assert (v.check, v.cause) == ("budget", "overrun") and "5.0% over budget" in v.detail


def test_budget_exactly_remaining_passes():
    assert rules.check_budget(req(amount=50_000), md(budget=(20_00_000, 19_50_000))) is None


@pytest.mark.parametrize(
    "kw,cause",
    [
        ({"cert_expiry": date(2026, 9, 18)}, "cert_expired"),
        ({"gst_status": "cancelled"}, "gst_cancelled"),
        ({"status": "blacklisted", "cert_expiry": date(2026, 1, 1)}, "blacklisted"),  # most severe first
    ],
)
def test_vendor_causes(kw, cause):
    v = rules.check_vendor(req(), md(vendors=[vendor(**kw)]))
    assert v.cause == cause


def test_certificate_expiring_next_month_is_not_expired():
    assert rules.check_vendor(req(), md(vendors=[vendor(cert_expiry=date(2026, 10, 20))])) is None


def test_unknown_vendor():
    assert (
        rules.check_vendor(req(vendor_id=None, vendor_name_raw="Nobody Ltd"), md()).cause == "unknown_vendor"
    )


def test_approver_on_leave_lists_delegation():
    v = rules.check_approver(req(), md(leave=(date(2026, 9, 20), date(2026, 10, 2))))
    assert v.cause == "approver_on_leave" and "delegate E-2 up to ₹2,00,000" in v.detail


def test_approver_back_from_leave_passes():
    assert rules.check_approver(req(), md(leave=(date(2026, 9, 1), date(2026, 9, 10)))) is None


def test_higher_amount_routes_to_next_approver():
    # ₹5L goes to E-9, who is present, even though the cost-centre head is on leave
    assert (
        rules.check_approver(req(amount=5_00_000), md(leave=(date(2026, 9, 20), date(2026, 10, 2)))) is None
    )


@pytest.mark.parametrize("amount,dup", [(1_05_000, True), (95_000, True), (1_06_000, False), (93_000, False)])
def test_duplicate_within_five_percent_inclusive(amount, dup):
    prior = [PriorRequestRec("PR-P", "V-001", 1_00_000, date(2026, 9, 10))]
    assert (rules.check_duplicate(req(amount=amount), md(prior=prior)) is not None) == dup


def test_duplicate_outside_30_days_passes():
    prior = [PriorRequestRec("PR-P", "V-001", 1_00_000, date(2026, 8, 20))]
    assert rules.check_duplicate(req(), md(prior=prior)) is None


def test_bank_change_in_ledger_within_30_days():
    v = rules.check_bank(req(), md(vendors=[vendor(bank_changed_at=date(2026, 9, 12))]))
    assert (v.cause, v.source) == ("bank_details_changed", "ledger")


def test_bank_change_older_than_30_days_passes():
    assert rules.check_bank(req(), md(vendors=[vendor(bank_changed_at=date(2026, 8, 1))])) is None


def test_bank_change_claimed_only_in_email():
    s = Signal("bank_change_claimed", "email_thread", "please use our new account")
    v = rules.check_bank(req(signals=[s]), md())
    assert (v.cause, v.source, v.source_span) == (
        "bank_details_changed",
        "email_thread",
        "please use our new account",
    )


@pytest.mark.parametrize(
    "amount,quotes,fails", [(2_00_000, 1, False), (2_00_001, 1, True), (5_00_000, 3, False)]
)
def test_quotes_threshold(amount, quotes, fails):
    assert (rules.check_quotes(req(amount=amount, quotes_count=quotes), md()) is not None) == fails


def test_related_party_signal_becomes_one_violation():
    s = [
        Signal("related_party", "email_thread", "my brother-in-law"),
        Signal("related_party", "justification", "family"),
    ]
    v = rules.run_checks(req(signals=s), md())
    assert checks(v) == [("related_party", "related_party")] and v[0].tag == "signal:related_party"


def test_several_failures_in_check_order():
    m = md(
        vendors=[vendor(bank_changed_at=date(2026, 9, 12))],
        budget=(20_00_000, 19_50_000),
        leave=(date(2026, 9, 20), date(2026, 10, 2)),
    )
    assert [c for c, _ in checks(rules.run_checks(req(amount=1_80_000), m))] == ["budget", "approver", "bank"]


@pytest.mark.parametrize(
    "raw,value",
    [
        ("4.8L", 4_80_000),
        ("₹4,80,000", 4_80_000),
        ("480000", 4_80_000),
        ("Rs. 4,80,000/-", 4_80_000),
        ("4.8 lakh", 4_80_000),
        ("1.2 cr", 1_20_00_000),
        ("60k", 60_000),
        ("INR 85,000", 85_000),
        ("approx 1.5 lakhs only", 1_50_000),
        ("", None),
        ("no amount", None),
    ],
)
def test_parse_amount(raw, value):
    assert parse_amount(raw) == value


def test_match_vendor():
    vs = {"V-001": vendor(), "V-002": vendor("V-002", name="Nizam Pumps")}
    assert match_vendor("deccan bearings", vs) == "V-001"
    assert match_vendor("Nizam Pumps Pvt Ltd", vs) == "V-002"
    assert match_vendor("vendor v-002", vs) == "V-002"
    assert match_vendor("Unknown Traders", vs) is None


def test_bands_and_fiscal_year():
    assert [amount_band(a) for a in (2_00_000, 2_00_001, 10_00_001)] == ["up to 2L", "2-10L", "over 10L"]
    assert fiscal_year(date(2026, 3, 31)) == "2025-26" and fiscal_year(date(2026, 4, 1)) == "2026-27"
    assert rules.inr(480000) == "₹4,80,000" and rules.inr(1_20_00_000) == "₹1,20,00,000"


def test_approver_on_leave_without_a_covering_delegation_has_its_own_cause():
    m = md(leave=(date(2026, 9, 20), date(2026, 10, 2)))
    assert rules.check_approver(req(amount=1_50_000), m).cause == "approver_on_leave"  # delegate up to 2L
    m.delegations[0] = m.delegations[0].__class__("E-1", "E-2", 1_00_000, date(2026, 4, 1), date(2027, 3, 31))
    assert rules.check_approver(req(amount=1_50_000), m).cause == "approver_on_leave_no_valid_delegate"
