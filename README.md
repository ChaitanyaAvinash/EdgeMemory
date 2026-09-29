# EdgeMemory

**Normal automation encodes the happy path. EdgeMemory learns where the happy path breaks, and how your
people fixed it.**

> **Synthetic data.** Kaveri Precision Components, its people, vendors and cases are fictional. Every request,
> precedent and number in this repository is synthetic. EdgeMemory recommends; a human always decides. It
> never releases a payment.

## The problem

A purchase request is meant to pass budget, vendor, approver, duplicate, bank-detail and quote checks. When
it breaks one of them, a senior analyst resolves it from experience that isn't written in any policy. When
that analyst is away, new analysts either escalate everything or improvise, and a generic AI assistant
answers confidently with nothing behind it.

## Who it's for

Ananya Rao is a procurement operations analyst three weeks into the job at Kaveri Precision Components, a
fictional precision-parts maker in Hyderabad. Ravi Menon, who has handled exceptions for nine years, is on
leave. EdgeMemory gives Ananya Ravi's past resolutions, cited, and says plainly when there is none.

## Demo

A 60-second walkthrough will be recorded from the scripted demo (`data/demo/fixtures.json`, run from **Demo
controls**).

## How it works

```
request ──► extractor (LLM) ──► rule engine (code): which of the six checks failed?
                                   │ none ──► normal: standard approval
                                   ▼
            per failed check: tagged recall ──┐     several checks: recall by combination
                                              ▼
                     verifier (one LLM call per case) ──► code guards (can only lower a verdict)
                                              ▼
            classify (code): known · generalized · composed · unknown, and maturity
                                              ▼
            compose: plain union ──► Hindsight reflect ──► code validation ──► conflicts ──► safety floor
                                              ▼
                      human decides ──► retained into Hindsight memory ──► lessons consolidate
```

Four claims, each built into the pipeline:

1. **Per-check coverage.** Each failed check is matched to precedents separately, so known, composed and
   unknown cases all follow from one rule.
2. **Interaction-aware composition.** When several checks fail together, the right procedure is often not
   the union of the single-check lessons. For example, "a PO is not a payment": release the PO but hold the
   payment until the bank callback. EdgeMemory learns these combinations from human resolutions; none is
   hard-coded.
3. **Lessons mature and get revised.** A lesson backed by one case is tentative and needs step-by-step
   review. Confirmations make it established, and it becomes one-click. A reviewer's override revises it in
   context. A policy change dates it.
4. **Honest unknowns.** A failed check without a verified precedent is escalated, together with what is known
   and what isn't.

The rules that keep it safe are in code, not in prompts:

- a **risk floor** (for example, a changed bank account always means a callback and a payment hold);
- **only an interaction precedent may remove** a risk-control or compliance step;
- **every step must cite** a case that exists in the ledger and was verified for this request.

## How Hindsight memory is used

All memory access goes through `api/memory/backend.py`. `HindsightBackend` is the Hindsight implementation;
arm D of the benchmark swaps in a plain vector store through the same interface.

- **Retain** (`api/memory/hindsight_backend.py`): every resolution becomes one memory in a fixed template
  that keeps step codes literal. It is tagged `step:<check>` for single-check lessons, or `interaction` plus
  `combo:<checks>` for combinations, so combination lessons don't pollute single-check ones. Observations
  are scoped per tag.

  ```python
  await self.client.aretain_batch(self.bank_id, [{
      "content": item.content, "timestamp": item.timestamp, "document_id": item.document_id,
      "metadata": {...}, "tags": item.tags, "observation_scopes": "per_tag", "resolve_entities": False}])
  ```

- **Recall**: one tagged recall per failed check, plus a recall over every combination tag when several
  checks fail. Consolidated observations come back with their source facts, and code maps those to case
  IDs. Scores are never thresholded; a separate verifier decides what applies.

  ```python
  await self.client.arecall(self.bank_id, query, types=["world", "experience", "observation"],
      prefer_observations=True, include_source_facts=True, max_source_facts_tokens=-1,
      tags=[f"step:{check}"], tags_match="any_strict", query_timestamp=...)
  ```

