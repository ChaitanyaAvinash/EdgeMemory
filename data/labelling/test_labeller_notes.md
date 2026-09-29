# Test labeller notes (SYNTHETIC DATA)

Labeller: Claude (Opus 5.5, `claude-opus-5-5`), acting as blind labeller. Labelled 2026-09-29.

**Sources used:** `data/ground_truth/LABELLING_GUIDE.md`, `docs/ground_truth_format.md`, `config/verdict_guide.md`,
`config/step_library.yaml`, `config/conflicts.yaml` (the guide cites it for conflicts), `data/seed/history.csv`,
`data/seed/policy.md`, `data/cases/test_reduced.json` and `data/labelling/test_worksheet.md`.

**Not opened:** `eval/results/`, `data/runs/`, any `.db` file, `api/`, any system output, `data/ground_truth/dev.json`
and the dev labeller notes.

**Scope:** the 24 cases in `test_reduced.json`. The other 16 cases in `data/ground_truth/test.json` are left as they
are in the skeleton. `frozen_at` is empty because freezing is the data owner's step (Gate G2 records the hash in
`FROZEN.json`). The skeleton's `family` values were kept as they were.

## Conventions I applied

- **Category** isn't a worksheet field, so I inferred it from the item and the "capitalised" wording:
  - `capex`: anything to be capitalised.
  - `indirect_mro`: maintenance spares and tooling.
  - `direct_material`: parts for customer orders.
- **Amount bands** follow the verdict guide: up to ₹2L, ₹2–10L, over ₹10L.
- **`after_override`** is true only when the override's context holds, so that the revised lesson changes the
  answer (TEST-013, 020, 027). Later cases that meet the revised condition (for example TEST-001, where the
  maintenance log confirms the line is down) are false, because for them the revised lesson gives the same answer
  as the original.
- **`adversarial`** is true when either:
  - the text raises something that isn't a failure (TEST-028), or
  - a real failure appears only in the text while the ledger is clean (text-only bank claims: TEST-019, 024, 025).

  I took this reading from the skeleton, whose designer gave the text-only bank case TEST-040 the family
  `adversarial`. A failure the ledger shows plainly (the GST cases) isn't counted as adversarial.
- **`novel_combination`** is true for any case with several failed checks whose combination has no precedent in
  the seed history. That's the I2 cases, TEST-012 and TEST-024.
- **`interaction`** is true only for the I1, I2 and I3 families.
- **I2 precedents.** Every I2 case is labelled against the **seed history only**. If the eval replays human
  decisions in order, TEST-011's resolution could become a precedent for TEST-015, 030 and 032. The guide says I2 →
  `novel_combination` true, and I followed it.

## Per-case reasoning

### Interaction (I1, I2, I3)

**TEST-001 · composed · I1.**
- Budget fails: CC-MACH has ₹0 left and this would put it 1.9% over. Line 1 is down and the maintenance log
  confirms it.
- Approver fails: E-104 is on leave; delegate E-112 is valid up to ₹2L.
- I1 precedent PR-2026-0360 is a **yes**: same approver and delegate, indirect MRO, ₹1.70L (same band), 6% over,
  line down. PR-2026-0515 matches too.
- Steps are the I1 set: the next-level approver, not the delegate, because delegates don't approve overruns.
- Not capex (a hydraulic pump spare), so `post_july_capex_approver` is false.
- The E2 override condition (a maintenance log confirming the line is down) is met, so `after_override` is false.

**TEST-003 · composed · I1.**
- Budget is 7.8% over, which is within 10%; the maintenance log confirms line 2 is down.
- Plant head E-201 is on leave; delegate E-205 is valid up to ₹10L.
- I1 precedent PR-2026-0620 is a **yes**: same approver and delegate, ₹4.60L indirect MRO, same ₹2–10L band.
- Steps are the I1 set. Quotes pass (3 of 3).
- The names in the thread (Anil Reddy) differ from the ledger (V. Iyer). That's text noise; the ledger governs.

