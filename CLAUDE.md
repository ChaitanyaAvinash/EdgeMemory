# EdgeMemory: project rules for Claude Code

Read this file at the start of every session. The full design is in `docs/SPEC.md`. Before writing code for a phase, read that phase's section and every section it references. Verified API details go in `docs/api-notes.md`, which you create in Phase 0; after that it overrides anything in this file or the spec that it contradicts.

## What we're building

EdgeMemory is an exception copilot for a procurement operations analyst at Kaveri Precision Components Pvt Ltd, a fictional mid-size manufacturer in Hyderabad. A rule engine finds which purchase-request checks failed. EdgeMemory then:

- finds how people resolved those failures before,
- composes a procedure, including how lessons change when several checks fail together,
- says plainly when no precedent exists, and
- learns from every human decision through Hindsight memory.

It recommends; a human always decides.

It's being built for HackwithHyderabad 3.0, which requires Hindsight by Vectorize. The judging weights are Innovation 30, Hindsight memory 25, Technical 20, UX 15 and Real-world impact 10.

Pitch line: "Normal automation encodes the happy path. EdgeMemory learns where the happy path breaks, and how your people fixed it."

## The four claims (every feature must serve at least one)

- **C1 Per-check coverage.** Coverage is tested once per failed check, not once per case. Known, generalized, composed and unknown cases all follow from that.
- **C2 Interaction-aware composition.** When several checks fail, the right procedure is often *not* the union of the single-check lessons. EdgeMemory learns those interactions from human resolutions and never hard-codes them.
- **C3 Lessons mature and get revised.** A lesson backed by one case is tentative. It becomes established once several cases confirm it. A reviewer override revises it, and a policy change dates it. These are the Hindsight-specific behaviours (observations, consolidation, temporal awareness), and both the demo and the benchmark must show them.
- **C4 Honest unknowns.** Any failed check without a verified precedent is escalated, together with what is known and what isn't. The target is zero false confidence.

If a task doesn't serve C1–C4, the UX, or the submission requirements, don't build it.

## Non-negotiable rules

1. **The LLM proposes, code verifies, a human decides, Hindsight remembers what the human decided.**
2. **Nothing releases money.** No step code releases a payment. The system never marks a PO as released; it only recommends steps for a human to approve.
3. **Numbers come from code.** Every count, amount, percentage and metric shown anywhere is computed from SQLite in Python. The LLM never computes or states numbers that end up in the UI or the README.
4. **The risk floor can't be overridden.** `engine/precedence.py` enforces floor invariants (for example, a recent or claimed bank change means `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT` must be present). Learned lessons may refine a procedure above the floor, never below it. The floor is applied after composition in every pipeline arm.
5. **Only an interaction precedent may remove a step.** Composition starts from the union of the verified single-check lessons. Reflect may remove a risk-control or compliance step from that union only when it cites a verified interaction precedent for the same combination of failed checks. Otherwise code puts the step back and flags it.
6. **Every citation must resolve.** Each step must cite at least one case ID that exists in the ledger and was a verified match for this request. Code drops any step that fails this and flags it on screen.
7. **Never threshold on recall scores.** Hindsight scores are relative within one query. Coverage is decided by the verifier plus a tag match.
8. **All memory access goes through `api/memory/backend.py`.** It defines the `MemoryBackend` protocol, implemented by `HindsightBackend` and `VectorBackend`. No other module imports the Hindsight client. Arm D depends on this.
9. **All LLM calls go through `api/llm.py`.** That means a JSON schema, Pydantic validation, 2 retries, then the fallback model, all under the rate limiter and the daily request counter. Log the raw output, token counts (including thinking tokens), finish reason, latency, model and cache hits to the `llm_calls` table.
10. **Ground truth is off-limits to the engine.** Nothing under `api/engine/` or `api/memory/` may read `data/ground_truth/`. Tune only on the dev split. The test split runs once per arm, at Gate G3.
11. **Fail visibly.** If recall or reflect errors, retry once, then show "Memory unavailable, escalating to a human". Never show a confident procedure you couldn't ground.
12. **Label synthetic data as synthetic** in the UI footer, the README and the demo video.

## Hindsight: verify, don't guess

