# Labelling guide (SYNTHETIC DATA)

The ground-truth labeller's rules. Part 1 is `config/verdict_guide.md` copied word for word; Part 2 gives the
family rules from SPEC §4, §5.3, §6.3, §7.2 and §13. The engine never reads this file (CLAUDE.md rule 10).
Frozen at Gate G2.

## Part 1: verdicts (copied from `config/verdict_guide.md`)

Verdicts for whether a past precedent applies to a new purchase-request exception (SPEC §5.1).
The same text is used by the verifier prompt and by data/ground_truth/LABELLING_GUIDE.md.

- yes: same failed check, same cause, the precedent's conditions hold (for example, "vendor otherwise in good standing"), and no relevant policy change since the precedent. A different vendor or amount is fine if it is within the same amount band (up to ₹2L, ₹2-10L, over ₹10L) and the same category.
- partial: same check and same cause, but a different amount band or category, or one of the precedent's conditions can't be confirmed from the request. The differences must be listed.
- no: a different cause (for example, GST cancelled versus certificate expired), a precedent condition that the request contradicts, a precedent overridden in this context, or a precedent superseded by a later policy change.

For an interaction precedent (several checks failed together), judge whether its combination of failed checks and its conditions match the new request in the same way.

## Part 2: family rules

### Which checks fail (SPEC §4)

- `budget`, `vendor`, `approver`, `duplicate`, `bank`, `quotes` are ledger checks; label what the ledger on the
  request date shows.
- A bank change **claimed only in the text** (email, justification) is a `bank` failure with cause
  `bank_details_changed`.
- A requester connected to the vendor is a `related_party` failure.
- **Adversarial rule:** don't label failures that aren't there. A certificate expiring next month is not
  expired; an amount 6% away from a recent one is not a duplicate.

### Class (SPEC §5.3)

- No failed checks → `normal`, with an empty step set (decided by the user, 2026-09-28).
- Any failed check whose best precedent verdict is `no` (or that has no precedent) → `unknown`; list it in
  `uncovered_checks`.
- Otherwise, more than one failed check → `composed` (`novel_combination` true unless a verified interaction
  precedent covers the combination).
- Otherwise one failed check: best verdict `yes` → `known`; `partial` → `generalized`.

### Steps (SPEC §7.1, §6.2, §6.3)

- Start from the union of each covered check's seeded lesson; apply any matching interaction precedent.
- Conflicts: the higher-priority class wins; within a class, the more conservative step
  (`config/conflicts.yaml`).
- The risk floor always applies:
  - F1 bank change (ledger or claimed) → `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`.
  - F2 `ROUTE_DELEGATE` when the delegate's limit is below the amount or the delegation isn't valid on the
    date → `ROUTE_NEXT_LEVEL_APPROVER`.
  - F3 related party → `DECLARE_CONFLICT_OF_INTEREST`.
  - F4 GST cancelled → `VERIFY_GST_STATUS`, `HOLD_PO`.
- For an uncovered check, the human answer comes from SPEC §13 (U1, U2, I2) or, for any other, from
  `data/seed/policy.md`.

### Families (SPEC §13, §7.2)

| Family | Check (cause) | Resolution steps |
|---|---|---|
| E1 Expired certificate | vendor (cert_expired) | `REQUEST_RENEWED_CERT`, `KEEP_VENDOR_ACTIVE`, `HOLD_PO` |
| E2 Emergency overrun (up to 10%, line down) | budget (overrun) | `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `ADD_CONTROLLER_SIGNOFF`, `EXPEDITE_PO` |
| E3 Approver away | approver (approver_on_leave) | `ROUTE_DELEGATE`; post-1-Jul-2026 capex also needs `ADD_CONTROLLER_SIGNOFF` |
| E4 Split shipment | duplicate (possible_duplicate) | `LINK_MASTER_PO`, `ALLOW_SPLIT_DELIVERY` |
| E5 Bank details changed | bank (bank_details_changed) | `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`, `HOLD_PO` |
| E6 Sole source | quotes (insufficient_quotes) | `SOLE_SOURCE_FORM`, `CATEGORY_HEAD_SIGNOFF` |
| I1 | approver + budget (overrun) | `ROUTE_NEXT_LEVEL_APPROVER`, `ADD_CONTROLLER_SIGNOFF`, `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `EXPEDITE_PO` |
| I2 (held out) | vendor (cert_expired) + quotes (sole source) | `CONDITIONAL_PO_WITH_QC`, `INCOMING_QC_INSPECTION`, `REQUEST_RENEWED_CERT`, `KEEP_VENDOR_ACTIVE`, `SOLE_SOURCE_FORM`, `CATEGORY_HEAD_SIGNOFF`; `novel_combination` true |
| I3 | bank + budget (emergency, line down) | `EXPEDITE_PO`, `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`, `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `ADD_CONTROLLER_SIGNOFF` |
| U1 Related party (held out) | related_party | `DECLARE_CONFLICT_OF_INTEREST`, `ESCALATE_AUDIT`, `COLLECT_QUOTES`, `HOLD_PO` |
| U2 GST cancelled (held out) | vendor (gst_cancelled) | `VERIFY_GST_STATUS`, `HOLD_PO`, `REQUEST_MORE_INFO` |

Overrides in the seed history (`kind = override`) revise a lesson in the stated context: E2 needs a maintenance
log confirming the line is down; E4 doesn't apply to a vendor with a prior duplicate-invoice incident; E6 needs
the approved-vendor list to show a single source.
