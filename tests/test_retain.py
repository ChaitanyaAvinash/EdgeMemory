"""retain.py: which memory kinds a human decision becomes (SPEC §8.3, §8.7 steps 1-2)."""

from datetime import date, datetime

import pytest

from api import ledger
from api.engine.retain import plan_retain
from api.memory.records import memory_item

D = date(2026, 9, 30)


def req():
    return ledger.Request(
        id="PR-N",
        submitted_at=datetime(2026, 9, 29),
        vendor_id="V-1",
        amount=1_90_000,
        category="direct_material",
        urgency="line_down",
        justification="pumps",
    )


def viol(*checks):
    return [
        ledger.ViolationRow(
            request_id="PR-N", check=c, cause=f"{c}-cause", detail=f"{c} failed", source="ledger"
        )
        for c in checks
    ]


def proc(steps, union):
    return ledger.Procedure(
        request_id="PR-N",
        arm="C",
        steps=[{"code": c} for c in steps],
        union_steps=[{"code": c} for c in union],
    )


def kinds(plan):
    return [r["kind"] for r in plan.records]


def test_resolving_an_unknown_is_an_experience():
    p = plan_retain(
        req(), viol("vendor"), None, [], "resolve", ["VERIFY_GST_STATUS", "HOLD_PO"], "gst", "A", "", D
    )
    assert kinds(p) == ["experience"] and memory_item(p.records[0]).tags == ["step:vendor"]


def test_approving_a_known_lesson_unchanged_is_a_confirmation():
    pr = proc(["HOLD_PO", "KEEP_VENDOR_ACTIVE"], ["HOLD_PO", "KEEP_VENDOR_ACTIVE"])
    p = plan_retain(
        req(), viol("vendor"), pr, ["PR-1"], "approve", ["HOLD_PO", "KEEP_VENDOR_ACTIVE"], "", "A", "", D
    )
    assert kinds(p) == ["confirmation"]


def test_multi_check_differing_from_union_is_an_interaction_with_combo_tags():
    pr = proc(["EXPEDITE_PO", "HOLD_PAYMENT"], ["HOLD_PO", "EXPEDITE_PO", "HOLD_PAYMENT"])
    p = plan_retain(
        req(),
        viol("bank", "budget"),
        pr,
        ["PR-1"],
        "confirm",
        ["EXPEDITE_PO", "HOLD_PAYMENT"],
        "po is not payment",
        "A",
        "",
        D,
    )
    assert kinds(p) == ["interaction"]
    item = memory_item(p.records[0])
    assert (
        item.tags == ["interaction", "combo:bank+budget"]
        and "Removed from the plain combination: HOLD_PO" in item.content
    )


def test_reject_is_an_override_plus_the_reviewers_own_decision():
    pr = proc(["LINK_MASTER_PO", "ALLOW_SPLIT_DELIVERY"], ["LINK_MASTER_PO", "ALLOW_SPLIT_DELIVERY"])
    p = plan_retain(
        req(),
        viol("duplicate"),
        pr,
        ["PR-2026-0266"],
        "reject",
        ["REJECT_REQUEST", "ESCALATE_AUDIT"],
        "vendor had a duplicate-invoice incident",
        "A",
        "",
        D,
    )
    assert kinds(p) == ["experience", "override"]
    ov = memory_item(p.records[1])
    assert ov.document_id == "PR-N-override-1" and ov.tags == ["step:duplicate"]
    assert "the lesson recommended LINK_MASTER_PO" in ov.content and "PR-2026-0266" in ov.content


def test_normal_cases_retain_nothing_and_bad_action_rejected():
    assert plan_retain(req(), [], None, [], "approve", ["STANDARD_APPROVAL"], "", "A", "", D).records == []
    with pytest.raises(ValueError):
        plan_retain(req(), viol("vendor"), None, [], "release_payment", [], "", "A", "", D)


class FakeObsBackend:
    consolidates = True
    bank_id = "kaveri-test"

    def __init__(self, ready_after: int):
        self.calls = 0
        self.ready_after = ready_after

    async def observations(self, tag):
        self.calls += 1
        cases = ["PR-1", "PR-N"] if self.calls > self.ready_after else ["PR-1"]
        return [{"id": "o1", "text": f"lesson from {len(cases)} cases", "case_ids": cases}]


def _fast_config(monkeypatch):
    import api.engine.retain as r

    monkeypatch.setattr(
        r, "config", lambda name: {"consolidation": {"poll_s": 0.0, "max_poll_s": 0.0, "timeout_s": 1}}
    )


def test_snapshots_wait_until_the_observation_cites_the_new_case(monkeypatch):
    import asyncio

    from sqlmodel import Session, select

    from api.engine.retain import take_snapshots

    _fast_config(monkeypatch)
    b = FakeObsBackend(ready_after=2)
    with Session(ledger.engine("sqlite://")) as s:
        out = asyncio.run(take_snapshots(s, b, ["step:vendor"], "PR-N"))
        rows = s.exec(select(ledger.ObservationSnapshot)).all()
    assert out["consolidated"] is True and b.calls == 3
    assert rows[0].source_case_ids == ["PR-1", "PR-N"] and rows[0].text == "lesson from 2 cases"


def test_snapshots_report_a_timeout_honestly(monkeypatch):
    import asyncio

    from sqlmodel import Session

    from api.engine.retain import take_snapshots

    monkeypatch.setattr(
        "api.engine.retain.config",
        lambda name: {"consolidation": {"poll_s": 0.0, "max_poll_s": 0.0, "timeout_s": 0}},
    )
    with Session(ledger.engine("sqlite://")) as s:
        out = asyncio.run(take_snapshots(s, FakeObsBackend(ready_after=99), ["step:vendor"], "PR-N"))
    assert out["consolidated"] is False and out["pending_tags"] == ["step:vendor"]


def test_vector_memory_has_nothing_to_snapshot():
    import asyncio

    from sqlmodel import Session

    from api.engine.retain import take_snapshots

    class NoConsolidation:
        consolidates = False

    with Session(ledger.engine("sqlite://")) as s:
        assert (
            asyncio.run(take_snapshots(s, NoConsolidation(), ["step:vendor"], "PR-N"))["consolidated"] is None
        )
