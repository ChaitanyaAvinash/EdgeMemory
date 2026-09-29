# EdgeMemory: build spec (v2)

This is the source of truth for the build. `CLAUDE.md` holds the standing rules, and `docs/api-notes.md` (written in Phase 0) holds verified API details. The plan assumes a 7-day build by a team of 3–4.

## 0. How to use this spec

- Build in the phase order of §17. Every phase ends with a gate that has pass/fail numbers.
- Section numbers are stable, so refer to them in commits and phase reports ("implements §7.1").
- Appendix A maps every gap found in the pre-build review to the section that closes it. Keep it true: if you change a decision, update the appendix.

## 1. Problem, persona and value

### 1.1 The problem

A purchase request is designed to follow a happy path: budget check, vendor check, approval, then purchase order. Many real requests break one or more of those checks. Typical breaks are an expired vendor certificate, an approver on leave, an order that looks like a duplicate, or vendor bank details that changed last week. A senior analyst resolves each break from experience, and that experience isn't written in the policy document.

When the senior analyst is away or leaves, one of two things happens:

- new analysts escalate everything, which is slow and makes the senior a bottleneck, or
- they improvise, which is risky. Paying to a recently changed bank account is a classic route to payment fraud.

A generic AI agent is worse still: it answers confidently with nothing to ground the answer.

### 1.2 Persona and demo characters (fictional)

- **Ananya Rao**, a Procurement Operations Analyst three weeks into the job. She is the user.
- **Ravi Menon**, the senior analyst with 9 years at the company. He's on leave during the demo, and his past resolutions are the seed memory.
- **Kaveri Precision Components Pvt Ltd**, a fictional Hyderabad manufacturer of precision machined parts with about 1,200 employees and 5 cost centres.

### 1.3 What EdgeMemory delivers

For each exception, it tells the analyst:

- which checks broke,
- how each break was resolved before (with the case cited),
- what changes when several breaks occur together,
- what is not known, and
- how confident the precedent is: tentative (one case) or established (several).

It keeps the resolution procedure within a safety floor, keeps an audit trail of why each exception was handled the way it was, and learns from every human decision.

### 1.4 How value is measured (all computed in code; definitions in §10)

- **Review effort per 10 cases**: escalations, plus edits, plus confirmations.
- **Estimated analyst minutes per 10 exception cases.** Assumptions are shown next to the figure and live in `config/assumptions.yaml`.
- **False confidence**: target 0.
- **Risk-floor violations**: target 0.

### 1.5 Who pays (hypothesis, labelled as one in the README)

The buyer is the Head of Procurement or the Finance Controller at an Indian manufacturer with 500–5,000 employees. The price hypothesis is about ₹4,000 per analyst seat per month, which is the "would someone pay $50/month" test.

## 2. The four claims and what proves each

| Claim | Meaning | Proven by (benchmark) | Shown in (demo) |
|---|---|---|---|
| C1 Per-check coverage | Each failed check is matched separately, so known, composed and unknown follow from one rule | Confusion matrix; procedure F1 per class | Case view: each failed check lights up with its precedent |
| C2 Interaction-aware composition | Several failures together can need a different procedure than their union; learned from humans | Arm C vs arm E on interaction cases; novel-combination flag recall | The ₹4.8L case: two interaction precedents change the plain union |
| C3 Lessons mature and get revised | 1 case = tentative; confirmations make it established; overrides revise it; policy changes date it | Arm C vs arm D: post-override correctness, outdated-lesson use, learning-curve slope | Tentative → established beat; override → observation revision beat |
| C4 Honest unknowns | No verified precedent means escalation with what's covered and what isn't | False confidence = 0; arm F ablation | Related-party case escalates |

## 3. Architecture and component ownership

The pipeline runs in this order:

1. **Intake:** form fields, free-text justification, an optional email thread and optional certificate text.
2. **Signal extractor (LLM):** fields and edge signals, each with the source span it came from.
3. **Rule engine (code):** six checks plus mapped signals. Each failure becomes a violation.
4. **No violations:** the case is Normal and goes to the standard route. Memory isn't called.
5. **Violations:**
   1. **Recall (per violation, in parallel):** recall through the MemoryBackend.
   2. **Interaction recall (when 2 or more violations):** one interaction recall.
   3. **Verify:** one batched verifier call for the whole case, covering every violation's candidates and the interaction candidates (§5.2).
   4. **Classify (code):** class, maturity, flags and review mode.
   5. **Compose:** a deterministic union, then reflect (or one LLM call in arm D), then validation in code.
   6. **Conflicts and risk floor (code).**
   7. **Human review:** approve, confirm step by step, edit, reject, or resolve an unknown.
   8. **Retain:** the result becomes an experience, interaction, override or confirmation, and observation snapshots are taken.

| Component | Owns | Never does |
|---|---|---|
| Hindsight (via `MemoryBackend`) | Resolved experiences, interaction lessons, overrides, policy memos, consolidated observations, reasoning across cases | Holding the exact record; ledger rows are the record |
| SQLite ledger | Master data, requests, violations, coverage, procedures, decisions, lessons, snapshots, LLM call log, eval runs | Deciding relevance |
| LLM (`llm.py`) | Signal extraction, verifying whether a precedent applies, narrative explanations | Counting, or releasing anything |
| Deterministic code | Checks, classification, maturity, review mode, union, citation validation, conflicts, risk floor, metrics | Guessing |
| Human | The final decision, which is then retained | — |

Repo layout:

```
repo/
  CLAUDE.md
  README.md
  Makefile
  .env.example
  config/
    models.yaml        # model per role, fallbacks
    limits.yaml        # RPM/TPM, daily token budget
    assumptions.yaml   # minutes-saved assumptions
    step_library.yaml
    conflicts.yaml
  api/
    main.py            # FastAPI routes
    llm.py             # Groq (httpx) and Gemini (google-genai) clients, schema, validation, retries, fallback chain, rate limiter, daily request/token counters, cache, logging
    ledger.py          # SQLModel tables and deterministic statistics
    memory/
      backend.py       # MemoryBackend protocol and shared types
      hindsight_backend.py
      vector_backend.py   # arm D: local embeddings and cosine search in NumPy
      citations.py     # result → case IDs (facts and observations)
    engine/
      extractor.py
      rules.py
      detector.py      # per-violation and interaction recall, batched verification
      classify.py      # class, maturity, review mode
      composer.py      # union, reflect, validation, diff
      precedence.py    # conflicts and risk floor
      pipeline.py      # orchestrates one request for any arm
    metrics.py
  scripts/
    phase0_spike.py        # verifies Hindsight, Groq and Gemini calls, measures requests, tokens and latency
    import_history.py      # CSV → ledger and memory (seeding and customer cold start)
    generate_cases.py      # case specs → messy narratives
    estimate_budget.py
    gate1.py
  eval/
    run_arms.py
    replay.py
    report.py
  data/
    seed/
    cases/
    ground_truth/          # blind, frozen; never read by api/engine or api/memory
  web/                     # Next.js
  docs/
    SPEC.md
    api-notes.md
    memory-design.md
    benchmark.md
    adoption.md
    content/               # outlines for team members' articles, posts, videos
  tests/
```

## 4. Checks and extracted signals

The six ledger checks (`engine/rules.py`):

| Check (tag) | Passes when |
|---|---|
| `budget` | The amount fits the cost centre's remaining budget for the fiscal year (Indian FY, April–March) |
| `vendor` | The vendor is active, its GST registration is active, and every required certificate is valid on the request date. **The failure detail must name the cause** (`cert_expired`, `gst_cancelled`, `blacklisted`), because U2 depends on it. |
| `approver` | The approver for this cost centre and amount is present on the request date (not on leave) |
| `duplicate` | No request to the same vendor within ±5% of the amount in the last 30 days |
| `bank` | The vendor's bank details haven't changed in the last 30 days |
| `quotes` | At least three quotes are attached when the amount is over ₹2,00,000 |

