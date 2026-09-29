"""Rule engine (SPEC §4): the six ledger checks plus mapped signals → violations.

Owns: deciding which checks fail, from a master-data snapshot and the request's facts. Pure and
deterministic. Never calls an LLM or memory, and never reads ground truth.
"""

from __future__ import annotations

from datetime import timedelta

from api.engine.types import ApprovalLimitRec, MasterData, RequestFacts, Violation, fiscal_year

QUOTES_THRESHOLD = 2_00_000  # at least three quotes above ₹2,00,000
QUOTES_REQUIRED = 3
DUPLICATE_WINDOW_DAYS = 30
DUPLICATE_TOLERANCE = 0.05  # ±5%, inclusive
BANK_WINDOW_DAYS = 30


def inr(n: int) -> str:
    """Indian digit grouping: 480000 → '₹4,80,000'."""
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-₹" if n < 0 else "₹") + s


def check_budget(req: RequestFacts, md: MasterData) -> Violation | None:
    fy = fiscal_year(req.submitted_on)
    b = md.budgets.get((req.cost_centre, fy))
    if b is None:
        return Violation(
            "budget", "no_budget", f"No FY {fy} budget for cost centre {req.cost_centre}", "ledger"
        )
    remaining = b.allocated - b.spent
    if req.amount is None or req.amount <= remaining:
        return None
    over_pct = (b.spent + req.amount - b.allocated) / b.allocated * 100 if b.allocated else 100.0
    return Violation(
        "budget",
        "overrun",
        f"{inr(req.amount)} exceeds the {inr(max(remaining, 0))} left in cost centre {req.cost_centre} "
        f"(FY {fy}, allocated {inr(b.allocated)}); {over_pct:.1f}% over budget",
        "ledger",
    )


def check_vendor(req: RequestFacts, md: MasterData) -> Violation | None:
    v = md.vendors.get(req.vendor_id or "")
    if v is None:
        return Violation(
            "vendor",
            "unknown_vendor",
            f"Vendor '{req.vendor_name_raw}' is not in the vendor master",
            "ledger",
        )
    d = req.submitted_on
    problems = []
    if v.status == "blacklisted":
        problems.append(("blacklisted", f"vendor {v.id} is blacklisted"))
    if v.gst_status != "active":
        problems.append(("gst_cancelled", f"GST registration {v.gstin} is {v.gst_status}"))
    if v.cert_expiry is not None and v.cert_expiry < d:
        days = (d - v.cert_expiry).days
        problems.append(
            (
                "cert_expired",
                f"{v.cert_name} certificate expired {v.cert_expiry.isoformat()} ({days} days before the request)",
            )
        )
    if v.status == "inactive":
        problems.append(("inactive", f"vendor {v.id} is inactive"))
    if not problems:
        return None
    # The cause is the most severe problem; the detail lists all of them.
    return Violation(
        "vendor", problems[0][0], f"{v.name} ({v.id}): " + "; ".join(p[1] for p in problems), "ledger"
    )


def approver_for(req: RequestFacts, md: MasterData) -> ApprovalLimitRec | None:
    """The approval-matrix row for this cost centre and amount: the lowest limit at or above the amount."""
    limits = sorted(
        (a for a in md.approval_limits if a.cost_centre == req.cost_centre), key=lambda a: a.max_amount
    )
    amount = req.amount or 0
    return next((a for a in limits if amount <= a.max_amount), None)


def check_approver(req: RequestFacts, md: MasterData) -> Violation | None:
    amount = req.amount or 0
    rule = approver_for(req, md)
    if rule is None:
        return Violation(
            "approver",
            "no_approver",
            f"No approver configured for {req.cost_centre} at {inr(amount)}",
            "ledger",
        )
    approver = md.employees.get(rule.approver_id)
    if approver is None or not approver.on_leave(req.submitted_on):
        return None
    d = req.submitted_on
    dels = [x for x in md.delegations if x.approver_id == approver.id]
    if dels:
        notes = "; ".join(
            f"delegate {x.delegate_id} up to {inr(x.max_amount)}, valid {x.valid_from.isoformat()} to {x.valid_to.isoformat()}"
            + ("" if x.valid_from <= d <= x.valid_to else " (not valid on the request date)")
            for x in dels
        )
    else:
        notes = "no delegation on file"
    covered = any(x.valid_from <= d <= x.valid_to and x.max_amount >= amount for x in dels)
    return Violation(
        "approver",
        # E3 precedents route to a delegate "when the amount is within the delegate's limit"; when no valid
        # delegation covers this amount on this date that condition fails, so the cause says so in code.
        "approver_on_leave" if covered else "approver_on_leave_no_valid_delegate",
        f"Approver {approver.id} ({approver.role}, {req.cost_centre}) is on leave "
        f"{approver.leave_from.isoformat()} to {approver.leave_to.isoformat()}; {notes}",
        "ledger",
    )


