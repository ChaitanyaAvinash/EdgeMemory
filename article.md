# A PO Is Not a Payment: Building a Procurement Copilot That Learns Where the Rules Break

A purchase request for ₹4,80,000 comes in. Production line 3 is down, the cost centre is 6% over budget, the approver is on leave, and the vendor changed its bank details twelve days ago. A rule engine shows three red checks and nothing more. The senior analyst who would know what to do is on leave.

I built EdgeMemory for that situation. It's an exception copilot for procurement operations. A deterministic rule engine decides which checks a purchase request failed. EdgeMemory then finds how people resolved those failures before, composes a procedure, and cites the case behind every step. When there's no precedent it says so and escalates. Each human decision goes back into memory. It only recommends, and a person makes every decision. Nothing in the codebase can release a payment.

This post covers one lesson that shaped most of the architecture. **When several checks fail together, the right procedure is often not the union of the single-check fixes.** Getting that right took a memory layer that learns combinations as their own lessons, and a code layer that decides what the model may take away.

## How it fits together

The pipeline for a single request looks like this:

```
request ─► extractor (LLM) ─► rule engine (code): which checks failed?
               ▼
  per failed check: tagged recall    +   per combination: tagged recall
               ▼
  verifier (one LLM call per case) ─► code guards (can only lower a verdict)
               ▼
  classify (code): known · generalized · composed · unknown
               ▼
  union of lessons ─► reflect ─► code validation ─► conflicts ─► risk floor
               ▼
  human decides ─► retained into memory ─► lessons consolidate
```