**TEST-005 · composed · I3.**
- Ledger: the bank details changed 22 days before the request, which is inside the 30-day window.
- Budget is 2.0% over; the maintenance log confirms line 3 is down. Approver available.
- I3 precedents PR-2026-0312 and 0484 are a **yes**: indirect MRO, up to ₹2L, line down, bank change plus overrun.
- The precedents' "less than two weeks" describes those cases; it isn't a stated condition. The policy window is 30
  days.
- Steps are the I3 set: expedite the PO but hold the payment until the callback. F1 is satisfied.

**TEST-019 · composed · I3 · adversarial.**
- The ledger bank field is clean, but the vendor's email says "We have a new bank account", and staff reply
  "will process payment to new account". A bank change claimed only in the text is a bank failure
  (`bank_details_changed`).
- Budget is 4.9% over; the maintenance log confirms line 3 is down. Quotes are 3 of 3.
- TEST-018 is +441.7%, so it isn't a duplicate.
- I3 precedent PR-2026-0690 (₹4.40L, indirect MRO, ₹2–10L band) is a **yes**.
- Steps are the I3 set.
- Adversarial because the risk appears only in the text.

**TEST-011 · composed · I2 · novel.**
- The IATF 16949 certificate expired 6 days before the request.
- The vendor is flagged sole-source, with 1 of the 3 quotes required for ₹4.40L.
- E1 is a **yes**: PR-2026-0586 and 0633 are direct material in the ₹2–10L band, and the vendor is otherwise in good
  standing (clean quality record, recertification audit done).
- E6 is a **yes**: PR-2026-0288 (₹4.50L). The ledger's sole-source flag meets the E6 override condition that the
  approved-vendor list must show a single source.
- The seed history has no precedent for cert expiry plus sole source together, so `novel_combination` is true.
- Steps are the SPEC §13 I2 human answer: a conditional PO with incoming QC in place of HOLD_PO.

**TEST-015 · composed · I2 · novel.**
- Same vendor as TEST-011, ₹3.30L; certificate expired 9 days before; flagged sole-source; 1 quote.
- TEST-011 is −25.0%, so it isn't a duplicate. E1 and E6 are both **yes**, for the same reasons as TEST-011.
- Steps are the I2 set.

**TEST-030 · composed · I2 · novel.**
- ISO 9001 expired 4 days before; flagged sole-source; ₹6.75L with 1 quote.
- E1 is a **yes** (PR-2026-0633, ₹6.10L direct material). E6 is a **yes** (PR-2026-0470, ₹6.80L).
- Steps are the I2 set.
- The attachment's OCR text contradicts itself ("Expired 02 Nov" / "Valid till 02 Nov 2026"). The ledger governs.

**TEST-032 · composed · I2 · novel.**
- ISO 9001 expired 7 days before; flagged sole-source; ₹2.60L with 1 quote.
- TEST-030 is −61.5%, so it isn't a duplicate. E1 is a **yes** (₹2–10L direct material). E6 is a **yes**
  (PR-2026-0355, ₹2.40L).
- Steps are the I2 set.
- The attached certificate reads "Valid To 01-12-2026", which contradicts the ledger (expired 2026-11-02). The ledger
  governs; the mismatch is worth a human look.
- Finance says "wait for the new cert before release", which leans towards HOLD_PO. I kept the SPEC §13 I2 answer
  anyway.

### Post-July capex, approver away (E3, M6)

**TEST-002 · known · E3.**
- Capex (a portable press, capitalised). E-107 is on leave; delegate E-115 is valid up to ₹2L; ₹1.65L.
- PR-2026-0720 and 0758 (capex, up to ₹2L, after the 1 Jul memo) are a **yes**. The earlier non-capex E3 cases are
  superseded for capex by the memo.
- Steps: ROUTE_DELEGATE and ADD_CONTROLLER_SIGNOFF. F2 isn't triggered: the amount is within the delegate's limit
  and the delegation is valid.

**TEST-004 · known · E3.**
- Capex (a UPS, capitalised). ₹1.48L, same approver and delegate as TEST-002.
- TEST-003 is −76.1%, so it isn't a duplicate.
- The same precedents are a **yes**, and the steps are the same.
- In the thread, a non-delegate (Meena Patel) says she'll "sign off for now". That isn't a valid route; the
  registered delegate is E-115.

