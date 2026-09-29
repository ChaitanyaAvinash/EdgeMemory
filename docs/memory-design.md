# Memory design (SPEC §8, with real examples)

> **Synthetic data.** Every lesson quoted below is verbatim Hindsight output from the `kaveri-demo` bank during
> the scripted rehearsal on 28 Sep 2026 (`scripts/rehearse.py`). Case IDs starting with `PR-DEMO-` were created
> live in that run.

## What goes into memory, and why it's tagged that way

Every resolved exception becomes one memory in a fixed template (`api/memory/records.py`), with step codes
written literally so the extracted facts keep them.

| Kind | When | `document_id` | Tags |
|---|---|---|---|
| `experience` | A resolved single-check exception, or a resolved unknown | case ID | `step:<check>` (or `signal:<name>`) |
| `interaction` | A resolved multi-check case whose steps differ from the plain combination | case ID | `interaction` and `combo:<checks>` **only** |
| `confirmation` | A lesson approved unchanged | new case ID | the lesson's tags |
| `override` | A reviewer rejected or edited a recommendation | `<case ID>-override-1` | the overridden lesson's tags |
| `policy_change` | A policy memo | `POLICY-2026-07-01` | `step:approver`, `policy` |

**Interaction lessons carry only `interaction` and `combo:` tags, so they never pollute single-check
lessons.** Observations are consolidated **per tag** (`observation_scopes: "per_tag"`), so each check and
each combination gets its own lesson.

Two findings from the real API changed the recall design (see `docs/api-notes.md`):

- **D6.** Hindsight types most case facts as `world`, so recall always includes `world`.
- **D15.** With per-tag scopes, an observation under `interaction` alone would merge every combination. So
  EdgeMemory recalls interactions by their `combo:` tags.

## Recall, citation, verification

- **One tagged recall per failed check** (`tags_match="any_strict"`), plus a recall over every combination tag
  when several checks fail.