- **Reflect** composes the procedure from the plain combination and the verified interaction precedents,
  under a JSON schema. Code then validates every step, citation and removal.

  ```python
  await self.client.areflect(self.bank_id, prompt, budget="mid", response_schema=schema,
      tags=tags, tags_match="any", include_facts=True)
  ```

- **Consolidation and history** make learning visible. After each human decision, EdgeMemory waits until
  the tag's observation cites the new case, snapshots it, and the lesson panel shows the before/after diff
  from Hindsight's observation history.

The memory design, with real before/after lesson text from the demo, is in
[docs/memory-design.md](docs/memory-design.md).

## Results

**Test split: 24 synthetic cases, ground truth frozen before scoring, each arm run once.** Full table,
per-case results and caveats: [docs/benchmark.md](docs/benchmark.md).

| | A: no memory | B: plain RAG | **C: EdgeMemory** | D: same pipeline, vector store |
|---|---|---|---|---|
| False confidence on unknowns | 3 of 5 | 1 of 5 | **0 of 5** | 0 of 5 |
| Required safety steps missing | 7 of 9 | 4 of 9 | **0 of 9** | 0 of 9 |
| Classes correct | 11 of 24 | 15 of 24 | **21 of 24** | 21 of 24 |
| Interaction procedures exactly right | 0 of 8 | 0 of 8 | **3 of 8** | 3 of 8 |
| Outdated pre-July lesson used | 0 of 3 | 0 of 3 | **0 of 3** | 2 of 3 |
| Correct after a reviewer override | 1 of 3 | 3 of 3 | **0 of 3** | 0 of 3 |

- **Learning curve** (test cases replayed in date order, each human decision remembered): with Hindsight,
  8 of 22 exception cases were one-click reviews. With the vector store it was 4 of 22. False confidence was 0
  on both.
- **Where EdgeMemory is behind:**
  - Plain RAG (B) handles cases that follow a reviewer override better: 3 of 3 against 0 of 3. EdgeMemory
    escalated two of them and gave the third an empty procedure, a defect described in the benchmark doc. It has since
    been fixed and checked on dev and in the demo; the test numbers are from before the fix.
  - B also has a higher procedure F1 (0.843 against 0.798), but it gave an unknown case a confident answer and
    missed required safety steps in 4 of 9 cases.

The development gate **G1**: 15 hand-written borderline cases, labelled by the engine
builder rather than blind, so it is not a benchmark result. The latest run
(`eval/results/gate1-20260928T132132.json`):

- **0 of 15** false confidence;
- **13 of 15** classes correct;
- **52 of 52** citations resolved to ledger cases.

## Setup

Python 3.11+ and Node 20+. The keys go in `.env` (see `.env.example`): Groq, Gemini and Hindsight Cloud, all on
free tiers or promotional credit.

```bash
make setup        # Python virtualenv and dependencies
cd web && npm install && cd ..
make api          # FastAPI on :8000
make web          # Next.js on :3000
make reset seed   # fresh demo ledger and memory bank (about 3 minutes)
make test         # unit tests (offline)
make gate1        # development gate G1
make budget       # LLM quota plan
```

The LLM is `openai/gpt-oss-120b` on Groq's free tier, with `gemini-3.8-flash` and then `gemini-3.7-flash` as
fallbacks. Hindsight Cloud runs its own model for retain, consolidation and reflect.

## Adoption

See [docs/adoption.md](docs/adoption.md): how it plugs into an approvals inbox, how to start from a
customer's history, and how it would run on real data.

## Limits

- The data is synthetic and covers one domain.
- The samples are small: 20 dev and 24 test cases.
- The test ground truth was written by one AI labeller (a separate session of the same model family that
  built the system) and not checked by a person.
- Time savings are estimates from stated assumptions (`config/assumptions.yaml`).
- The hackathon build uses free-tier LLMs, and only synthetic data may go through them.
