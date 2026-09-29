# Dev labelling notes: first labeller (SYNTHETIC DATA)

Labeller: Claude Code, the engine-building session, at the user's request. Labelled blind from
`data/labelling/dev_worksheet.md`, `data/ground_truth/LABELLING_GUIDE.md`, `data/seed/history.csv` and
`data/seed/policy.md`; no EdgeMemory output for these cases was opened. Answers: `data/ground_truth/dev.json`.

## Agreement with the second labeller

Before adjudication the two labellings agreed on every field in **11 of 20** cases. On `class`,
`failed_checks`, `causes` and `uncovered_checks` they agreed in 20 of 20. They differed only on two conventions:

- **Normal-case steps: 16 of 20.** I gave the four normal cases `STANDARD_APPROVAL`; the second labeller gave
  them `[]`.
- **`novel_combination`: 15 of 20.** I set it false on the five composed cases with no interaction precedent;
  the second labeller set it true.

**Adjudicated by the user on 2026-09-28:** normal cases get `[]`, and `novel_combination` is true on any
composed case that no verified interaction precedent covers (SPEC §5.3). After adjudication `dev.json` matches
the second labelling on every field in 20 of 20 cases.

## Conventions (after adjudication)

- **Normal cases** have an empty step set.
- **`novel_combination`** is true on every composed case that no verified interaction precedent covers,
  matching SPEC §5.3. M5 scores the flag on the I2 cases only.
- **`adversarial`** follows the family: true only for the two `adversarial`-family cases.
- **Categories and bands** decide yes versus partial (verdict guide): up to ₹2L, ₹2–10L, over ₹10L;
  `direct_material`, `indirect_mro`, `capex`, `services`.

## Per case

| Case | Class | Judgement |
|---|---|---|
| DEV-001 | composed | E3 yes (PR-2026-0301: E-107, ₹1.1L, MRO, delegate ₹2L valid). E5 yes (PR-2026-0118, MRO ≤₹2L). Plain union. |
| DEV-002 | composed | E1 yes (PR-2026-0227 / 0512, MRO ≤₹2L; long-standing vendor). The attached renewal is valid only from 28 Sep, after the request. E3 yes. Plain union. |
| DEV-003 | generalized | Direct material, ₹4.2L. Every E3 precedent is ≤₹2L (and the two post-July ones are capex), so the best is partial (band). Delegate's ₹10L limit covers it. |
| DEV-004 | known | E3 yes. The deputy manager's offer to sign is not the registered delegate; route to E-115. |
| DEV-005 | composed | +3.2% against PR-2026-0812: duplicate. E4 yes (PR-2026-0266, crates, MRO); "no invoice issues", so the E4 override doesn't apply. E3 yes. |
| DEV-006 | normal | All checks pass. |
| DEV-007 | normal | All checks pass (17025 valid to 2027-03-15). |
| DEV-008 | known | E1 yes (PR-2026-0417: ISO 9001, direct material, ₹1.4L). +48% against PR-2026-0846 is not a duplicate. |
| DEV-009 | generalized | A calibration *service* (`services`); every E1 precedent is direct material or MRO, so partial (category). The attached certificate names Kaveri's own QA lab, so it proves nothing about the vendor's renewal. |
| DEV-010 | unknown | U1: the vendor's partner says the requester is her cousin. SPEC §13 human answer. |
| DEV-011 | unknown | U2: GST cancelled; E1 precedents are a different cause (no). SPEC §13 human answer. |
| DEV-012 | normal | All checks pass. "Process the payment" is not procurement's to do, but no check fails. |
| DEV-013 | known | Bank change only in the vendor accounts email: a claimed change, so `bank` fails. E5 yes (PR-2026-0118, MRO ≤₹2L). Adversarial (hides a risk). |
| DEV-014 | composed | Bank change claimed in email; sole-source flagged with 1 quote. E5 yes (PR-2026-0233 / 0309, direct material ₹2–10L). E6 yes; the ledger's sole-source flag satisfies the E6 override's condition. Plain union. |
| DEV-015 | known | E6 yes (direct material ₹2–10L), sole-source flagged. Not an after-override case: the override's context (a second approved vendor) doesn't hold. |
| DEV-016 | normal | Certificate valid to 20 Nov; +10% against PR-2026-0934 is not a duplicate. Adversarial (looks like an edge case). |
| DEV-017 | known | Bank changed 2 days before. E5 yes (direct material ₹2–10L). Certificate valid on the date. |
| DEV-018 | composed | +2.9% against PR-2026-0988: duplicate; E4 yes (PR-2026-0402, aluminium, direct material). Bank changed 10 days before; E5 yes (PR-2026-0455). Plain union. |
| DEV-019 | unknown | U1: the requester's brother runs the vendor. |
| DEV-020 | unknown | E1 yes (MRO gauges ≤₹2L, renewal audit done). Approver uncovered: the delegate's ₹1L limit is below ₹1.6L, which contradicts every E3 precedent's condition (no). Policy §3 and floor F2: route to the next-level approver. |