Extracted signals (`engine/extractor.py`) come with source spans and map to violations as follows:

- `bank_change_claimed`: the text says the vendor has new bank details, even if the ledger doesn't show it yet. This becomes a `bank` violation with source "email".
- `related_party`: the requester is connected to the vendor. This becomes a violation with tag `signal:related_party`.
- `urgency`, with values `line_down`, `urgent` or `normal`, is an attribute rather than a violation. Lessons and the verifier use it.
- `category`: `direct_material`, `indirect_mro`, `capex` or `services`.
- Amounts are normalised from "4.8L", "₹4,80,000" or "480000" into integer rupees, in code, after the LLM extracts the raw string.

**Adversarial rule:** the extractor must not create violations that aren't there. A certificate expiring next month is not expired, and an amount 6% away from a recent one is not a duplicate. The adversarial cases in §13 test this.

## 5. Classes, coverage, maturity and review mode

### 5.1 Verifier verdicts (shared with the ground-truth labeller)

The same text goes in the verifier prompt and in `data/ground_truth/LABELLING_GUIDE.md`.

- **yes:** same failed check, same cause, the precedent's conditions hold (for example, "vendor otherwise in good standing"), and no relevant policy change since the precedent. A different vendor or amount is fine if it's within the same amount band (up to ₹2L, ₹2–10L, over ₹10L) and the same category.
- **partial:** same check and same cause, but a different amount band or category, or one of the precedent's conditions can't be confirmed from the request. **The differences must be listed.**
- **no:** a different cause (for example, GST cancelled versus certificate expired), a precedent condition that the request contradicts, a precedent overridden in this context, or a precedent superseded by a later policy memo.

### 5.2 Aggregating candidates to one status per violation

By default the verifier gets **one call per case** (`verifier_batching: per_case`). That call covers every violation's candidates, plus the interaction candidates when there are 2 or more violations, and returns a verdict, differences and a reason for each candidate. If dev-set accuracy turns out lower than with one call per violation, switch to `per_violation`; it uses more requests and tokens, and Groq's tokens per day are what the free tier limits. The violation's coverage status is the best verdict (yes > partial > no) among candidates that carry the matching tag. Ties are broken first by precedent strength (§5.4), then by the most recent resolution date. All verdicts are stored in `coverage`.

Candidates whose supporting cases are all overridden are still shown to the verifier, annotated from the ledger as "OVERRIDDEN on <date>: <reason>". They count for nothing in precedent strength.

### 5.3 Classification

The code below is written in `engine/classify.py`; make it pure and unit-tested.

```python
def classify(violations, coverage, interaction) -> Classification:
    if not violations:
        return Classification(cls="normal")
    uncovered = [c for c in coverage if c.status == "no"]
    if uncovered:
        # compose what is covered, escalate the rest
        return Classification(cls="unknown", uncovered=uncovered)
    if len(violations) > 1:
        return Classification(
            cls="composed",
            novel_combination=(interaction is None or interaction.status != "yes"),
        )
    return Classification(cls="known" if coverage[0].status == "yes" else "generalized")
```

### 5.4 Precedent strength and maturity (the answer to learning from a single case)