In Phase 0, install `hindsight-client` (`from hindsight_client import Hindsight`) and inspect the real method signatures with `inspect.signature` and the package source. Write each verified call into `docs/api-notes.md`. Things already confirmed from the docs (v0.10, read 28 Sep 2026):

- **retain** accepts `content` (the only required field), `context`, `timestamp` (ISO 8601, or `"unset"`), `metadata` (string key-value pairs), `document_id`, `update_mode` (`replace` by default, or `append`), `entities`, `resolve_entities`, `tags`, `observation_scopes`, `retain_async` and `operation_id`.
  - Extraction modes are `concise` (the default), `verbose`, `verbatim` and `chunks`. Find the parameter name.
  - **The allowed values of `observation_scopes` are NOT confirmed.** Find them in the client or API reference before using `per_tag`.
- **recall** accepts `query` (**maximum 500 tokens**), `types` (`world`, `experience`, `observation`), `prefer_observations`, `budget` (`low`, `mid` by default, `high`), `max_tokens`, `query_timestamp`, `temporal_window`, `include` (`chunks`, `source_facts`, `entities`), `tags`, `tags_match`, `tag_groups`, `trace` and `min_scores`.
  - `tags_match` is one of `any` (the default; it **includes untagged** memories), `any_strict`, `all`, `all_strict` or `exact`.
  - `query_timestamp` is an **anchor for relative time expressions, not a filter**. It does not hide memories dated later.
  - Result fields: `id`, `text`, `type`, `context`, `metadata`, `tags`, `entities`, `occurred_start`, `occurred_end`, `mentioned_at`, `document_id`, `chunk_id`, `scores`, and `source_fact_ids` (observations only).
  - **An observation merges facts from several cases, so get its case IDs from `source_fact_ids`, using `include.source_facts`.** Write this as `memory.citations(result) -> list[case_id]` and unit-test it against recorded fixtures.
- **reflect** accepts `query`, `budget` (`low` by default), `max_tokens`, `response_schema`, `tags`, `tags_match`, `tag_groups`, `include` (`facts`, `tool_calls`), `reflect_search_observations_max_tokens` and `reflect_search_observations_include_entities`.
  - Facts are requested through `include`; there is no `include_facts` argument. Confirm the client's spelling.
  - The response contains `text`, `structured_output`, `structured_output_error`, `based_on`, `usage` and `trace`.
  - Reflect returns HTTP 500 when retrieval, tool calling or the provider fails. An empty result is not a failure.
- **Bank configuration** has three separate missions (`retain_mission`, `observations_mission`, `reflect_mission`) and three dispositions (`disposition_skepticism`, `disposition_literalism`, `disposition_empathy`, each 1–5). Directives are created through the API and can be tagged; untagged directives always apply. **Missions, dispositions and directives affect reflect only, never recall.** `enable_auto_consolidation` exists; how long consolidation takes isn't documented, so measure it.
- **Mental models** use `create_mental_model(name, source_query, id?, tags?, max_tokens?, trigger?)` and `refresh_mental_model()`. The trigger accepts `refresh_after_consolidation`, `refresh_cron` and `mode`. They're a stretch goal only.
- **Which LLM Hindsight uses.** Retain, consolidation and reflect run on Hindsight's own LLM, not on our `llm.py`.
  - **Default: Hindsight Cloud.** Its LLM runs on the $50 promo credit, so none of Hindsight's calls touch the Groq or Gemini quotas.
  - Verified in Phase 0: Cloud doesn't let you choose or see that model. `docs/benchmark.md` must say that arm C composes with Hindsight Cloud's undisclosed model while arm D composes with `openai/gpt-oss-120b`.
  - Self-hosting with `HINDSIGHT_API_LLM_PROVIDER=gemini`, `HINDSIGHT_API_LLM_API_KEY` and `HINDSIGHT_API_LLM_MODEL=gemini-3.8-flash` (per-operation overrides are `HINDSIGHT_API_RETAIN_LLM_*`, `HINDSIGHT_API_REFLECT_LLM_*` and `HINDSIGHT_API_CONSOLIDATION_LLM_*`) would make that comparison exact. But it puts every Hindsight call on the same free quota and needs Docker plus PostgreSQL. **Ask before switching.**

