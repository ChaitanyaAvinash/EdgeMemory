"""Shared engine types: request facts, master-data snapshot, violations, coverage and classification.

Owns: plain data shapes passed between rules, detector and classify. Never does I/O or calls an API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

CHECKS = ("budget", "vendor", "approver", "duplicate", "bank", "quotes")
SIGNAL_VIOLATIONS = ("related_party",)  # signals that become violations (SPEC §4)
VERDICT_RANK = {"no": 0, "partial": 1, "yes": 2}


def amount_band(amount: int) -> str:
    """SPEC §5.1 bands: up to ₹2L, ₹2-10L, over ₹10L."""
    if amount <= 2_00_000:
        return "up to 2L"
    if amount <= 10_00_000:
        return "2-10L"
    return "over 10L"


def fiscal_year(d: date) -> str:
    """Indian FY, April-March: 2026-09-28 → '2026-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def tag_for(check: str) -> str:
    return f"signal:{check}" if check in SIGNAL_VIOLATIONS else f"step:{check}"


@dataclass(frozen=True)
class Signal:
    name: str  # bank_change_claimed | related_party
    source: str  # justification | email_thread | attachment_text
    span: str  # verbatim quote from that source


@dataclass
class RequestFacts:
    id: str
    submitted_on: date
    vendor_id: str | None
    vendor_name_raw: str
    amount: int | None
    cost_centre: str
    category: str
    urgency: str
    requester_id: str
    quotes_count: int
    signals: list[Signal] = field(default_factory=list)


@dataclass(frozen=True)
class VendorRec:
    id: str
    name: str
    gstin: str
    gst_status: str  # active | cancelled
    status: str  # active | blacklisted | inactive
    cert_name: str
    cert_expiry: date | None
    bank_changed_at: date | None
    sole_source: bool
    category: str


@dataclass(frozen=True)
class EmployeeRec:
    id: str
    name: str
    role: str
    cost_centre: str
    leave_from: date | None
    leave_to: date | None

    def on_leave(self, d: date) -> bool:
        return bool(self.leave_from and self.leave_to and self.leave_from <= d <= self.leave_to)


@dataclass(frozen=True)
class ApprovalLimitRec:
    cost_centre: str
    max_amount: int
    approver_id: str


@dataclass(frozen=True)
class DelegationRec:
    approver_id: str
    delegate_id: str
    max_amount: int
    valid_from: date
    valid_to: date


@dataclass(frozen=True)
class BudgetRec:
    cost_centre: str
    fiscal_year: str
    allocated: int
    spent: int


@dataclass(frozen=True)
class PriorRequestRec:
    id: str
    vendor_id: str
    amount: int
    submitted_on: date


@dataclass
class MasterData:
    vendors: dict[str, VendorRec]
    employees: dict[str, EmployeeRec]
    approval_limits: list[ApprovalLimitRec]
    delegations: list[DelegationRec]
    budgets: dict[tuple[str, str], BudgetRec]
    prior_requests: list[PriorRequestRec]


@dataclass
class Violation:
    check: str  # one of CHECKS, or a signal violation name
    cause: str
    detail: str
    source: str  # ledger | justification | email_thread | attachment_text
    source_span: str = ""

    @property
    def tag(self) -> str:
        return tag_for(self.check)


@dataclass
class Coverage:
    """One status per violation (SPEC §5.2)."""

    check: str
    status: str  # yes | partial | no
    case_ids: list[str] = field(default_factory=list)
    strength: int = 0  # distinct active supporting cases (SPEC §5.4)
    differences: list[str] = field(default_factory=list)
    reason: str = ""
    flags: list[str] = field(default_factory=list)  # e.g. predates_policy:POLICY-2026-07-01 (SPEC §8.8)


@dataclass
class InteractionCoverage:
    status: str  # yes | partial | no
    combo: str
    case_ids: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class Classification:
    cls: str  # normal | known | generalized | composed | unknown
    uncovered: list[Coverage] = field(default_factory=list)
    novel_combination: bool = False
