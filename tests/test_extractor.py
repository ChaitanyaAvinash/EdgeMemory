"""extractor.py code checks: spans must be verbatim in the named source; amounts and vendors come from code."""

from datetime import date, datetime

from api.engine.extractor import ExtractionOut, IntakeForm, SignalOut, build_facts, span_in_source
from api.engine.types import VendorRec

V = {
    "V-107": VendorRec(
        "V-107",
        "Nizam Pumps",
        "36AAACN1111A1Z1",
        "active",
        "active",
        "ISO 9001",
        date(2027, 1, 1),
        None,
        False,
        "direct_material",
    )
}


def form(**kw):
    base = dict(
        request_id="PR-1",
        submitted_at=datetime(2026, 9, 24, 10, 0),
        requester_id="E-401",
        cost_centre="CC-MACH",
        vendor_name="Nizam Pumps Pvt Ltd",
        amount_raw="1.9L",
        quotes_attached=1,
        justification="Line 3 band hai, urgent chahiye.",
        email_thread="From: accounts@nizampumps\nPlease note our NEW bank account from this month.",
    )
    return IntakeForm(**(base | kw))


def out(signals, amount=""):
    return ExtractionOut(
        category="direct_material", urgency="line_down", amount_mentioned=amount, signals=signals
    )


def test_span_check_is_whitespace_and_case_insensitive():
    assert span_in_source("please note our new   bank account", "x\nPlease note our NEW bank account from")
    assert not span_in_source("our new bank account details", "Please note our NEW bank account from")
    assert not span_in_source("   ", "anything")


def test_signal_kept_when_span_is_verbatim_in_named_source():
    facts, dropped = build_facts(
        form(),
        out([SignalOut(name="bank_change_claimed", source="email_thread", span="our NEW bank account")]),
        V,
    )
    assert [s.name for s in facts.signals] == ["bank_change_claimed"] and dropped == []


def test_signal_dropped_when_span_is_invented_or_in_wrong_source():
    sigs = [
        SignalOut(name="related_party", source="email_thread", span="owner is my brother-in-law"),  # invented
        SignalOut(
            name="bank_change_claimed", source="justification", span="our NEW bank account"
        ),  # wrong source
    ]
    facts, dropped = build_facts(form(), out(sigs), V)
    assert facts.signals == [] and [d["name"] for d in dropped] == ["related_party", "bank_change_claimed"]


def test_amount_and_vendor_come_from_code():
    facts, _ = build_facts(form(), out([]), V)
    assert (facts.amount, facts.vendor_id, facts.submitted_on) == (1_90_000, "V-107", date(2026, 9, 24))


def test_amount_falls_back_to_text_when_form_has_none():
    facts, _ = build_facts(form(amount_raw=""), out([], amount="Rs 1,20,000"), V)
    assert facts.amount == 1_20_000