## LLM: Groq gpt-oss-120b, with Gemini fallbacks, free tiers only

**Only these three models, and only on their free tiers.** Don't add another model or provider, don't use a paid tier, and don't suggest either. If the quota runs short, cut scope (see "Quota rules").

| Order | Model | Provider | Key (`.env`) | Free-tier limits (`config/limits.yaml`) |
|---|---|---|---|---|
| Primary (every role) | `openai/gpt-oss-120b` | Groq, called over `httpx` | `GROQ_API_KEY` | RPM 30, RPD 1,000, TPM 8,000, **TPD 200,000**, refilled continuously (rolling 24 h) |
| Fallback 1 | `gemini-3.8-flash` | Gemini, `google-genai` | `GEMINI_API_KEY` | RPM 5, TPM 250,000, **RPD 20**, reset at midnight Pacific |
| Fallback 2 | `gemini-3.7-flash` | Gemini, `google-genai` | `GEMINI_API_KEY` | RPM 5, TPM 250,000, **RPD 20** (its own quota), reset at midnight Pacific |

Verified call details are in `docs/api-notes.md`, which overrides this section where they differ.

**Calling the models**

- **Groq:** `POST https://api.groq.com/openai/v1/chat/completions` with `response_format={"type": "json_schema", "json_schema": {"name": ..., "strict": true, "schema": ...}}`, `reasoning_effort`, `max_completion_tokens` and `include_reasoning: false`.
  - Strict mode needs every field required and `additionalProperties: false` on every object; `llm.strict_schema()` adds the latter.
  - Only `finish_reason == "stop"` counts as success.
- **Gemini:** the Interactions API, `client.aio.interactions.create(...)`, reading `output_text`. Only `status == "completed"` counts as success. `generate_content` remains a config switch.
- **Schemas support only a subset of JSON Schema:** types, `title`, `description`, `properties`, `required`, `additionalProperties`, `enum`, `format` (date and time only), `minimum`/`maximum`, `items`, `prefixItems` and `minItems`/`maxItems`.
  - Build every schema with `llm.gemini_schema()`, which inlines `$ref`s and rejects anything else.
  - Keep schemas shallow and make every field required.
  - Convert enum values (step codes, verdicts) to their expected case in code before validating.
- Always validate the parsed output with Pydantic.
- Treat a safety-blocked, empty or truncated response as a failure: retry, then use the next model, then escalate.

**Models** (`config/models.yaml`)

