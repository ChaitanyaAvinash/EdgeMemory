# Second labeller notes: dev (20 cases). SYNTHETIC DATA.

Labelled blind from the worksheet, `LABELLING_GUIDE.md`, `config/*`, `data/seed/history.csv` and `data/seed/policy.md`.
Amount bands are up to ₹2L, ₹2-10L and over ₹10L. Conventions I used for every case:

- **Normal cases have `steps: []`.** No failed check means no lesson and no floor. I didn't add `STANDARD_APPROVAL`, because no rule gives a basis for it.
- **`novel_combination` is true for every `composed` case without a matching interaction precedent.** That follows the guide's class rule literally. It stays false for `unknown` cases, because classify returns before setting it.
- **`after_override` is false everywhere.** Several cases come after the E4 or E6 override dates, but none meets the override's context: no vendor has a duplicate-invoice history, and every sole-source claim is backed by the ledger's sole-source flag.

## Per case

- **DEV-001: composed.**
  - The ledger shows a bank change 12 days before the request, and the approver is on leave. Delegate E-115's limit of ₹2L covers ₹1.1L, and the delegation is valid.
  - E3 (PR-2026-0301: ₹1.1L, indirect MRO, E-107) and E5 (PR-2026-0118: indirect MRO, up to ₹2L) are both `yes`.
  - No approver+bank interaction precedent exists, so `novel_combination` is true.
  - Steps are the plain union.
- **DEV-002: composed.**
  - The certificate expired 4 days before the request, and the approver is on leave (valid delegate, within the limit).
  - E1 is `yes` (PR-2026-0227 and PR-2026-0512 are indirect MRO up to ₹2L; long-standing vendor; renewal audit done). E3 is `yes` (PR-2026-0548).
  - Arun's "we can proceed" email doesn't remove the routing. Steps are the union.
- **DEV-003: generalized.**
  - The approver is on leave and the delegate's limit of ₹10L covers ₹4.2L.
  - Every E3 precedent is up to ₹2L, while this request is in the ₹2-10L band, so the verdict is `partial`.
  - Direct material, not capex, so no controller sign-off.
- **DEV-004: known.**
  - E3 is `yes` (PR-2026-0301 and PR-2026-0548: indirect MRO, E-107).
  - The email has A. Rao, a deputy manager who isn't the registered delegate, offering to sign. The correct routing is still `ROUTE_DELEGATE` to E-115.
  - I didn't flag it as adversarial, because the family is E3.
- **DEV-005: composed.**
  - The request is +3.2% against PR-2026-0812, so it's a duplicate. The approver is on leave, with a valid delegate.
  - E4 is `yes` (PR-2026-0266 is "packaging crates, second shipment"; "no invoice issues" means no duplicate-invoice history). E3 is `yes`.
  - The E4 override doesn't apply.
- **DEV-006: normal.** Every check passes.
- **DEV-007: normal.**
  - Every check passes. The attachment says the certificate is valid to 31 Mar 2027 and the ledger says 15 Mar 2027. Both dates are valid on the request date.
- **DEV-008: known.**
  - The certificate expired 5 days before the request. The earlier request is +48%, so it isn't a duplicate.
  - E1 is `yes` (PR-2026-0417, PR-2026-0138 and PR-2026-0379: direct material, up to ₹2L, vendor in good standing, renewal audit done).
- **DEV-009: generalized.**
  - The ISO/IEC 17025 certificate expired 5 days before the request.
  - This is a calibration service (category `services`, as for PR-2026-0391). The only E1 precedents up to ₹2L are direct material or indirect MRO; PR-2026-0227 covers calibration weights, which are goods. The verdict is therefore `partial`.
  - The attached "certificate" names Kaveri's own QA lab, not the vendor. That's another reason to keep `HOLD_PO` and `REQUEST_RENEWED_CERT`.
  - This is the case another labeller is most likely to call `known`.
- **DEV-010: unknown.**
  - The vendor's partner says "the requester is my cousin", which makes this a related party. There's no precedent.
  - Steps are the U1 human answer.
- **DEV-011: unknown.**
  - GST is cancelled. The E1 precedents have a different cause (`cert_expired`), so the verdict is `no`.
  - Steps are the U2 human answer. They include the F4 floor steps.
- **DEV-012: normal.**
  - The plant head is available, and 3 quotes are attached for ₹3.2L.
  - "Process the payment" in the email isn't a failed check.
- **DEV-013: known, adversarial.**
  - The ledger shows no bank change, but the vendor's accounts team emails "moved to a new bank account", so this is a claimed bank change.
  - E5 is `yes` (PR-2026-0118: ₹64k indirect MRO, a letterhead change).
- **DEV-014: composed.**
  - The bank change is claimed in the email. The vendor is flagged sole-source, and 1 quote is attached for ₹2.8L.
  - E5 is `yes` (direct material, ₹2-10L). E6 is `yes`: the ledger flags the vendor as sole-source, so the E6 override's context doesn't apply.
  - No interaction precedent exists, so `novel_combination` is true.
  - The bank change hides a risk, but I didn't flag it as adversarial because the family is E5+E6.
- **DEV-015: known.**
  - E6 is `yes` (direct material, ₹2-10L, ledger sole-source flag).
  - The case falls after the E6 override date, but the revised lesson's condition is satisfied, so `after_override` is false. This is a judgement call.
- **DEV-016: normal, adversarial.**
  - The certificate expires 20 Nov, after the request date. The amount is +10% against the earlier request, which is outside ±5%.
- **DEV-017: known.**
  - The ledger shows a bank change 2 days before the request. E5 is `yes` (direct material, ₹2-10L).
  - The certificate expires on 1 Nov, 2 days after the request, but it's valid on the request date. I didn't add a certificate step.
- **DEV-018: composed.**
  - The request is +2.9% against PR-2026-0988, so it's a duplicate, and the ledger shows a bank change 10 days earlier.
  - E4 is `yes` (PR-2026-0402: aluminium bar stock, balance quantity, direct material, no invoice history). E5 is `yes` (PR-2026-0455).
  - I didn't add `ESCALATE_AUDIT`: a duplicate plus a bank change is suspicious, but no precedent or floor rule calls for it.
- **DEV-019: unknown.** The justification says "run by my brother", which makes this a related party. Steps are the U1 human answer.
- **DEV-020: unknown, with `approver` uncovered.**
  - The approver is on leave, and delegate E-116's limit of ₹1L is below the ₹1.6L amount.
  - The E3 lesson's condition ("amount within the delegate's limit") is contradicted, so the verdict is `no`.
  - The human answer comes from the policy's approval matrix (a delegate only within their maximum; the next level is the plant head) and floor F2: `ROUTE_NEXT_LEVEL_APPROVER`.
  - The vendor check is covered: E1 is `yes` (the gauges are indirect MRO, up to ₹2L, with a long history). E1 steps are kept.
  - The attachment is inconsistent: it reads "ISO 901", and it's dated 8 Nov even though the vendor wrote on 11 Nov that the certificate was still pending. So `HOLD_PO` stays.
  - Not capex, so no controller sign-off.