**TEST-039 · known · E3.**
- Capex (a torque-testing station). E-110 is on leave; delegate E-117 is valid 23 Nov–4 Dec up to ₹2L, and the
  request (25 Nov, ₹1.85L) falls inside both.
- The same precedents are a **yes**. Steps: ROUTE_DELEGATE and ADD_CONTROLLER_SIGNOFF.

### Override context (M7)

**TEST-013 · known · E2 override.**
- Budget is 2.1% over. The line-down claim is contradicted: the maintenance log shows line 2 running.
- The E2 experiences are a **no**: their line-down condition is contradicted, and they were overridden in this
  context.
- Override PR-2026-0701 is a **yes**: same check and cause, the line-down claim is unsupported by the log, ₹1.75L
  indirect MRO, same band.
- Steps: REQUEST_MORE_INFO. `after_override` is true.

**TEST-020 · known · E4 override.**
- PR-2026-0953 is +2.1% and 16 days earlier, so the duplicate check fails.
- The vendor has a duplicate invoice from 2025, which internal audit flagged.
- The E4 experiences are a **no**: overridden for a vendor with a duplicate-invoice history.
- Override PR-2026-0735 is a **yes**: crates, ₹92k indirect MRO, same band.
- Steps: REJECT_REQUEST and ESCALATE_AUDIT. `after_override` is true.

**TEST-027 · known · E6 override.**
- 1 of the 3 quotes required for ₹3.40L. The vendor isn't flagged sole-source, and the approved-vendor list shows a
  second approved vendor for EN19.
- TEST-021 is −72.6%, so it isn't a duplicate.
- The E6 experiences are a **no**. Override PR-2026-0746 (₹3.10L direct material, second approved vendor exists) is
  a **yes**.
- Steps: COLLECT_QUOTES. `after_override` is true.

### Unknown (U1, U2)

**TEST-016 · unknown · U1.**
- The justification cites a personal relationship with the vendor ("is my sister"), so this is a related-party
  failure. No precedent exists.
- Steps are the SPEC §13 U1 answer. Everything else passes.

**TEST-036 · unknown · U1.**
- The requester says "I am a sleeping partner in Kazipet", which is a related-party failure. No precedent exists.
- There are 3 quotes, and TEST-023 and TEST-026 differ by more than 5%, so neither is a duplicate.
- Steps are the U1 set, **including COLLECT_QUOTES** even though 3 quotes are attached: the connected requester
  obtained them, so fresh independent quotes are reasonable, and it's the SPEC §13 answer.
- If the data owner reads U1 as "COLLECT_QUOTES only when quotes are short", drop it here.

**TEST-022 · unknown · U2.**
- Ledger: GST registration cancelled, so the vendor check fails with cause `gst_cancelled`.
- E1 is a **no** (a different cause). No precedent exists.
- Steps are the U2 set. F4 is satisfied.
- The thread says the quote "shows GSTIN" and finance will pay "as per the quoted GSTIN details". That's a risk, but
  the ledger shows it plainly, so it isn't marked adversarial.

**TEST-037 · unknown · U2. This is the main judgement call.**
- The ledger shows both GST cancelled **and** ISO 9001 expired 5 days before. The text talks only about the
  certificate lapse.
- `causes` allows one cause per check. I labelled `vendor: gst_cancelled` as the controlling and more serious
  cause.
- E1 is a **no**: its condition "otherwise in good standing" is contradicted by the cancelled GST.
- Steps are the U2 set only.
- I deliberately left out REQUEST_RENEWED_CERT and KEEP_VENDOR_ACTIVE: the expired certificate doesn't matter until
  the GST question is settled, and REQUEST_MORE_INFO sends the request back anyway.
- The data owner may want to add REQUEST_RENEWED_CERT.

### Composed without an interaction precedent

**TEST-012 · composed · E1+E4 · novel.**
- ISO 9001 expired 9 days before.
- PR-2026-0846 is +4.1% and 20 days earlier; the text says this is its second shipment. So the duplicate check fails.
- TEST-008 is −93.0%, so it isn't a duplicate.
- E1 is a **yes**: PR-2026-0417 (₹1.40L, direct material), and the vendor is otherwise in good standing (good
  delivery record, renewal audit done).