- Every role (extractor, verifier, composer for arm D, arms A and B, narrative generator) uses `openai/gpt-oss-120b`.
- **Fallback order:** 2 retries on the primary, then one attempt on `gemini-3.8-flash`, then one on `gemini-3.7-flash`, then escalate. A 429 that asks for a wait of 60 s or less (a per-minute limit such as Groq's TPM) waits and retries the same model; a longer 429 (a daily limit) or any other 4xx goes straight to the next model.
- A run that falls back must say so in its results, because §14.1 wants every arm on the same model.
- **Effort** (Groq `reasoning_effort`, or Gemini `thinking_level` on the fallbacks): `low` for the extractor and the narrative generator. The verifier starts at `medium` and moves to `low` only if the Gate G1 numbers hold on dev.
- Reasoning tokens count toward limits. Groq's `completion_tokens` already includes them.
- Only change effort or prompts based on measured dev-set results.

**Quota rules.** The binding constraint is **Groq's tokens per day**. On the Gate G1 cases a verifier call averaged about 2,000 tokens at `medium` effort (mostly reasoning) and an extraction about 800, so Groq serves about 100 case verifications a day; Gemini adds at most 40 requests a day across both models. `make budget` always uses the latest measured averages.

- Limits come from the user (Groq console → Limits; AI Studio rate-limit page, which lists limits per model and per project). **Never guess them.**
- Groq's daily limits refill continuously, so they're counted over a rolling 24 h.
- Gemini's daily quotas reset at midnight Pacific: 12:30 PM IST until early November, 1:30 PM IST after.
- **Token levers, in this order:** keep `reason` and `differences` fields short (output is the largest share); drop to `low` effort where G1 allows; reuse cached results; then cut scope with SPEC §14.6 and the cut order below.
- **Verifier:** one call per **case**, covering every failed check's candidates plus the interaction candidates (`verifier_batching: per_case`). Switch to `per_violation` only if dev accuracy drops.
- **Cache extraction** in SQLite, keyed by case ID, content hash, model and prompt version. Every arm and every run reuses it.
- **Arm E reuses arm C's coverage** from the same run, and arm F makes no verifier calls.
- `VectorBackend` uses a local embedding model (`sentence-transformers`), never an LLM API.
- **Rate limiter:** token buckets on RPM and TPM, plus daily request and token counters per model: a rolling 24 h for Groq, the Pacific day for Gemini. Every request that reaches an API is counted, including 429s and 5xx. On a 429, honour `retry-after` / `retryDelay`; retry the same model for a per-minute limit, move to the next model for a daily one. The TPM bucket follows Groq's `x-ratelimit-remaining-tokens` header.
- `scripts/estimate_budget.py` (`make budget`) projects requests and tokens against these limits. The eval runner refuses to start a run that would go over the remaining quota unless it's passed `--force`, and it can resume the next day.
- Batch APIs aren't part of the free tiers, so don't build for them.

**Data rule.** Free tiers may keep or use prompts (Google uses free-tier Gemini data to improve its products; Groq keeps data up to 30 days for abuse monitoring unless Zero Data Retention is on). **Only synthetic data may go through either provider.** `docs/adoption.md` describes the production setup: Groq with Zero Data Retention, or the customer's own model provider, with `llm.py` as the only file that changes.

## Stack and conventions

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel on SQLite, httpx (also the Groq client), asyncio (checks run in parallel under the rate limiter), `google-genai`, `hindsight-client`, and `sentence-transformers` for arm D's local embeddings. Run pytest for anything deterministic. Use ruff for formatting and linting.
- **Frontend:** Next.js (app router), TypeScript, Tailwind, shadcn/ui, Recharts. Use typed API clients generated from, or hand-mirrored against, the FastAPI OpenAPI schema.
- Every module gets a short docstring saying what it owns and what it never does (see the SPEC §3 table).
- **Write tests for:** `rules.py`, `classify`, `precedence.py` (floor, conflicts, removal rule), `memory.citations`, maturity and review mode, and metrics. Use recorded Hindsight fixtures so the tests run offline.
- **Make targets:** `setup`, `seed`, `reset`, `test`, `api`, `web`, `gate1`, `eval ARM=<A|B|C|D|E|F> SPLIT=<dev|test>`, `replay BACKEND=<hindsight|vector>`, `budget`.
- Config lives in `.env` (keep `.env.example` up to date) plus `config/*.yaml`. No secrets in the repo.

## Scope discipline

Build the MVP (SPEC §16) before any stretch item. Cut in this order when behind: ablation arm F, boundary map, the separate generalized class (merge it into known with its differences listed), arm E, and finally the test set, reduced to 30 cases. Never cut arm D, the override beat, the interaction cases or the risk floor. Those are what the judges score.

## Writing: README, docs, UI copy

- Leave out internal history ("what changed from the pitch"), unverified claims about other companies, and statements about competitors' features unless you've verified them in the competitor's own docs.
- Give counts, not bare percentages: "0 of 14", not "0%". Publish per-case results.
- State the limits: synthetic data, one domain, small sample, estimated time savings.
- Use plain language in the UI. Explain every procurement term on first use with a glossary tooltip (`web/lib/glossary.ts`).

## How to work

- Work one phase at a time (SPEC §17). At the end of a phase, run the tests and the phase gate and report: what's built, the gate's result with its numbers, and what's at risk.
- **Stop and ask before** changing any decision in SPEC §2–§10 (classes, floor, composition rule, memory design, metrics), adding a dependency not listed here, or running anything against the test split.
- **Record every change in `docs/CHANGELOG.md`** as it happens (newest first): what changed, why, and whether the user decided it or an API behaviour forced it. That covers code, config, docs, data and decisions.
- If a documented Hindsight, Groq or Gemini behaviour turns out different, update `docs/api-notes.md`, adapt the code, and mention it in your phase report.