- **Citations.** For an observation, the case IDs come from its source facts (`source_fact_ids` → the source
  fact's `document_id`); for a fact, from its `document_id`. Every case ID must exist in the ledger. On Gate G1,
  52 of 52 citations resolved.
- **Scores are never thresholded.** One verifier call per case judges every candidate: same check, same
  cause, conditions hold, no later policy change, same amount band and category. Code guards can only lower
  its verdict.

## How a lesson matures (C3): real observation history

The first expired-certificate case in the demo bank had no precedent. It was **unknown**, and it escalated.
The analyst resolved it. Hindsight consolidated a lesson, then revised it with each later case. Here is the
observation's own history, from Hindsight's `get_observation_history`:

1. *"…an expired ISO 9001 certificate triggers a hold rather than a rejection; the procedure involves step
   codes REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, and HOLD_PO, as applied in case PR-DEMO-E1-01."*
2. *"… as applied in cases PR-DEMO-E1-01 and PR-DEMO-E1-02."*
3. *"… as applied in cases PR-DEMO-E1-01, PR-DEMO-E1-02, and PR-DEMO-R001."*
4. *"… as applied in cases PR-DEMO-E1-01, PR-DEMO-E1-02, PR-DEMO-R001, and PR-DEMO-R002."*
5. Now: *"For vendors with clean delivery records and completed renewal audits, an expired ISO 9001
   certificate triggers a hold rather than a rejection; the procedure involves step codes
   REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, and HOLD_PO, as applied in cases PR-DEMO-E1-01, PR-DEMO-E1-02,
   PR-DEMO-R001, PR-DEMO-R002, and PR-DEMO-E1-03."*

The ledger's snapshots (`observation_snapshots`) recorded the same growth: 1 case → 2 → 4 → 5.

The code turns this into review effort (SPEC §5.4, §5.5):

- **one supporting case = tentative**, so the analyst confirms step by step;
- **two or more = established**, so the case is one-click.

In the rehearsal, the case after the replay was **known, established, one-click**.

## How an override revises a lesson in context (C3)

The seeded split-shipment lesson already carried its condition:

> *"…the procedure is to apply step codes LINK_MASTER_PO and ALLOW_SPLIT_DELIVERY to link the request to the
> master PO, provided the vendor has no history of duplicate invoices. This lesson is supported by cases
> PR-2026-0266, PR-2026-0402, PR-2026-0477, PR-2026-0569, and PR-2026-0648."*

A split shipment came from a vendor that had a duplicate-invoice incident. The reviewer **rejected** the
recommendation and wrote why. EdgeMemory then did three things:

1. It retained an `override` memory and the reviewer's own decision.
2. It recorded the override's context on the cited ledger lessons. The lessons stay active elsewhere.
3. It waited for consolidation and took snapshots.

Hindsight formed a **separate, context-specific lesson**:

> *"When a procurement request is flagged as a duplicate but the vendor has a history of duplicate-invoice
> incidents, the standard split-shipment resolution procedure is overridden; the request must be handled
> using step codes REJECT_REQUEST and ESCALATE_AUDIT to prevent potential double payment. This lesson is
> supported by cases PR-DEMO-E4-01 and PR-DEMO-E4-02."*

The next split shipment from the same vendor was recommended **REJECT_REQUEST + ESCALATE_AUDIT**. The original
lesson still holds for vendors without that history.

**When memory merges an override into the lesson it revised.** Consolidation can fold an override into the
same observation as the standard lesson. The test benchmark showed what goes wrong then (TEST-013, TEST-027):
- the verifier judged the merged memory as a whole and correctly said the standard lesson didn't apply;
- but the override's own answer was lost, so the case was escalated.

So the detector now splits every per-check memory that mixes override cases with standard ones into two
candidates:
- the standard cases;
- the overrides, each shown with the context its reviewer recorded.

The verifier judges the override on its own:
- **"yes"** when the request shares the override's context: the lesson comes from the override;
- **"no"** otherwise: the standard lesson applies.

On dev, the verifier said "no" to the override in all four cases where it was split out and the context didn't
apply, and the procedures were unchanged. An exception case that still ends up with no steps is flagged
`empty_procedure` and escalated.

## Interaction lessons (C2)

These are consolidated per combination from the seed history:

> **`combo:bank+budget`**: *"When a bank detail change coincides with a line-down budget overrun, the
> procurement policy allows for immediate PO release via steps EXPEDITE_PO, ALLOW_BUDGET_OVERRUN,
> ATTACH_LINE_DOWN_EVIDENCE, and ADD_CONTROLLER_SIGNOFF, while mandating HOLD_PAYMENT and
> VERIFY_BANK_CALLBACK to ensure security; this procedure was applied in cases PR-2026-0312, PR-2026-0484,
> and PR-2026-0690."*

> **`combo:approver+budget`**: *"When an approver is on leave and a budget overrun occurs, the standard
> delegation process is bypassed to prevent stalls; the procedure requires ROUTE_NEXT_LEVEL_APPROVER,
> ADD_CONTROLLER_SIGNOFF, ALLOW_BUDGET_OVERRUN, ATTACH_LINE_DOWN_EVIDENCE, and EXPEDITE_PO, as demonstrated in
> cases PR-2026-0360, PR-2026-0515, and PR-2026-0620."*

In the ₹4.8L hook case both applied:

- **The PO hold was removed,** citing PR-2026-0312, PR-2026-0484 and PR-2026-0690.
- **The delegate was replaced** by the next-level approver, citing PR-2026-0360, PR-2026-0515 and PR-2026-0620.
- **The payment stayed held** until the bank callback.

Removing a risk-control or compliance step like `HOLD_PO` is allowed **only** when the reasoning cites a
verified interaction precedent. Otherwise code restores the step and flags it (CLAUDE.md rule 5).

## Dating lessons against a policy change

The 1 Jul 2026 memo (capex delegate approvals need Finance Controller co-sign) is retained as a
`policy_change` memory and stored in `policy_changes`. The verifier sees which cited cases predate it. As a
code backstop, any coverage citing a case dated before a policy change on the same tag is flagged, and review
becomes step by step (SPEC §8.8).

## What the vector baseline (arm D) doesn't have

Arm D stores the same memories as one chunk each, filters by the same tags, and searches by local-embedding
cosine within the same context budget. It has no consolidation, no observation history, no temporal
reasoning, and no reflect: one LLM call composes instead. The benchmark's C vs D comparison measures what
that difference is worth.