def check_duplicate(req: RequestFacts, md: MasterData) -> Violation | None:
    if req.amount is None or not req.vendor_id:
        return None
    lo = req.submitted_on - timedelta(days=DUPLICATE_WINDOW_DAYS)
    for p in md.prior_requests:
        if p.id == req.id or p.vendor_id != req.vendor_id or not (lo <= p.submitted_on <= req.submitted_on):
            continue
        if abs(req.amount - p.amount) <= DUPLICATE_TOLERANCE * p.amount:
            diff = (req.amount - p.amount) / p.amount * 100
            return Violation(
                "duplicate",
                "possible_duplicate",
                f"Request {p.id} to {req.vendor_id} on {p.submitted_on.isoformat()} for {inr(p.amount)} "
                f"is within 5% ({diff:+.1f}%) in the last {DUPLICATE_WINDOW_DAYS} days",
                "ledger",
            )
    return None


def check_bank(req: RequestFacts, md: MasterData) -> Violation | None:
    v = md.vendors.get(req.vendor_id or "")
    ledger_change = None
    if v and v.bank_changed_at is not None:
        age = (req.submitted_on - v.bank_changed_at).days
        if 0 <= age <= BANK_WINDOW_DAYS:
            ledger_change = (
                f"bank details changed on {v.bank_changed_at.isoformat()} ({age} days before the request)"
            )
    claim = next((s for s in req.signals if s.name == "bank_change_claimed"), None)
    if ledger_change is None and claim is None:
        return None
    if ledger_change and claim:
        return Violation(
            "bank",
            "bank_details_changed",
            f"{ledger_change}; also claimed in the {claim.source}",
            "ledger",
            claim.span,
        )
    if ledger_change:
        return Violation("bank", "bank_details_changed", ledger_change, "ledger")
    return Violation(
        "bank",
        "bank_details_changed",
        f"new bank details claimed in the {claim.source}; the ledger shows no change yet",
        claim.source,
        claim.span,
    )


def check_quotes(req: RequestFacts, md: MasterData) -> Violation | None:
    if req.amount is None or req.amount <= QUOTES_THRESHOLD or req.quotes_count >= QUOTES_REQUIRED:
        return None
    v = md.vendors.get(req.vendor_id or "")
    sole = " (vendor is flagged sole-source)" if v and v.sole_source else ""
    return Violation(
        "quotes",
        "insufficient_quotes",
        f"{req.quotes_count} quote(s) attached for {inr(req.amount)}; {QUOTES_REQUIRED} required above "
        f"{inr(QUOTES_THRESHOLD)}{sole}",
        "ledger",
    )


def signal_violations(req: RequestFacts) -> list[Violation]:
    """One violation per signal type, from its first occurrence."""
    out = []
    seen: set[str] = set()
    for s in req.signals:
        if s.name == "related_party" and s.name not in seen:
            seen.add(s.name)
            out.append(
                Violation(
                    "related_party",
                    "related_party",
                    f"requester connected to the vendor ({s.source})",
                    s.source,
                    s.span,
                )
            )
    return out


def run_checks(req: RequestFacts, md: MasterData) -> list[Violation]:
    """All violations for a request, in check order, then signal violations."""
    found = [
        check_budget(req, md),
        check_vendor(req, md),
        check_approver(req, md),
        check_duplicate(req, md),
        check_bank(req, md),
        check_quotes(req, md),
    ]
    return [v for v in found if v is not None] + signal_violations(req)