The backend is FastAPI with SQLite for the ledger. The frontend is Next.js. All LLM calls go through one module, `llm.py`, which handles JSON-schema output, Pydantic validation, retries and a fallback model. Memory is [Hindsight](https://github.com/vectorize-io/hindsight), and the rest of the system reaches it only through a `MemoryBackend` protocol. That protocol has two implementations, `HindsightBackend` and a plain `VectorBackend` built on local sentence-transformer embeddings. That split let me measure what Hindsight contributes against an ordinary vector store running the same pipeline.

One rule runs through the whole codebase: **the LLM proposes, code verifies, a human decides, and memory records what the human decided.** Every count on screen is computed in Python from SQLite, and the model never states a number the UI displays.

## The union problem

A single failed check is easy. If the vendor's bank details changed, you call the vendor on a number you already have on file, and you hold the payment until that callback happens. If the budget is overrun and the line is down, you attach the line-down evidence, get the controller's sign-off and expedite the PO. Each of those is a lesson one analyst learned once and repeated many times.

Now take a request that fails both checks. The naive composition is the union: every step from the bank lesson plus every step from the budget lesson. That union includes `HOLD_PO`, because an unverified bank change feels like a reason to freeze everything. But holding the PO keeps line 3 down. What experienced analysts actually do is release the PO and hold the *payment* until the callback. A PO commits you to buy; it doesn't move money. The risk sits in the payment.

No rule author wrote that down. It exists in the resolutions of three earlier cases, and my job was to make the system learn it from them rather than hard-code it.

## Designing memory around tags

The first thing I got wrong was treating memory as one pool. If combination lessons and single-check lessons consolidate together, the bank-change lesson turns into a blend of "hold everything" and "release the PO", and neither one is usable.

Hindsight stores raw facts and also consolidates them into **observations**, which are durable lessons it keeps revising as new evidence arrives. The [Hindsight docs](https://hindsight.vectorize.io/) describe `observation_scopes`. With `per_tag`, each tag gets its own consolidated lessons. Once I saw that option, the tag scheme became the memory schema:

```python
def tags_for(rec: dict[str, Any]) -> list[str]:
    """Interactions get only `interaction` + `combo:`, so they don't pollute single-check lessons.
    Overrides carry the overridden lesson's tags."""
    if rec["kind"] == "interaction":
        return ["interaction", "combo:" + "+".join(sorted(rec["checks"]))]
    if rec["kind"] == "policy_change":
        return [rec["tag"], "policy"]
    return [tag_for(c) for c in rec["checks"]]
```

A single-check resolution is tagged `step:bank`. A multi-check resolution whose steps differ from the plain union is tagged `combo:bank+budget` and nothing else. My original design was to recall interactions under the plain `interaction` tag and filter them by metadata afterwards. When I ran that against the real API, the observation built under `interaction` carried only that one tag, so every combination family merged into a single lesson with no combo left to filter on. The fix was to recall each subset of the failed checks by its own `combo:` tag. I only found this by recording real responses as fixtures and reading them, and that turned out to be a pattern for the rest of the project.

Recall is one tagged call per failed check, using `any_strict` so untagged memories stay out. The default `any` mode includes untagged memories, which is exactly how cross-contamination gets in:

```python
resp = await self.client.arecall(
    self.bank_id, q,
    types=rc["types"],                 # world, experience, observation
    prefer_observations=True,
    include_source_facts=True,
    max_source_facts_tokens=-1,
    budget=rc["budget"],
    max_tokens=rc["max_tokens"],
    tags=tags,
    tags_match="any_strict",
    query_timestamp=query_timestamp.isoformat() if query_timestamp else None,
)
```

`include_source_facts` matters here. An observation merges facts from several cases, so the lesson's text isn't evidence by itself. The citation code follows each observation's `source_fact_ids` back to the underlying facts. From there it reads the `document_id` (our case ID) and then checks that the case exists in the ledger. If a source fact is missing, the citation is marked unresolved. It is never guessed.

## Letting the model remove things, carefully

Composition starts from the union. I pass the union, the verified single-check precedents and any verified interaction precedents to Hindsight's `reflect`, together with a JSON schema. The bank also has directives that always apply: cite a case for every step, never recommend releasing a payment, say explicitly when nothing applies. Reflect returns a list of steps and a separate list of steps it removed from the union.

I don't trust that output directly. The validator in `composer.py` is where the interaction rule is actually enforced:

```python
for us in u:
    if us.code in kept_codes:
        continue
    note = removal_notes.get(us.code)
    guarded = lib[us.code] in GUARDED_CLASSES          # risk_control, compliance
    cites = [c for c in (note.cited_case_ids if note else []) if c in precedent_cases]
    if guarded and not cites:
        steps.append(Step(us.code,
            "restored: removing a risk-control or compliance step needs a verified "
            "interaction precedent", us.cited_case_ids, "union"))
        flags.append(f"restored_removed_step:{us.code}")
```

The model can drop `HOLD_PO` only when the removal cites a case that the verifier accepted as an interaction precedent for this combination of failed checks. Any other removal gets restored and shown on screen as a flag. Every step also has to cite a case that was verified for this request. A step added beyond the union has to cite a case whose approved steps actually included it.

After validation comes the risk floor, which is plain deterministic code:

```python
def floor_required(ctx: FloorContext) -> dict[str, str]:
    req: dict[str, str] = {}
    if ctx.bank_change:
        req |= {"VERIFY_BANK_CALLBACK": "F1", "HOLD_PAYMENT": "F1"}
    if ctx.related_party:
        req |= {"DECLARE_CONFLICT_OF_INTEREST": "F3"}
    if ctx.gst_cancelled:
        req |= {"VERIFY_GST_STATUS": "F4", "HOLD_PO": "F4"}
    return req
```

The floor runs after composition in every path, including the fallback when reflect fails. Learned lessons can add steps on top of the floor, but they can never take a floor step away. Steps the floor adds are labelled as floor steps, never as learned ones.

The result for the ₹4.8L request: `HOLD_PO` is removed, citing three `combo:bank+budget` precedents. The on-leave approver's delegate is replaced by the next-level approver, because a separate `combo:approver+budget` lesson says delegates don't approve overruns. The payment stays held until the bank callback. The UI shows the plain union with the removed step struck through, and every change carries a cited case.

## Lessons that mature, and one that went wrong

This is where Hindsight did work a vector store can't. Observations are revised in place, and `get_observation_history` returns every earlier version. The first expired-certificate case had no precedent, so it was classed unknown and escalated. An analyst resolved it. Hindsight then consolidated the resolution into a lesson citing that one case, and revised it as more cases came in: two cases, then four, then five, with the condition narrowing to vendors with clean delivery records and completed renewal audits. Consolidation after a retain settled in about four seconds in my measurements, so this is visible live.

The code turns that support count into review effort. A lesson backed by one case is **tentative**, and the analyst approves it step by step. At two or more cases it becomes **established**, and review is one click. A policy memo is retained as a dated memory, and any coverage that cites a case from before the policy changed is flagged for step-by-step review.

Overrides were the painful part. A reviewer rejected a split-shipment recommendation because the vendor had a history of duplicate invoices. Hindsight correctly formed a separate, context-specific lesson: reject and escalate to audit for that kind of vendor. But in some banks, consolidation folded the override into the standard lesson's observation. My verifier judged that merged memory as a whole and correctly said the standard lesson didn't apply. The override's own answer was lost with it, so the case was escalated. That was safe, but it was wrong, and it's also where a plain RAG baseline beat us, because RAG just reads the override narrative. The fix was to split every recalled per-check memory that mixes override cases with standard ones into two candidates, and to let the verifier judge the override in its own context.

## What the measurements say

Because both backends sit behind one interface, I could run the identical pipeline on Hindsight and on a local vector store over the same labelled, held-out evaluation set of 24 cases, with ground truth frozen before scoring. The results are mixed, and I'll report them that way:

- **False confidence on unknowns:** 0 of 5 for both memory backends. A single-prompt baseline with no memory got 3 of 5 wrong, and plain RAG got 1 of 5. The zero comes from the pipeline (per-check coverage, guards that can only lower a verdict), not from the memory store.
- **Outdated lessons used after a policy change:** 0 of 3 with Hindsight, 2 of 3 with the vector store.
- **Learning speed:** replaying the cases in date order with each resolution retained, Hindsight reached one-click review on 8 of 22 exception cases. The vector store reached 4 of 22.
- **After an override:** 0 of 3 correct for both, before the fix above. Plain RAG got 3 of 3.

The sample is small and the minutes-saved figures are estimates. It's still the table I'd want to read before believing anyone's memory layer.

## What I'd tell someone building this

1. **Your tags are your memory schema.** Decide the consolidation scopes before retaining anything. In Hindsight, the tag a fact carries decides which lesson it can turn into. Tag carelessly and your lessons blend together.
2. **Never threshold on recall scores.** Relevance scores are relative within a single query. I let recall surface candidates, then an LLM verifier plus code guards decide what applies, and the guards can only make a verdict more conservative.
3. **Give the model permission to remove, and make removal expensive.** The interesting procedures differ from the union by what they leave out. Require every removal of a guarded step to cite a verified precedent for the exact combination, and restore it visibly if it doesn't.
4. **An observation is a summary, not evidence.** Resolve every citation back to source facts and ledger records. If a citation can't be resolved, drop the step and show the flag.
5. **Put memory behind an interface and build the boring baseline.** The vector-store arm showed me what [agent memory with consolidation and temporal awareness](https://vectorize.io/what-is-agent-memory) actually bought, which was dated lessons and faster maturity. It also showed me where it didn't help. Without that comparison I'd have been guessing.

Normal automation encodes the happy path. The expensive knowledge in an operations team is how people handled the cases where it broke, and it mostly sits in one senior person's head. Getting it out of there needed a memory that keeps lessons separate, revises them and dates them. It also needed code that checks every step before a human sees it.