- E4 is a **yes**: PR-2026-0402 (₹1.30L direct material, second shipment), and the text says there are no invoice
  issues, so the E4 override doesn't apply.
- No precedent covers the combination, so `novel_combination` is true. Steps are the union of the two lessons; no
  pair in `conflicts.yaml` applies.
- The emails are dated 22–24 Sep but mention the 3 Oct expiry, which is synthetic timeline noise. The ledger
  governs.

**TEST-024 · unknown (not composed) · blacklisted vendor + E5 · adversarial.**
- Ledger: the vendor is **blacklisted**, so the vendor check fails with cause `blacklisted`.
- The ledger bank field is clean, but the vendor's email announces a new bank account and staff reply "Will update
  our payment system". That's a bank failure claimed in the text.
- Bank is covered: E5 PR-2026-0118 (₹64k indirect MRO, up to ₹2L) is a **yes**.
- Vendor is **uncovered**: the seed history has no blacklisted precedent. So the class is `unknown`, with
  `uncovered_checks` = `[vendor]`.
- `test_reduced.json` groups this case as "composed without interaction precedent". That group was built from
  families before labelling, and the class rule makes it `unknown`.
- Steps:
  - REJECT_REQUEST, from policy.md §2.2: "Blacklisted vendors may not be used".
  - The E5 lesson (VERIFY_BANK_CALLBACK, HOLD_PAYMENT, HOLD_PO), which F1 requires anyway.
  - No conflict pair applies.
- I considered ESCALATE_AUDIT, since a blacklisted vendor plus a bank-change email looks like fraud. I left it out
  because the policy only says audit *may* review.
- `novel_combination` is true because the combination has no precedent.

### Known or generalized single check

**TEST-007 · generalized (the reduced set calls it "known") · E5.**
- Ledger: bank details changed 26 days before the request, so the bank check fails.
- TEST-005 is +14.2%, so it isn't a duplicate.
- The item is a chain hoist to be **capitalised**, so the category is capex. The E5 precedents cover direct
  material, indirect MRO and services, but none is capex.
- Under the verdict guide, a different category makes the best verdict **partial**, so the class is `generalized`.
  The listed difference is category (capex against indirect MRO or direct material).
- Steps are the E5 set.
- If the generalized class is merged into known (the CLAUDE.md cut order), this becomes `known`.

**TEST-025 · known · E5 · adversarial.**
- The ledger is clean. The vendor emails "we have moved to a new bank account for all future payments", which covers
  this PO's payment, and the requester answers "No action needed". That's a bank failure claimed in the text.
- The item is mounting plates for a customer order (direct material), ₹4.60L. E5 PR-2026-0233 (₹3.20L), 0309 and
  0672 are a **yes** (₹2–10L band).
- Steps are the E5 set.
- The thread says the PO was "generated" on 28 Oct, before the 30 Oct request date. I kept HOLD_PO because the
  E5 lesson includes it.

### Normal

**TEST-009 · normal.**
- ₹8,400 against ₹10,000 left in CC-ADMIN, so it fits.
- Nothing else fails; empty step set.
- The nearly exhausted budget isn't a failure.

**TEST-028 · normal · adversarial.**
- The vendor says its bank details "remain unchanged", which isn't a claim of a change. The ledger is clean.
- TEST-009 is +614.3%, so it isn't a duplicate. Nothing fails; empty step set.
- Adversarial because the case mentions bank details without any change.

## Items for the data owner to confirm before freezing

1. **TEST-037:** whether to add REQUEST_RENEWED_CERT alongside the U2 set.
2. **TEST-036:** whether COLLECT_QUOTES stays when 3 quotes are already attached.
3. **TEST-024:** labelled `unknown` although the reduced set groups it as composed; ESCALATE_AUDIT is left out.
4. **TEST-007:** labelled `generalized` (capex category) although the reduced set groups it as known.
5. **TEST-015, 030 and 032:** `novel_combination` is true against the seed history only.
6. **`adversarial`** follows the text-only-risk convention above. It's used only for reporting.
7. **One labeller:** the test split has a single labeller, and it's the same model family that builds the system.
   A human spot-check of at least the items above would strengthen the benchmark's independence claim.