- **Precedent strength** of a covered violation is the number of distinct resolved cases that support the matched lesson and are not overridden. It is computed by mapping citations (including an observation's source facts) to case IDs, then checking in the ledger that each case's final steps contain the lesson's steps for that check.
- The maturity is **tentative** at strength 1 and **established** at strength 2 or more.
- A case's maturity is the lowest maturity among the lessons it uses, including any interaction precedent.

### 5.5 Review mode (computed in code; it also drives the review-effort metric)

| Condition | Review mode |
|---|---|
| Class `unknown` | Escalate: a resolution form for the uncovered checks; covered steps are pre-filled |
| Class `generalized`, any tentative lesson, `novel_combination`, or any policy flag | Step by step: the analyst ticks each step |
| Class `known` or `composed`, all lessons established, no flags | One click, with citations visible |

That makes learning from a single case safe. One decision creates a tentative lesson that a human must confirm step by step. Only repeated agreement unlocks one-click review. The demo shows this progression (§18).

## 6. Step library, conflicts and the risk floor

### 6.1 Step library (`config/step_library.yaml`, 25 codes)

| Class (priority, highest first) | Codes |
|---|---|
| Risk control | `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`, `ESCALATE_AUDIT`, `DECLARE_CONFLICT_OF_INTEREST` |
| Compliance | `HOLD_PO`, `REQUEST_RENEWED_CERT`, `VERIFY_GST_STATUS`, `SOLE_SOURCE_FORM`, `COLLECT_QUOTES`, `CONDITIONAL_PO_WITH_QC`, `INCOMING_QC_INSPECTION`, `ATTACH_LINE_DOWN_EVIDENCE` |
| Approval routing | `STANDARD_APPROVAL`, `ROUTE_DELEGATE`, `ROUTE_NEXT_LEVEL_APPROVER`, `ADD_CONTROLLER_SIGNOFF`, `CATEGORY_HEAD_SIGNOFF`, `ADD_CFO_SIGNOFF` |
| Convenience | `ALLOW_BUDGET_OVERRUN`, `EXPEDITE_PO`, `LINK_MASTER_PO`, `ALLOW_SPLIT_DELIVERY`, `KEEP_VENDOR_ACTIVE` |
| Outcome | `REQUEST_MORE_INFO`, `REJECT_REQUEST` |

No code releases a payment.

### 6.2 Conflicting step pairs (`config/conflicts.yaml`)

- `HOLD_PO` ↔ `EXPEDITE_PO`
- `HOLD_PO` ↔ `CONDITIONAL_PO_WITH_QC`
- `ROUTE_DELEGATE` ↔ `ROUTE_NEXT_LEVEL_APPROVER`
- `REJECT_REQUEST` ↔ any of `EXPEDITE_PO`, `CONDITIONAL_PO_WITH_QC`, `LINK_MASTER_PO`, `ALLOW_SPLIT_DELIVERY`

**Default resolution:** the higher-priority class wins, and within a class the more conservative step wins.

**Precedent resolution:** if a verified interaction precedent (§7) for a subset of this case's failed checks chose the lower-priority step, keep the precedent's choice, provided the risk floor still holds afterwards.

Every conflict is recorded and shown with its reason, either "default priority" or "precedent PR-…".

### 6.3 Risk floor (`engine/precedence.py`; runs last, in every pipeline arm)

| ID | Condition | Floor action |
|---|---|---|
| F1 | Bank details changed in the last 30 days (ledger) or `bank_change_claimed` | Must include `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT` |
| F2 | `ROUTE_DELEGATE` is present and the delegate's `max_amount` is below the amount, or the delegation isn't valid on the request date | Replace it with `ROUTE_NEXT_LEVEL_APPROVER` |
| F3 | `related_party` signal | Must include `DECLARE_CONFLICT_OF_INTEREST`; review can never be one-click |
| F4 | Vendor GST is cancelled | Must include `VERIFY_GST_STATUS` and `HOLD_PO`; no precedent can remove them |
| F5 | Any step outside the library | Drop it and flag it |

Steps added by the floor are labelled "Added by safety floor" in the UI. They are never presented as learned from memory, and the floor never changes the class.

## 7. Composition (closes the "it's just a union plus a priority table" gap)

### 7.1 Algorithm (`engine/composer.py`)

1. **Single lessons (deterministic).** For each covered violation, take the supporting cases (from citations). The lesson's steps are the ones that appear in the final decisions of at least half of those supporting cases, restricted to supporting cases of kind `experience` or `confirmation`.
2. **Union `U`** is all the single-lesson steps together, each tagged with its source cases.
3. **Interaction precedent `P` (only when 2 or more violations).** Run an interaction recall (§8.4); its candidates are verified in the same per-case verifier call (§5.2). `P` is the best verified interaction whose combination of failed checks is a subset of this case's failed checks. More than one can apply (for example I1 and I3 together).
4. **Reflect** (arm D uses one LLM call with the same schema instead). The inputs are:
   - the request summary,
   - the violations with their verdicts and differences,
   - `U` with source cases,
   - each `P` with its final steps and cases, and
   - the step library.

   The instruction is: "Start from U. Adapt for listed differences. Apply each interaction precedent's changes. Give a reason and a cited case ID for every step, and for every step you remove from U." The response schema is `Procedure { steps: [{code, reason, cited_case_ids}], removed_from_union: [{code, reason, cited_case_ids}], open_questions: [str] }`.
5. **Validate (code).**
   - Every code must be in the library.
   - Every step must cite at least one verified case for this request.
   - **Removing a risk-control or compliance step from `U` requires citing a case from a verified interaction precedent.** Otherwise the step is restored and flagged.
   - Removing a routing or convenience step requires a reason.
   - Map `based_on` to case IDs (§8.6) and check that every cited case appears there or in the verified set.
6. **Conflicts** are resolved as in §6.2.
7. **The risk floor** is applied as in §6.3.
8. **Diff against `U`,** displayed as "Changed from the plain combination: −HOLD_PO, +… (precedent PR-2026-0312: a PO is not a payment; payment held until callback)."

**If reflect fails:** fall back to `U` plus default conflict resolution plus the floor. Mark the case "composed without memory reasoning" and force step-by-step review.

**For unknown cases:** compose only the covered violations, and list the uncovered ones for the resolution form.

### 7.2 The interaction families (these make C2 testable)

| ID | Failed checks | Plain union gives | Humans actually did | Status |
|---|---|---|---|---|
| I1 | `approver` + `budget` (overrun) | `ROUTE_DELEGATE` plus E2 steps | `ROUTE_NEXT_LEVEL_APPROVER` instead of delegate (delegates don't approve overruns, even within their limit), plus `ADD_CONTROLLER_SIGNOFF`, `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `EXPEDITE_PO` | Seeded (3) |
| I2 | `vendor` (cert expired) + `quotes` (sole source) | `HOLD_PO`, `REQUEST_RENEWED_CERT`, `KEEP_VENDOR_ACTIVE`, `SOLE_SOURCE_FORM`, `CATEGORY_HEAD_SIGNOFF` | No hold, because a hold leaves no supply at all: `CONDITIONAL_PO_WITH_QC`, `INCOMING_QC_INSPECTION`, `REQUEST_RENEWED_CERT`, `KEEP_VENDOR_ACTIVE`, `SOLE_SOURCE_FORM`, `CATEGORY_HEAD_SIGNOFF` | **Held out**: the system should flag `novel_combination` |
| I3 | `bank` + `budget` (emergency, line down) | Conflict between `HOLD_PO` and `EXPEDITE_PO`; the default keeps `HOLD_PO`, so the production line stays down | `EXPEDITE_PO`, `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`, `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `ADD_CONTROLLER_SIGNOFF` ("a PO is not a payment"); the floor still holds | Seeded (3) |

## 8. Hindsight memory design

**Which LLM Hindsight runs on.** Use Hindsight Cloud, whose own LLM performs retain extraction, consolidation and reflect on the $50 promo credit. That keeps every Hindsight call off the Groq and Gemini free quotas. Phase 0 found that Cloud doesn't let you choose or see that model, so `docs/benchmark.md` states the difference (arm C composes with Hindsight's model, arm D with `openai/gpt-oss-120b`). Self-hosting Hindsight on one of our three models (see CLAUDE.md) stays an option to ask about only if the measured quota has room.

### 8.1 Banks (isolation matters)

| Bank | Used for |
|---|---|
| `kaveri-demo` | Live demo; seeded with everything except E1 and the E4 override, both of which happen live (§18) |
| `kaveri-{split}-{arm}-{run}` | Benchmark runs; fresh bank per run, seeded identically |
| `kaveri-replay-{backend}` | Learning-curve replay; starts empty |

`make reset` deletes and recreates the demo bank and ledger. `VectorBackend` uses the same naming, with a local store directory per bank.

### 8.2 Bank configuration (verify field names in Phase 0)

**`retain_mission`:**

> "Extract how procurement exceptions at Kaveri were resolved: which standard check failed and why, why the standard process did not fit, the exact step codes the human approved, the outcome, and the lesson. Keep case IDs, vendor IDs, dates and rupee amounts exact."

**`observations_mission`:**

> "Form one durable lesson per failed check, and one per combination of failed checks, stating when the exception applies, the procedure as step codes, the supporting case IDs, and any override or policy change that limits it."

**`reflect_mission`** (first person):

> "I help Kaveri's procurement analysts handle purchase requests that break the standard process. I apply lessons from past exceptions cautiously, cite the case behind every step, and say when no lesson applies."

**Disposition:** skepticism 5, literalism 4, empathy 2.

**Directives** (untagged, so they always apply):

1. "Cite the case ID behind every step."
2. "Never recommend releasing a payment. Propose only steps for a human to approve."
3. "Whenever vendor bank details changed recently or are claimed to have changed, include VERIFY_BANK_CALLBACK and HOLD_PAYMENT."
4. "If no experience covers a condition, say so explicitly."
5. "Prefer lessons dated after any relevant policy change; flag any lesson that predates one."

### 8.3 Retain

| Kind (`metadata.kind`) | When | `document_id` | Tags |
|---|---|---|---|
| `experience` | A resolved single-check exception, or a resolved unknown | case ID | `step:<check>` for each failed check (or `signal:<name>`) |
| `interaction` | A resolved multi-check case whose steps differ from the plain union | case ID | `interaction` and `combo:<checks sorted, joined with +>` **only**, so interaction lessons don't pollute the single-check observations |
| `confirmation` | A known lesson approved unchanged | new case ID | the same step tags |
| `override` | A reviewer rejected or edited a recommended procedure | `<case ID>-override-<n>` | the tags of the overridden lesson |
| `policy_change` | A policy memo | `POLICY-2026-07-01` | `step:approver`, `policy` |

**Other retain fields:**

- `timestamp` is the resolution date, or the effective date for a policy memo.
- `context` is `"procurement exception resolution"`.
- `metadata` holds `case_id`, `kind`, `outcome`, `reviewer`, `combo` and `overrides`, all as strings.
- `entities` holds vendor and approver IDs, with `resolve_entities=False`.
- `observation_scopes`: the intent is one consolidated lesson per tag. Use the verified value from `api-notes.md`; if per-tag scoping isn't supported, rely on the tags plus `observations_mission`.
- **Extraction mode:** in Phase 0, retain 5 seed narratives in both `concise` and `verbose` mode. Keep whichever mode's recalled facts preserve the step codes and the "why the standard process didn't fit" sentence, and record the choice.

The content template is below; step codes appear literally so that the extracted facts keep them.

```
Case PR-2026-0417, resolved 14 Mar 2026 by R. Menon (Procurement Ops). Kind: experience.
Failed checks: vendor (cause: cert_expired).
Request: ₹1,40,000 direct material, bearing housings, vendor V-017 (in good standing, 2 years on-time delivery).
What happened: ISO 9001 certificate expired 6 days before the request.
Why the standard process did not fit: the vendor check blocks the vendor outright, but the vendor was otherwise in good standing and renewal was in progress.
Steps approved (codes): REQUEST_RENEWED_CERT, KEEP_VENDOR_ACTIVE, HOLD_PO.
Outcome: renewed certificate received in 3 days; PO released.
Lesson: a recently expired certificate is a hold, not a rejection, when the vendor is otherwise in good standing.
```

### 8.4 Recall

**Per violation, in parallel:**

- `query`: `f"{check} check failed ({cause}): {detail}. {summary}"`, with the summary kept to 60 words or fewer and the whole query truncated to under 500 tokens.
- `tags=[f"step:{check}"]` with `tags_match="any_strict"`
- `types=["experience","observation"]` plus `world` for policy memos
- `prefer_observations=True`, `include={"source_facts": ...}`, `budget="mid"`, `max_tokens=2048`
- `query_timestamp=request.submitted_at`

Deduplicate by case (via citations) and send the top 5 to the verifier. **Don't use score cutoffs.**

**Interaction recall** (one per case, when there are 2 or more violations):

- `tags=["interaction"]` with `any_strict`
- `query`: a description of the failed checks and urgency
- Then filter in code to candidates whose `metadata.combo` is a subset of this case's failed checks and has at least 2 checks.

### 8.5 Reflect

- `tags`: the covered step tags, plus `interaction`, plus the matching combo tags, with `tags_match="any"`
- `response_schema=Procedure.model_json_schema()`
- facts requested through `include` (verify the spelling)
- `budget="mid"`, dropping to `"low"` if the p95 latency on dev is over 10 seconds

Read `structured_output`. If it is missing and `structured_output_error` is set, retry once, then fall back as in §7.1.

### 8.6 Citations (`memory/citations.py`)

- For a fact result, the case comes from `document_id` or `metadata.case_id`.
- For an observation, follow `source_fact_ids`, using `include.source_facts`, and take each source fact's `document_id`, which gives one or more case IDs.
- Strip the `-override-n` suffix and record that the citation came from an override.
- Every returned case ID must exist in the ledger. Unresolvable IDs are dropped and logged.

Unit-test this against recorded JSON fixtures of real responses captured in Phase 0.

### 8.7 Overrides (C3)

When a reviewer rejects or edits a procedure that used lesson L:

1. Retain an `override` memory stating what L recommended, the context, what the reviewer did instead and why, and the date.
2. Retain the reviewer's final decision as an `experience` for the new case, so the corrected procedure has support of its own.
3. The ledger marks L as `overridden` in `lessons` (with its context).
4. Take an observation snapshot (§8.9).

### 8.8 Policy change (C3, temporal)

On 1 Jul 2026 a policy memo takes effect: "For capex requests, when the approver is on leave, the delegate may approve only with Finance Controller co-sign (ADD_CONTROLLER_SIGNOFF)."

- The memo is retained as `policy_change` and stored in `policy_changes`.
- Pre-July E3 lessons (`ROUTE_DELEGATE` alone) are now outdated for capex.
- The rule engine does **not** know this rule. Memory and the verifier must get it right, and that's what the benchmark measures.
- As a deterministic backstop, the code flags (but never changes) any cited lesson dated before a policy change on the same tag. The UI shows "Lesson predates policy change of 1 Jul 2026", and review becomes step by step.

### 8.9 Making consolidation visible

After each retain in the demo or a replay:

1. Wait for consolidation. Poll with backoff up to a limit measured in Phase 0, and show "consolidating…".
2. Fetch the observations for each affected tag: recall with `types=["observation"]` and the tag under `any_strict`, or a list API if one exists.
3. Store in `observation_snapshots` the text, the number of source cases and the fetch time.

The Lesson panel (§15) shows the current observation, the number of cases behind it, and a before/after diff with the previous snapshot. Use Hindsight's own observation history if the API exposes it (check in Phase 0); otherwise the snapshots are the history.

### 8.10 Stretch

A mental model named "Procurement exception map" with `refresh_after_consolidation` set, feeding the boundary map.

## 9. Runtime workflow (`engine/pipeline.py`; the same function runs every arm, with flags)

1. **Intake:** `POST /requests` with form fields, justification, an optional email thread and optional certificate text. `category` and `urgency` come from extraction.
2. **Extract** (cached): the structured request plus signals with source spans; the vendor name is matched to a ledger vendor ID.
3. **Check:** the six checks plus mapped signals produce violations with details and causes.
4. **Normal:** if there are no violations, the case is normal, gets `STANDARD_APPROVAL`, and memory isn't called.
5. **Coverage:** recall each violation in parallel, plus an interaction recall if there are 2 or more violations (§8.4); then make one verifier call for the case (§5.2).
6. **Classify:** §5.3, then maturity and review mode (§5.4, §5.5), then policy flags (§8.8).
7. **Compose, conflicts, floor:** §7 and §6.
8. **Review:** in the UI or the simulated eval reviewer.
9. **Retain:** §8.3 and §8.7, then snapshots (§8.9).

Every step writes to the ledger, so `GET /requests/{id}` can render the whole trace.

## 10. Metrics (`api/metrics.py`; counts shown as "x of n")

| ID | Metric | Definition | Target |
|---|---|---|---|
| M1 | **False confidence** (replaces "unsafe auto-resolutions") | Cases where at least one ground-truth failed check has no valid precedent, but the system marked every check covered and didn't escalate | 0 |
| M2 | Risk-floor violations | Final procedures missing a step required by F1–F4. Zero by construction for arms C–F; the real comparison is against A and B | 0 |
| M3 | Classification | 5-class confusion matrix, and correct as "x of n" | Higher |
| M4 | Procedure F1 | Step-set F1 against ground truth, averaged per class | Higher |
| M5 | Interaction accuracy | On the 8 interaction cases (4 seeded I1/I3, 4 held-out I2): exact match and F1; plus the novel-combination flag rate on I2 | Higher; flag on 4 of 4 |
| M6 | Outdated-lesson use | Post-July capex approver-away cases whose final steps lack `ADD_CONTROLLER_SIGNOFF` | 0 |
| M7 | Post-override correctness | Cases after an override that follow the revised lesson | 3 of 3 |
| M8 | Review effort per 10 cases | Simulated reviewer: escalations (1 each), plus edits (the symmetric difference with ground-truth steps), plus confirmations (one per step in step-by-step mode, one per case in one-click mode) | Lower |
| M9 | Estimated analyst minutes per 10 exception cases | From `config/assumptions.yaml`, compared with a baseline where every exception is researched from scratch; the assumptions are shown next to the number | Lower |
| M10 | Unnecessary escalations | Ground truth is known, generalized or composed, but the system said unknown | Lower |
| M11 | Cost and latency | LLM requests and tokens (including reasoning tokens) per case and per model (Groq and any Gemini fallback), Hindsight calls per case, and p50/p95 seconds per case | Report |

`config/assumptions.yaml` starts with these values, which are labelled as assumptions everywhere they appear:

```yaml
research_unfamiliar_exception_min: 40
step_by_step_review_min: 6
one_click_review_min: 1
edit_min: 2
escalation_min: 40
```

## 11. Data model (SQLModel)

| Table | Key columns |
|---|---|
| `vendors` | id, name, gstin, gst_status, status, cert_expiry, bank_changed_at, sole_source, category |
| `employees` | id, name, role, cost_centre, leave_from, leave_to |
| `delegations` | approver_id, delegate_id, max_amount, valid_from, valid_to |
| `budgets` | cost_centre, fiscal_year, allocated, spent |
| `policy_changes` | id, effective_date, tag, text |
| `requests` | id, submitted_at, vendor_id, amount, cost_centre, category, urgency, requester_id, justification, email_thread, attachment_text, class, maturity, review_mode, novel_combination, status |
| `violations` | id, request_id, check, cause, detail, source, source_span |
| `coverage` | id, violation_id (null for interaction rows), request_id, memory_id, case_ids, verdict, differences, reason, is_interaction |
| `procedures` | id, request_id, arm, steps (JSON: code, reason, cited_case_ids, origin = memory, floor or default), union_steps, removed_from_union, conflicts, flags, raw_output |
| `decisions` | id, request_id, reviewer, action, final_steps, rationale, decided_at |
| `lessons` | case_id, kind, tags, combo, steps, resolved_at, status (`active`, `overridden`, `predates_policy`), overridden_by |
| `experiences` | case_id, document_id, bank_id, retained_at, kind, edge_family (scoring only; never sent to memory or the engine) |
| `observation_snapshots` | id, bank_id, tag, text, source_case_ids, fetched_at |
| `step_library` | code, class, description |
| `llm_calls` | id, role, model, prompt_version, input_tokens, output_tokens, thinking_tokens, finish_reason, latency_ms, cache_hit, error, created_at |
| `quota_usage` | model, pacific_date, requests, tokens (feeds the Gemini daily counters; Groq's rolling 24 h window is counted from `llm_calls`) |
| `eval_runs` | run_id, arm, split, case_id, predicted_class, predicted_steps, review_mode, flags, scores, tokens, latency_ms |

## 12. API (FastAPI)

| Method | Path | Does |
|---|---|---|
| POST | `/requests` | Submit a request; runs the pipeline; returns the case view |
| GET | `/requests/{id}` | Case view: signals with spans, violations, coverage, interaction, procedure, diff against the union, conflicts, floor additions, maturity, review mode |
| POST | `/requests/{id}/decision` | Approve, confirm, edit, reject or resolve; triggers retain and snapshots |
| GET | `/queue` | Open cases grouped by class |
| GET | `/lessons?tag=` | Current observation, supporting cases, status and snapshot history per tag |
| GET | `/memory/trace/{request_id}` | Per violation: what was recalled, the citations, each verdict and why |
| GET | `/audit/export.csv` | Every recommendation, citation, verdict, floor addition and human decision, with timestamps |
| GET | `/eval/results` | Benchmark results per arm, including per-case rows |
| POST | `/admin/seed` · `/admin/reset` | Seed or reset the demo bank and ledger |
| POST | `/demo/clock` | Set the demo date, used for `submitted_at` and `query_timestamp` |
| POST | `/demo/replay` | Fast-forward N scripted cases (resolve and retain) to show maturity |
| GET | `/boundary-map` | (stretch) Counts per edge family and class over time |

## 13. Synthetic data

**Master data:**

- 40 vendors with GSTINs in the correct format for Telangana (state code 36), certificate expiries, GST status, bank-change dates and sole-source flags
- 25 employees across 5 cost centres, with leave calendars
- a delegation matrix with `max_amount` and validity dates
- budgets for FY 2025–26 and FY 2026–27
- a two-page procurement policy (v1), plus the 1 Jul 2026 memo

Everything is labelled as synthetic.

**Edge families and seeds** (seeded through `scripts/import_history.py`, the same path a real customer would use for a cold start):

| Family | Check (cause) | Seeded resolution steps | Seeds |
|---|---|---|---|
| E1 Expired certificate | vendor (cert_expired) | `REQUEST_RENEWED_CERT`, `KEEP_VENDOR_ACTIVE`, `HOLD_PO` | 7 (none in the demo bank; learned live) |
| E2 Emergency overrun (up to 10%) | budget | `ALLOW_BUDGET_OVERRUN`, `ATTACH_LINE_DOWN_EVIDENCE`, `ADD_CONTROLLER_SIGNOFF`, `EXPEDITE_PO` | 6 |
| E3 Approver away | approver | `ROUTE_DELEGATE`; post-July capex also needs `ADD_CONTROLLER_SIGNOFF` | 6 (4 pre-July, 2 post-July capex) |
| E4 Split shipment | duplicate | `LINK_MASTER_PO`, `ALLOW_SPLIT_DELIVERY` | 5 |
| E5 Bank details changed | bank | `VERIFY_BANK_CALLBACK`, `HOLD_PAYMENT`, `HOLD_PO` | 6 |
| E6 Sole source | quotes | `SOLE_SOURCE_FORM`, `CATEGORY_HEAD_SIGNOFF` | 5 |
| I1, I3 | see §7.2 | see §7.2 | 3 each |
| Overrides | one each on E2, E4, E6 | Reviewer rejects a lesson in a specific context (for example, split-shipment treatment for a vendor with a prior duplicate-invoice incident becomes `REJECT_REQUEST` plus `ESCALATE_AUDIT`) | 3 (the E4 override is left out of the demo bank; it happens live) |
| Policy memo | approver | §8.8 | 1 |
| U1 Related party | signal | Held out. Human answer: `DECLARE_CONFLICT_OF_INTEREST`, `ESCALATE_AUDIT`, `COLLECT_QUOTES`, `HOLD_PO` | 0 |
| U2 GST cancelled | vendor (gst_cancelled) | Held out. Human answer: `VERIFY_GST_STATUS`, `HOLD_PO`, `REQUEST_MORE_INFO` | 0 |
| I2 | see §7.2 | Held out | 0 |

There are 45 seed items in total.

**Messiness:**

- informal justifications with typos and some Hinglish ("line 3 band hai, urgent chahiye")
- email threads of 3–6 messages
- certificate snippets that look like OCR output
- amounts written several ways
- some bank changes mentioned only in the email thread

**Benchmark cases: 60, split 20 dev and 40 test, stratified by class**

| Class | Count | Contents |
|---|---|---|
| Normal | 10 | Every check passes |
| Known | 12 | E1–E6 with new vendors and amounts, including **3 post-July capex approver-away cases** (M6) and **3 cases after an override** (M7) |
| Generalized | 6 | A precedent in a different amount band or category |
| Composed | 16 | 4 where the plain union is correct; 4 seeded interactions (2 I1, 2 I3); 4 held-out I2 (novel combination); 4 involving a bank change (floor) |
| Unknown | 10 | 4 U1, 3 U2, and 3 where one violation is uncovered among covered ones |
| Adversarial | 6 | 3 that look like an edge case but aren't (the certificate expires next month; the amount is 6% off); 3 that look normal but hide a risk (a bank change only in the email) |

**Generation and labelling:**

1. Each case starts as a structured spec: family, vendor, dates, amount, category, urgency. `scripts/generate_cases.py` has the LLM write the messy narrative from the spec.
2. The data owner, who **never touches the engine**, writes the ground-truth class and step set from the spec using `LABELLING_GUIDE.md` (the §5.1 text plus family rules).
3. A second teammate labels the 20 dev cases independently, and the agreement is reported as "x of 20".
4. A human spot-checks 20 narratives.
5. Ground truth is committed and frozen at Gate G2.

## 14. Evaluation

### 14.1 Arms (all use the same model, schema, step library and retrieved-context budget)

Every call made from our code (extraction, verification, arm D's composer, arms A and B) uses `openai/gpt-oss-120b` on Groq's free tier. If a call falls back to `gemini-3.8-flash` or `gemini-3.7-flash` (CLAUDE.md fallback order), the run's results say which cases were affected. Arm C's reflect runs on Hindsight Cloud's own, undisclosed LLM (§8), and `docs/benchmark.md` says so.

| Arm | What it is | Isolates |
|---|---|---|
| A | No memory: policy document plus the request, one LLM call | — |
| B | Plain RAG: A plus top-k vector search over the seed narratives (2,048-token budget), one call | What a generic RAG agent gets |
| C | **EdgeMemory:** full pipeline with `HindsightBackend` | — |
| D | **Pipeline with vector memory:** the same pipeline with `VectorBackend` (same narratives, cosine top-k, and one LLM call in place of reflect; overrides and the policy memo are stored as extra chunks, with no consolidation or temporal reasoning) | **What Hindsight adds** (C vs D) |
| E | Union composer: C without interaction recall or reflect, so `U` plus default conflicts plus the floor. It reuses C's single-check coverage from the same run, so it costs no extra LLM requests | **What interaction composition adds** (C vs E) |
| F | (stretch) C without the verifier: the top recall is accepted | **What verification adds** (C4) |

The simulated reviewer for M8 treats ground truth as the reviewer's answer.

### 14.2 Protocol

1. Blind ground truth, frozen at G2.
2. Tune only on dev. Run test **once per arm** at G3.
3. Every run gets a fresh bank (§8.1), seeded the same way.
4. Arms B, C and D get the same retrieved-context token budget and the same prompt skeleton.
5. Variance: run C and D 3 times on dev and report the range, if the daily quota allows (§14.5); otherwise run them once and say so. The test set runs once.
6. Report counts, not bare percentages, and publish per-case results in `docs/benchmark.md` and `eval/results/`.
7. State the limits: synthetic data, one domain, small sample, estimated minutes.

### 14.3 Honest expectations (write these into `docs/benchmark.md` whatever happens)

- B may match C on plain known cases. If so, say so.
- C should beat E on interaction cases.
- C should beat D on post-override correctness, outdated-lesson use and learning speed.
- If C doesn't beat D, report it and explain why.

### 14.4 Learning curve (`eval/replay.py`)

1. Start from an empty bank, once with `hindsight` and once with `vector`.
2. Replay seeds and test cases in date order, retaining each ground-truth resolution after it's processed (the simulated reviewer).
3. Plot four lines:
   - the rolling share of exception cases handled in one-click mode,
   - review effort (M8),
   - false confidence (M1), which should stay at zero, and
   - maturity per family over time.
4. Compare the two backends. Run the replay once per backend.

### 14.5 Quota budget (run `make budget` before any eval)

We use only free tiers: Groq `openai/gpt-oss-120b` (RPM 30, RPD 1,000, TPM 8,000, TPD 200,000, refilled continuously over a rolling 24 h) as the primary, and `gemini-3.8-flash` then `gemini-3.7-flash` (RPM 5, TPM 250,000, RPD 20 each, reset at midnight Pacific: 12:30 PM IST until early November, 1:30 PM IST after) as fallbacks. The binding limit is **Groq's tokens per day**: on the Gate G1 cases a verifier call averaged about 2,000 tokens at `medium` effort and an extraction about 800, so Groq serves about 100 case verifications a day (`make budget` uses the latest measured averages).

`scripts/estimate_budget.py` reads `config/limits.yaml` (RPM, TPM, RPD and, for Groq, TPD per model, entered by the user from the Groq console and the AI Studio rate-limit page). It multiplies those against measured averages from `llm_calls`:

- requests and tokens (including thinking tokens) per role per case
- retains, recalls and reflects per case (Hindsight Cloud credit)

It prints, per arm and in total:

- projected requests per model
- the number of quota-days the plan needs
- the requests left today

The eval runner refuses to start a run that would go over today's remaining quota unless it's given `--force`, and it can resume a partial run the next day.

**Planning estimate** (replace it with measured numbers as they come in). LLM requests per exception case: arm C about 1 (verifier), arm D about 2 (verifier plus composer), arm E 0, arm F 0, arms A and B 1 each. Extraction is 1 per case, once, because of the cache. Rough totals for the week:

| Item | LLM requests |
|---|---|
| Narratives (60 cases plus 45 seeds) | ~105 |
| Extraction (60 cases, cached) | ~60 |
| Dev runs (C and D ×3, A and B ×1) | ~190 |
| Test runs (all arms once) | ~180 |
| Learning curves (C and D) | ~250 |
| Development, Gate G1 and demo rehearsals | ~400 |
| **Total** | **~1,200** |

`make budget` converts the total to quota-days using measured tokens per request against Groq's TPD, plus the Gemini fallbacks' RPD. Use §14.6 if the plan needs more than about 4 quota-days. Paid tiers and other models are ruled out (CLAUDE.md), so beyond §14.6 the lever is scope.

**Cost controls:**

- the extraction cache is shared by all arms and runs
- one verifier call per case
- arm E reuses C's coverage
- A and B are single calls
- local embeddings for arm D
- thinking set to `low` wherever dev results allow

If the primary model's quota runs out, the rate limiter moves roles to `gemini-3.8-flash`, then `gemini-3.7-flash`. Each Gemini model has its own quota (confirmed in AI Studio in Phase 0; see `api-notes.md`).

### 14.6 Reduced benchmark (if the plan needs more than about 4 quota-days)

- Test 24 cases stratified by class instead of 40, and keep all 8 interaction cases.
- Drop arm F.
- Run dev variance only for C and D, and only once each if needed.
- Run the learning curve only on the test cases, not the seeds.
- Run evals right after the daily reset (about 12:30 PM IST), using the resume support to finish across days.
- State the reduction in `docs/benchmark.md`.

## 15. UI (Next.js)

### 15.1 MVP screens

1. **Case queue.** Incoming requests with a class badge (Normal, Known, Generalized, Composed, Unknown), a maturity badge (tentative or established), and flags (novel combination, predates policy).
2. **Case view.** This is the screen judges remember.
   - At the top is a plain-language summary computed in code, for example "3 of 3 problems have precedents · 2 interaction precedents apply · payment held by safety floor".
   - **Staged reveal:**
     1. The request text appears with extracted signals highlighted.
     2. The failed checks appear.
     3. Each check lights up with its precedent case, verdict and maturity.
     4. The plain union appears.
     5. Interaction changes animate, with struck-through steps and the precedent shown.
     6. Floor additions appear, labelled "Added by safety floor".
     7. The final procedure is shown.

     In demo mode it auto-advances (about 1.5 seconds per stage). Otherwise it renders at once, with a "replay" toggle.
   - Each step has a **"Why this step?"** drawer showing:
     - the cited cases (ledger rows),
     - the recalled memory text (fact or observation),
     - the verifier's verdict and differences,
     - the observation's source-case count, and
     - any policy or override flags.
   - The action buttons change with the review mode: **Approve** in one-click mode, per-step checkboxes plus Confirm in step-by-step mode, and Resolve for unknowns. Edit and Reject are always available.
3. **Resolution form.** For unknowns, it shows what's covered and what isn't. The analyst picks steps from the library and adds a rationale and outcome, then clicks "Save as edge experience". In demo mode it opens pre-filled from `data/demo/fixtures.json`.
4. **Lesson panel.** This replaces the separate memory explorer. It shows the lessons per check and per combination:
   - the current Hindsight observation text,
   - the supporting cases,
   - the status (active, overridden, predates policy), and
   - a **before/after diff** from the snapshots.

   It opens from the case view and from the queue.
5. **Benchmark.** Arms side by side (with C vs D and C vs E called out), the confusion matrix, M1–M11 as counts, the learning curve (C vs D), and the assumptions behind M9 shown next to it.
6. **Demo controls.** Demo clock, seed, reset, "replay 3 weeks", a latency readout, and the LLM quota left (Groq tokens and requests over the last 24 h; Gemini requests left today).

### 15.2 Across all screens

- Glossary tooltips for GSTIN, delegation matrix, line-down, sole-source, PO, lakh, capex and controller.
- Show ₹ in the Indian format (₹4,80,000).
- A "Synthetic data" footer.
- A visible "composing from N cases…" state during reflect.

### 15.3 Stretch

- Boundary map: checks as columns and edge families as chips, with counts over time. Overridden lessons are struck through, and new families (such as U1 once it's resolved) appear as they're learned.
- Memory timeline.

## 16. MVP and stretch

**MVP (must ship):**

- extractor, rules, `MemoryBackend` with both backends, and citations
- the batched verifier, classify, maturity and review mode
- the composer with interactions, conflicts and the floor
- overrides and the policy memo
- observation snapshots
- the case view, resolution form, lesson panel, benchmark page and demo controls
- arms A–E and the learning curve for C and D
- audit export
- the README and the docs in §19

**Stretch, in priority order:**

1. arm F
2. boundary map with the mental model
3. email intake endpoint
4. memory timeline

**Cut order when behind:** arm F, then the boundary map, then the separate generalized class (merged into known with differences), then arm E, then the test set reduced to 30. **Never cut:** arm D, the interaction cases, the override beat, or the risk floor.

## 17. Build phases, gates and lanes

**Lanes (team of 4):**

- P1: engine and backend
- P2: memory and eval
- P3: frontend
- P4: data, ground truth, demo and content. **P4 never edits `api/engine` or `api/memory`.**

With a team of 3, P4's work is split between P2 and P3, but ground truth is still written by someone who doesn't build the engine.

| Day | Phase | Work | Gate |
|---|---|---|---|
| 0 | Phase 0: setup and verification | Repo scaffold; `.env.example`; `llm.py` with rate limiter, cache and logging; `scripts/phase0_spike.py`, which creates a scratch bank, sets missions, directives and disposition, retains 5 seeds in two extraction modes, recalls with tags and source facts, reflects with a schema, and records fixtures; confirms the Gemini and Groq call styles, structured output and thinking/reasoning level; confirms the model IDs with each provider's model listing; measures requests, tokens, thinking tokens, latency, Hindsight calls and consolidation delay; `config/limits.yaml` filled from the numbers the user supplies | **G0:** `docs/api-notes.md` has a verified signature for every Hindsight, Groq and Gemini call used; fixtures recorded; consolidation delay measured; `make budget` shows the week's plan in quota-days, and the full or reduced (§14.6) benchmark is chosen; fallback model confirmed; the answer to whether Hindsight Cloud lets you choose its LLM is recorded |
| 1 | Phase 1: detector | Ledger models plus minimal master data; `rules.py` with tests; extractor with source spans; `HindsightBackend`; `citations.py` with tests; batched verifier; `classify.py` with tests; 15 hand-written borderline cases (5 known, 5 composed including 2 interactions, 5 unknown including 1 U2) | **G1** (`make gate1`): **0 false confidence**; at least 12 of 15 classes correct; 100% of citations resolve to ledger case IDs, including through observations. If it fails, fall back to 4 families (E1, E2, E3, E5) plus I3 and escalate anything uncertain: zero false confidence matters more than coverage |
| 2 | Phase 2: composition and data | Union, reflect, validation (removal rule), conflicts, floor and diff, with tests; maturity and review mode; `import_history.py`; full seeds; `generate_cases.py`; P4 writes ground truth blind | **G2:** ground truth committed and frozen; labeller agreement on dev reported; composer tests green |
| 3 | Phase 3: product and arm D | FastAPI endpoints; case view with staged reveal; resolution form; lesson panel; `VectorBackend`; arms A, B, D and E in `run_arms.py` | Every endpoint works against the demo bank; all arms run on 3 dev cases |
| 4 | Phase 4: memory dynamics and dev eval | Overrides; the policy memo and flags; observation snapshots; `/demo/replay`; `replay.py`; `make budget`; dev runs (3 for C and D); fixes on dev only | Dev results for all arms; learning curves for C and D |
| 5 | Phase 5: test | Test split once per arm; `report.py`; benchmark page; `docs/benchmark.md` | **G3:** C shows 0 false confidence and 0 floor violations on test. If not, report it honestly and don't tune on test |
| 6 | Phase 6: polish | Demo mode, glossary, audit export, README and docs, recorded video; content outlines in `docs/content/` | Full demo run from reset in 3:00 or less |
| 7 | Phase 7: rehearse | Fixes only | Three clean rehearsals; recorded fallback ready |

**Prompts to start each phase in Claude Code:**

- "Read CLAUDE.md and docs/SPEC.md §0–§9, §14.5 and §17. Do Phase 0. My Groq and Gemini free-tier limits are in the message below. Stop at gate G0 and report."
- "Read docs/api-notes.md and SPEC §4, §5, §8 and §9. Do Phase 1. Run make gate1 and report the numbers."
- "Do Phase 2 (SPEC §6, §7 and §13). Don't read or write data/ground_truth; P4 owns it. Stop at G2."
- "Do Phase 3 (SPEC §12, §14.1 and §15). Arm D must reuse pipeline.py with VectorBackend; no forked pipeline."
- "Do Phase 4 (SPEC §8.7–§8.9, §14.4 and §14.5). Run make budget before any eval run."
- "Phase 5: run the test split once per arm with make eval SPLIT=test; don't change engine code after this starts. Generate the report."
- "Phase 6: polish the demo to SPEC §18 and write the README and docs per §19."

## 18. Demo script (3:00)

The demo bank is seeded with everything except E1 and the E4 override, so the first exception and the override both happen live. Run `make reset && make seed` before every rehearsal.

| Time | Beat | Claim | What judges see |
|---|---|---|---|
| 0:00–0:20 | Hook | — | "Ananya is three weeks in. Ravi, who knows how every exception gets handled, is on leave." A ₹4,80,000 request lands: line 3 is down, the cost centre is 6% over budget, the approver is on leave, and the vendor changed bank details on 12 Sep. The plain rule engine shows three red checks and no guidance. "Let's see how EdgeMemory learns first." |
| 0:20–0:40 | First exception | C4 → C3 | A ₹60,000 order whose vendor certificate expired 6 days ago. **Unknown**: no precedent. Ananya resolves it (pre-filled form) and clicks "Save as edge experience". The lesson panel shows the new lesson. |
| 0:40–1:05 | Tentative, then established | C3 | Demo clock +1 week. A different vendor has the same problem: **Known · tentative (1 precedent)**, so she confirms step by step. Click "replay 3 weeks" to resolve two more. The lesson panel shows the **Hindsight observation now consolidated from 3 cases**, with a before/after diff. The next case is **Known · established**: one click. |
| 1:05–1:40 | Composed with interactions | C1, C2 | Back to the ₹4.8L case. Each check lights up with its precedent. The plain union holds the PO, so line 3 stays down; that step is shown struck through. Two interaction precedents apply. **I1:** delegates don't approve overruns, so it routes to the next-level approver. **I3:** a PO is not a payment, so the PO is released while payment is held until the bank callback. The safety floor badge reads "payment held, callback required". "No rule author wrote this. Ravi's team did, one case at a time." |
| 1:40–2:05 | Override revises a lesson | C3 | A split-shipment case for a vendor with a past duplicate-invoice incident. The recommendation links it to the master PO. The reviewer rejects it and writes why. The lesson panel shows the **observation text change** and the old lesson marked overridden in this context. A similar case is re-run and follows the revised lesson. |
| 2:05–2:20 | Honest limit | C4 | The email thread reveals that the vendor's owner is the requester's brother-in-law. **Unknown.** The screen shows what's covered and what isn't; the floor adds `DECLARE_CONFLICT_OF_INTEREST`, and the case escalates. |
| 2:20–2:50 | Proof | All | Benchmark page, with real numbers only: arms B, C and D side by side, and C vs E on interaction cases; false confidence "0 of N"; review effort; minutes (assumptions visible); the learning curve for C vs D. |
| 2:50–3:00 | Close | — | The pitch line. "It recommends; your people decide; it remembers what they decided." |

**60-second cut:** the hook (10 seconds), the composed-with-interactions beat (30 seconds) and the override beat (20 seconds).

**Rehearsal:**

- Show the "composing from N cases…" state during reflect.
- Keep the recorded video ready in case the network or an API fails.
- Warm up the demo bank with one recall before going on stage.

## 19. README, docs and submission

**README sections:**

1. The problem in 3 sentences.
2. The persona.
3. The 60-second GIF.
4. How it works: the architecture diagram plus the four claims.
5. How Hindsight memory is used: real retain, recall and reflect snippets from the code, what each memory kind is, and why interactions have their own tags.
6. Benchmark results: a table with counts, a link to per-case results, and the limits.
7. Setup: `make setup seed api web`.
8. Adoption.
9. The synthetic-data notice.

**`docs/memory-design.md`:** §8, expanded with real examples from the demo bank, including before/after observation snapshots.

**`docs/benchmark.md`:** the §14 protocol, results, honest expectations and limits.

**`docs/adoption.md`:**

- **Integration point:** requests arrive by email to a monitored approvals inbox, or as a CSV or webhook export from whatever system holds the approval queue. Recommendations go back as an approval-note attachment plus the audit CSV.
- **Cold start:** export the last 12 months of exception tickets or approval emails to the `import_history.py` CSV format.
- **Buyer and pricing hypothesis:** §1.5, labelled as a hypothesis.
- **Data and model:** the hackathon build runs on the Groq and Gemini free tiers with synthetic data only. Production would run Groq with Zero Data Retention enabled, or the customer's own model provider. `llm.py` is the only file that changes.
- **Rollout:** start in shadow mode, where EdgeMemory recommends and the analysts compare; move to step-by-step review after 2 weeks.
- **Where else this works:** accounts payable exceptions, IT change approvals and insurance claims. The mechanism is per-check coverage plus interaction-aware composition.
- **Competitive framing:** procurement suites automate the standard path and some offer AI assistants. EdgeMemory is complementary because it learns this team's own exception decisions. **Don't state any named competitor's features unless verified from their own docs.**

**`docs/content/`:** outlines only for each member's article, social post and video, per the official content guide. Each person writes their own.

**Submission checklist:**

- GitHub repo with clean, documented code
- demo video (3:00, with the 60-second core first)
- live demo with a recorded fallback
- the Hindsight explanation (`docs/memory-design.md` plus one slide)
- content deliverables from every member
- Hindsight Cloud credit applied (promo code MEMHACK99, in billing after sign-up)
- join the Hindsight Community Slack

## 20. Risks

| Risk | Early sign | Mitigation |
|---|---|---|
| Unknown treated as known | G1 failures; adversarial dev cases passing | Batched verifier with a shared guide; tag match; arm F; fall back to fewer families |
| Free LLM quota runs out (Groq TPD first) | 429s; `make budget` shows more than 4 quota-days | One verifier call per case; short verifier reasons; `low` effort where G1 allows; cache; E reuses C; Gemini fallbacks' own quotas; resume as Groq's window refills; §14.6; then scope cuts |
| Model ID or SDK call style changes | 404 or a TypeError from the SDK | Confirmed in G0; config-driven; call style recorded in `api-notes.md` |
| Structured output breaks | Parse errors; enum casing mismatches | Simple all-required schemas; normalise case in code; Pydantic validation; retry, then fallback |
| Safety filter blocks a fraud-related prompt | Empty response with a safety finish reason | Treated as a failure: retry, fallback, then escalate; logged |
| Real data sent to the free tier | — | Synthetic data only (CLAUDE.md data rule) |
| Hindsight's LLM differs from ours | Confirmed in Phase 0: Cloud's model can't be set or seen | Stated in `docs/benchmark.md`; self-hosting Hindsight on one of our models only if the quota allows, and after asking |
| Hindsight credit burn | Cost per retain or reflect higher than planned | Measured in G0; fresh banks only when needed; a single replay per backend |
| Consolidation slow or invisible | Snapshot unchanged after retain | Measured delay; polling with a visible state; ledger snapshots as history |
| Observation citations don't resolve | Case IDs missing in the case view | `citations.py` through source facts; tested on fixtures in G1 |
| Reflect slow or failing live | Over 10 seconds, or 500 errors | Budget low; visible state; union fallback; recorded video |
| Composer invents steps or removals | Codes outside the library; removals without citations | Validation (§7.1); restore and flag |
| C doesn't beat D | Dev results | Report it honestly; find where each wins; no tuning on test |
| Benchmark looks rigged | The same people wrote the cases and the engine | Blind ground truth; second labeller; held-out I2, U1 and U2; per-case results |
| Scope creep | UI unfinished on day 5 | Cut order (§16) |

## Appendix A: review gaps and where they're closed

| Gap from the review | Closed in |
|---|---|
| Too close to the PDF's Accounts Payable Agent idea | §2 (C2 and C3 as the lead claims), §7.2, §18 composed and override beats |
| Composition was just union plus priority | §7.1 (union → interaction precedent → validated removals), §6.2 precedent resolution, §7.2 families, arm E |
| The demo only showed what a vector DB can do | §8.9 consolidation visible, §18 tentative → established and override beats, lesson panel (§15) |
| The benchmark didn't isolate Hindsight | Arm D (§14.1), a shared `pipeline.py`, the `MemoryBackend` protocol |
| Citations vs `prefer_observations` | §8.6 citations through `source_fact_ids`; G1 requires 100% of citations to resolve |
| Learning from a single case | §5.4 maturity, §5.5 review mode, §18 beat 3 |
| Default extraction may drop details; there are three missions | §8.2 missions, §8.3 extraction-mode test in Phase 0 |
| LLM rate limits too tight (Gemini free tier is 20 RPD per model; Groq's TPD binds) | Primary moved to Groq `openai/gpt-oss-120b` with Gemini fallbacks (Phase 0); CLAUDE.md quota rules, one verifier call per case, E reuses C, §14.5 quota-days, §14.6, G0 |
| Fallback model not verified | CLAUDE.md fallback order (`gemini-3.8-flash`, then `gemini-3.7-flash`), both confirmed in G0 with `client.models.list()` and a live call |
| Model-mismatch confound in C vs D | §8 (which LLM Hindsight uses), §14.1 note, G0 |
| Hindsight credit unmeasured | Phase 0 spike, §14.5, §20 |
| Scope too large | §15 (memory explorer folded into the lesson panel), §16 cut order, §17 lanes |
| No rule for aggregating verdicts; known vs generalized is subjective | §5.1 shared guide, §5.2 aggregation, §13 second labeller |
| The demo opened on a Normal case | §18 hook opens on the pain |
| The case view was too crowded | §15 staged reveal plus a plain-language summary |
| Jargon | §15 glossary tooltips |
| A live form fill is fragile | §15 pre-filled demo fixtures |
| No "why?" | §15 "Why this step?" drawer, `/memory/trace` |
| No time or money metric | M9 with visible assumptions (§10) |
| "Unsafe auto-resolutions" sounded automatic | Renamed M1 false confidence (§10) |
| Thin adoption path | §19 `docs/adoption.md`, `import_history.py` as the cold start, audit export |
| Competitor framing | §19, without unverified claims |
| Internal notes in the doc | CLAUDE.md writing rules; the README has none |
| `include_facts` name | CLAUDE.md API notes; §8.5 |
| `query_timestamp` isn't a filter | CLAUDE.md API notes; §8.1 fresh banks per run for isolation |
