# API notes (verified in Phase 0, 28 Sep 2026)

These notes **override CLAUDE.md and SPEC.md** where they disagree (CLAUDE.md, first paragraph). Each call
below was checked against the installed package source *and* run live. The fixtures are in `tests/fixtures/`,
and the measurements are in `docs/phase0_results.json`, written by `scripts/phase0_spike.py`.

| Package | Version | Server |
|---|---|---|
| `hindsight-client` | 0.10.1 | Hindsight Cloud `https://api.hindsight.vectorize.io`, `api_version` 0.10.1 |
| `google-genai` | 2.25.0 | Gemini API (free tier) |
| Python | 3.12.10 (Windows) | — |

## Divergences from CLAUDE.md / SPEC (act on these)

| # | Doc said | Verified reality | What the code does |
|---|---|---|---|
| D1 | Extraction mode is a retain parameter | It is a **bank setting**: `retain_extraction_mode` on `create_bank` / `update_bank_config`. Values: `concise` (default), `verbose`, `custom`, `verbatim`, `chunks` | Set once per bank; we use **`concise`** (see "Extraction mode" below) |
| D2 | `retain(..., observation_scopes=...)` | `Hindsight.retain()` has **no** `observation_scopes` parameter. Only the item dict of `retain_batch`/`aretain_batch` accepts it | All retains go through `aretain_batch([item])` |
| D3 | `observation_scopes` values unconfirmed | `"per_tag"`, `"combined"` (default), `"shared"`, or `list[list[str]]` (generated model docstring). Live: `per_tag` gave exactly one observation scope per tag | Use `"per_tag"` |
| D4 | "There is no `include_facts` argument" on reflect | True on the wire (`include: {facts: {}}`), but the **Python client spells it `include_facts=True`** (bool) and builds `include` itself | `areflect(..., include_facts=True)` |
| D5 | recall `include={"source_facts": ...}` | Client flags: `include_source_facts=True`, `max_source_facts_tokens` (default **4096 total**, `-1` = unlimited). Source facts come back **on the response**, as `response.source_facts: dict[fact_id → RecallResult]`, not on each result | Citations read `response.source_facts[id].document_id`; use `max_source_facts_tokens=-1` for citation recalls and check `response.source_facts_truncated` |
| D6 | SPEC §8.4 `types=["experience","observation"]` (+`world` for policy) | Hindsight assigns its **own** fact type at extraction. Most of our case facts came back as **`world`**, not `experience` (for example, "Case PR-2026-0233 … failed the bank check" is `world`) | Recall **always** includes `world`: `types=["world","experience","observation"]` |
| D7 | reflect `response_schema=Procedure.model_json_schema()` | With Pydantic's `$ref`/`$defs` schema, reflect returned **objects flattened to strings** (`"steps": ["VERIFY_BANK_CALLBACK", …]`) with `structured_output_error: null`, which is silently wrong. With the **inlined** schema (`llm.gemini_schema(Procedure)`), the output validated | Always pass the inlined schema, and always `Procedure.model_validate(structured_output)` in code |
| D8 | Missions/dispositions via bank config | `create_bank(retain_mission=, observations_mission=, reflect_mission=, retain_extraction_mode=)` works (PUT). Its `disposition_*` args are **deprecated**; set them with `update_bank_config(disposition_skepticism=5, disposition_literalism=4, disposition_empathy=2)` (PATCH `{"updates": …}`) | As stated |
| D9 | Can Hindsight Cloud's LLM be chosen? | **No.** The resolved bank config has no provider/model keys (the only LLM-related keys are `consolidation_llm_batch_size`, `consolidation_llm_parallelism`, `llm_gemini_safety_settings`, `mental_model_min_refresh_interval_seconds`). The Cloud docs and pricing page don't name the model. Provider selection exists only as **self-hosted** env vars. `test_bank_llm` is disabled on Cloud (`features.bank_llm_health: false`), and it never reveals the model anyway | `docs/benchmark.md` must say that **arm C composes with Hindsight Cloud's undisclosed model while arm D composes with `gemini-3.8-flash`** |
| D10 | Observation history: "use Hindsight's if exposed" | **Exposed**: `client.memory.get_observation_history(bank_id, memory_id)`. Observations are **revised in place** (same id) | Lesson panel diffs use this; `observation_snapshots` stays as the ledger copy |
| D11 | Gemini call style unconfirmed | Both exist in 2.25.0; **Interactions chosen** on measured reliability (below) | `config/models.yaml: call_style: interactions`; `generate_content` remains a switch |
| D12 | SPEC lives at `docs/SPEC.md` | It was at the repo root | Moved to `docs/SPEC.md` |
| D13 | Every role on `gemini-3.8-flash` (free tier) | Gemini's free tier is **20 RPD per model**. On 28 Sep 2026 the user moved the primary to **Groq `openai/gpt-oss-120b`** | `models.yaml` roles → `openai/gpt-oss-120b`; fallbacks `gemini-3.8-flash`, then `gemini-3.7-flash`. See "Groq" below |
| D15 | SPEC §8.4 interaction recall: `tags=["interaction"]`, then filter by `metadata.combo` | With `per_tag` scopes, the observation built under `interaction` carries **only** `["interaction"]` (fixture `recall_interaction.json`), so with several families it would merge I1 and I3 into one lesson and has no combo to filter on | The detector recalls interactions with `tags=[combo:<a+b>, …]` for every subset (at least 2) of the case's failed checks, `any_strict`. Each combo scope consolidates only its own combination |
| D14 | Daily quotas reset at midnight Pacific | True for Gemini. **Groq refills continuously**: after 1 and 2 requests, `x-ratelimit-reset-requests` read `1m26.4s` and `2m52.8s` (86,400 s ÷ 1,000 RPD per request) | Groq limits are counted over a rolling 24 h from `llm_calls` (`daily_window: rolling_24h`) |

## Hindsight: verified calls

Client construction, in `api/memory/hindsight_backend.make_client()`, which is the only importer (rule 8):

```python
Hindsight(base_url="https://api.hindsight.vectorize.io", api_key=HINDSIGHT_API_KEY,
          timeout=120.0, max_attempts=2, user_agent="edgememory/0.0.1")
```

Every convenience method has an async twin (`aretain_batch`, `arecall`, `areflect` and so on). The sync ones
call `run_until_complete` and fail inside a running loop, so FastAPI code must use the `a*` methods. The
low-level `client.memory`, `client.banks` and `client.operations` APIs are async-only. The client retries
only recall and reflect, only on 429/503, with jitter; retains are never retried.

### Bank setup

```python
await hs.acreate_bank(bank_id, retain_mission=..., observations_mission=..., reflect_mission=...,
                      retain_extraction_mode="concise")                   # PUT /v1/default/banks/{id}
await hs.aupdate_bank_config(bank_id, disposition_skepticism=5, disposition_literalism=4,
                             disposition_empathy=2, enable_auto_consolidation=True,
                             enable_observations=True)                    # PATCH …/config {"updates": {...}}
await hs.aget_bank_config(bank_id)   # -> {"bank_id", "config": <resolved>, "overrides": <bank-level>}
await hs.acreate_directive(bank_id, name, content, priority=0, is_active=True, tags=None)
await hs.alist_directives(bank_id, tags=None, limit=None, offset=None)
await hs.adelete_bank(bank_id)
```

- The resolved config echoed every value we set (fixture `bank_config_concise.json`).
- `update_bank_config` also exposes `max_observations_per_scope`, `observation_scope_limits`,
  `recall_budget_*`, `reflect_default_options` and `audit_log_enabled`. We don't use them yet.
- Directives: reflect applies untagged directives. Reflect's `based_on.directives` listed all **5**.
- `clone_bank` / `export_bank` / `import_bank` exist. They're a possible cheaper `make reset` for the demo
  bank, but that's **unverified**.

### Retain

```python
item = {"content": str, "timestamp": datetime | ISO str, "context": str, "document_id": case_id,
        "metadata": {str: str}, "entities": [{"text": "V-031", "type": "vendor"}],
        "resolve_entities": False, "tags": [...], "observation_scopes": "per_tag",
        "update_mode": "replace" | "append", "strategy": str | None}
resp = await hs.aretain_batch(bank_id, [item], document_id=None, document_tags=None,
                              retain_async=False, operation_id=None)
# resp: success, bank_id, items_count, async (var_async), operation_id(s), usage{input_tokens,
#        output_tokens, total_tokens, cached_tokens, thoughts_tokens}
```

- `metadata` values must be strings (`Dict[str, StrictStr]`). `update_mode` is validated as `replace`/`append`.
- `timestamp` accepts a `datetime` or a string (anyOf). `"unset"` is not tested.
- `operation_id` only applies with `retain_async=True`; the client warns otherwise.
- `hs.suspend_retains()` is a context manager that no-ops retains. It could keep eval runs from writing, if needed.
- **Measured (concise, 5 seeds):** sync retain took **3.1–5.0 s**. Usage was **2,370–2,514 input** and
  742–1,220 output tokens per seed, with thoughts 0. Verbose took 2.3–8.2 s with 513–1,688 output tokens.

**Extraction mode: `concise` chosen** (SPEC §8.3 test, fixtures `list_memories_{concise,verbose}.json`):

| | concise | verbose |
|---|---|---|
| Seeds whose facts keep every step code | 5 of 5 | 5 of 5 |
| "Why the standard process did not fit" kept | 5 of 5 (a fact of its own, or the fact's trailing context clause) | 5 of 5 |
| Facts per seed | 3–5, consistent and atomic | 1–6; **2 of 5 seeds collapsed into one long fact**, and one included leaked mission text ("The user requested an extraction of…") |
| Output tokens (5 retains) | 4,892 | 5,435 |

Codes survive literally in a dedicated fact ("R. Menon approved step codes VERIFY_BANK_CALLBACK, HOLD_PAYMENT,
and HOLD_PO …"). The interaction seed also kept "while removing HOLD_PO".

### Recall

```python
resp = await hs.arecall(bank_id, query, types=["world", "experience", "observation"],
                        prefer_observations=True, include_source_facts=True, max_source_facts_tokens=-1,
                        budget="mid", max_tokens=2048, tags=[f"step:{check}"], tags_match="any_strict",
                        query_timestamp="2026-09-20T10:00:00+05:30", trace=False,
                        tag_groups=None, min_scores=None, temporal_window=None,
                        include_entities=False, include_chunks=False)
```

- `tags_match`: `any` (the default; **includes untagged**), `all`, `any_strict`, `all_strict`, `exact`. This
  matches CLAUDE.md.
- `query_timestamp` is a string, used as an anchor for relative time and recency scoring, **not a filter**.
  `temporal_window` only re-ranks and doesn't drop anything.
- `min_scores` exists (`semantic`, `keyword`, `reranker`, `final`). **We never use it** (rule 7).
- `RecallResult` fields: `id, text, type, entities, context, occurred_start, occurred_end, mentioned_at,
  document_id, metadata, chunk_id, tags, source_fact_ids, scores{final, reranker, semantic, keyword},
  attachments`. `RecallResponse`: `results, trace, entities, chunks, source_facts, source_facts_truncated`.
- **Observations** come back with `document_id: null` and `metadata: {}`. They carry `tags` and
  `source_fact_ids`. **Facts** carry `document_id` (our case ID) and our `metadata` (`case_id`, `kind`, …).
- Live, the `step:vendor` recall returned **one observation** with 9 `source_fact_ids`. Through
  `response.source_facts[id].document_id` these resolve to **PR-2026-0417 (4 facts) and PR-2026-0488 (5 facts)**.
  This is the §8.6 citation path, and fixture `recall_violation_vendor.json` is the unit-test input for
  `memory.citations()`.
- **Tag isolation:** the `step:bank` recall under `any_strict` returned only memories tagged `step:bank`,
  so no `interaction`-tagged memory leaked in.
- **Latency:** 586 ms per violation, 377 ms for the interaction recall (`budget="mid"`).

**`memory.citations(result, response)` rule, derived from the fixtures:**

- For a fact, use `document_id`, then `metadata.case_id`.
- For an observation, map `[response.source_facts[i].document_id for i in result.source_fact_ids]`.
- If `response.source_facts_truncated` is true, re-query or mark the citation unresolved (never guess).
- Strip `-override-n`.

### Reflect

```python
resp = await hs.areflect(bank_id, query, budget="low", context=None, max_tokens=4096,
                         response_schema=gemini_schema(Procedure),  # INLINED (D7)
                         tags=[...], tags_match="any", include_facts=True,
                         include_tool_calls=False, fact_types=None, apply_all_directives=False,
                         exclude_mental_models=False,
                         reflect_search_observations_max_tokens=None,
                         reflect_search_observations_include_entities=None)
# resp: text (markdown), based_on{memories[ReflectFact{id,text,type,context,occurred_*}],
#        mental_models, directives}, structured_output (dict), structured_output_error, usage, trace
```

- `based_on.memories` items have **no `document_id`**, only `id`. To map them to case IDs, match `id`
  against recalled or listed memory IDs (§8.6 "map based_on to case IDs").
- **Measured:** budget `low` took 7.6 s (24,497 in / 1,432 out tokens) and then 16.5 s with the inlined schema
  (18,560 in / 1,560 out). Budget `mid` took 7.3 s (18,196 in / 1,479 out).
- Content was correct on the I3 test. It started from U, applied PR-2026-0312, removed `HOLD_PO` citing
  PR-2026-0312, and cited a case for every step (fixture `reflect_inlined_schema.json`).
- The default budget is `low`. SPEC §8.5 says `mid`, dropping to `low` if dev p95 is over 10 s. Both
  measured 7–17 s, so expect to need `low` and the "composing…" state.

### Consolidation and observations

- Consolidation is automatic after retain (`enable_auto_consolidation=True`, `enable_observations=True`).
  There's one consolidation operation per retained document.
  - Status: `await hs.operations.list_operations(bank_id, status="pending"|"processing"|"completed"|"failed"|"cancelled", type="consolidation")`
  - Manual trigger: `hs.banks.trigger_consolidation(bank_id)`
- **Measured delay (clean run):** one new retain into a bank with 5 seeds, then **4.1 s** after the retain
  returned the `step:vendor` observation included the new case (polled at 1 s).
  - The first 5-retain batch settled within 3.3 s (verbose) and at most 25.5 s (concise), but the concise
    figure is an upper bound because its polling started only after the verbose bank's retains.
  - **Polling plan for §8.9:** check every 1 s with backoff to 5 s, give up at 60 s, then show
    "consolidating…" and fall back to the ledger snapshot.
- **Observation revision is visible:**
  - before: "…as demonstrated in cases PR-2026-0417 and PR-2026-0488"
  - after: "…ISO 9001, ISO/IEC 17025, or IATF 16949 certificate … as demonstrated in cases PR-2026-0417,
    PR-2026-0488, and PR-2026-0520"
  - The observation ID stayed the same.
- `await hs.memory.get_observation_history(bank_id, memory_id)` returns a list of
  `{previous_text, previous_tags, previous_occurred_start/end, previous_mentioned_at, changed_at,
  new_source_memory_ids, source_facts[...]}`. It had 2 entries after 3 cases (1→2 cases, 2→3 cases).
- `await hs.memory.list_observation_scopes(bank_id)` returns `{scopes: [{tags, count}], total, limit, offset}`.
  Live it gave 5 scopes: `combo:bank+budget`, `interaction`, `step:approver`, `step:bank`, `step:vendor`.
- `await hs.alist_memories(bank_id, type="observation"|"world"|"experience", search_query=None, limit=100, offset=0)`
  returns `items[{id, text, fact_type, document_id, metadata, tags, proof_count, source_memory_ids, state,
  consolidated_at, invalidated_at, …}]`.

### Mental models (stretch only)

`create_mental_model(bank_id, name, source_query, tags=None, max_tokens=None, trigger=None, id=None)`, where
`trigger` is a dict (for example `{"refresh_after_consolidation": True}`); only the named keys are sent.
Also `refresh_mental_model(bank_id, id)`. Signatures come from the source; **not run live**.

### Hindsight Cloud cost (https://vectorize.io/pricing, read 28 Sep 2026)

- Retain $10.00 per million input tokens; recall $0.75 per million tokens; reflect $0.05 per call.
- Consolidation isn't priced separately (unverified).
- At the measured ~2,400 input tokens, one retain costs about $0.024. `make budget` projects the week.

## Gemini: verified calls

Client: `genai.Client(api_key=GEMINI_API_KEY)`. **The SDK doesn't retry by default** (`http_options.retry_options`
is None, meaning "never retry"), so `llm.py` owns every retry and every request is counted.

`client.models.list()` confirms both IDs:

| Model | Listed | Input limit | Output limit | `thinking` | `supported_actions` |
|---|---|---|---|---|---|
| `models/gemini-3.8-flash` | yes | 1,048,576 | 65,536 | true | generateContent, countTokens, createCachedContent, batchGenerateContent |
| `models/gemini-3.7-flash` | yes | 1,048,576 | 65,536 | true | same |

`batchGenerateContent` is listed, but CLAUDE.md says Batch isn't available on the free tier. Don't build for it.

### Interactions API (chosen: `call_style: interactions`)

```python
it = await client.aio.interactions.create(
    model="gemini-3.8-flash", input=prompt, system_instruction=system,
    response_format={"type": "text", "mime_type": "application/json", "schema": schema},
    generation_config={"thinking_level": "low" | "medium" | "high" | "minimal", "max_output_tokens": 8192},
    store=False)
text = it.output_text
status = it.status   # "completed" is the only usable status; also in_progress, requires_action, failed,
                     # cancelled, incomplete, budget_exceeded, queued
u = it.usage         # total_input_tokens, total_output_tokens, total_thought_tokens, total_cached_tokens
```

- `create(**body)` validates kwargs into a Pydantic request. The `"schema"` key is the alias of `schema_`, and
  it is **serialized as `"schema"`** (checked by model round-trip), so the schema really is sent.
- There is **no finish reason** field, so a safety block has to surface as a non-`completed` status or an
  empty `output_text`. Both are treated as failures.
- Errors are subclasses of `google.genai._gaos.errors.GenAiError` with `.status_code`, `.body` and `.headers`.
  These differ from the `generate_content` errors.
- `store=False` was accepted, so interactions aren't stored server-side.

### generate_content (kept as a switch)

```python
resp = await client.aio.models.generate_content(model=..., contents=prompt,
    config=types.GenerateContentConfig(system_instruction=..., response_mime_type="application/json",
        response_json_schema=schema, thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        max_output_tokens=8192))
resp.text; resp.candidates[0].finish_reason (enum: STOP, SAFETY, …); resp.prompt_feedback.block_reason
resp.usage_metadata.prompt_token_count / candidates_token_count / thoughts_token_count / cached_content_token_count
```

- `types.ThinkingLevel` is `MINIMAL | LOW | MEDIUM | HIGH`.
- Errors: `google.genai.errors.ClientError` / `ServerError` (`APIError`) with `.code`, `.status`, `.message`
  and `.details` (the JSON body).

### Structured output

`llm.gemini_schema(Model)`:

- inlines `$ref`s and drops `default`;
- **raises** on anything outside the supported subset (for example `anyOf` from `Optional`), and on any
  property that isn't required.

Enum values are normalised to their canonical case before Pydantic validation (`llm.normalise_enums`). Every
successful live call validated. The verifier-shaped test gave C1 `partial` ("different category: indirect
MRO vs direct material") and C2 `no` ("different cause") on all 6 of 6 successful answers (both styles,
both models).

### Measured (spike, 28 Sep 2026; 28 attempts, 6 successes)

| Style | Model | Thinking | Latency | In / out / thinking tokens |
|---|---|---|---|---|
| interactions | 3.8-flash | low | 20.5 s, 10.9 s | 271 / 210, 205 / **0** |
| interactions | 3.8-flash | **medium** (verifier) | **43.4 s** | 271 / 182 / **417** |
| generate_content | 3.8-flash | low | 3.4 s, 3.6 s | 271 / 177, 184 / 0 |
| generate_content | 3.7-flash (fallback) | low | 93.1 s | 271 / 176 / 191 |

**Reliability, which is why Interactions was chosen:**

| Style | Attempts | OK | 503 "high demand" | 429 |
|---|---|---|---|---|
| generate_content | 25 | 3 | 21 | 1 |
| interactions | 3 | 3 | 0 | 0 |

The sample is small, and both were measured in the same window. Re-check on dev before G1.

- **503 `UNAVAILABLE` "This model is currently experiencing high demand"** hit both 3.8-flash and 3.7-flash.
  `llm.py` now backs off exponentially with jitter between 5xx retries. Whether 503s count toward the
  RPM/RPD quota is **unknown**, so the counter counts them (conservative).
- **429 `RESOURCE_EXHAUSTED`** body: `Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 5, model: gemini-3.8-flash … Please retry in 7.406474259s`.
  The part we logged doesn't give the window (per minute or per day). The short retry delay suggests per
  minute, but **the real RPM/TPM/RPD must come from AI Studio** (config/limits.yaml).
  - `llm.py` parses `retryDelay` from the details. The full error body (up to 4,000 chars) is now logged.
- Thinking on 3.8-flash: `low` reported **0** thinking tokens (4 of 4 calls) and `medium` reported 417.
  The verifier at `medium` is **slow (43 s)**, so G1 has to measure whether `low` holds accuracy.

## Quota (config/limits.yaml)

- **From the user's AI Studio screenshot (28 Sep 2026):** both `gemini-3.7-flash` and `gemini-3.8-flash` are
  at **RPM 5, TPM 250,000, RPD 20**. Each model has its own usage counter (3.7: 10/20, 3.8: 19/20), so the
  fallback **has its own quota**, giving 40 requests/day across both.
- **The counter must count every request that reaches the API.** AI Studio showed 19 used on 3.8-flash while
  the ledger had counted 17, because the 429 wasn't counted. `llm.py` now counts 429s as well as 5xx, and
  today's rows were brought up to AI Studio's figures.
- **TPM isn't binding:** about 550 tokens per verifier-sized request. **RPM 5 is**: the limiter serialises
  calls about 12 s apart per model.
- **RPD 20 makes the SPEC §14.5 plan infeasible in 7 days** (`make budget`): full 30 quota-days (planning) or
  140 (with measured overhead); reduced (§14.6) 21 or 98. A decision is needed before Phase 1.
- The quota day is computed in code (`settings.pacific_date`), with the US DST rule written out because
  Windows has no tz database. The reset is 07:00 UTC (12:30 PM IST) until 1 Nov 2026, then 08:00 UTC
  (1:30 PM IST).

## Groq (primary since 28 Sep 2026)

HTTP only, through `httpx` (already in the stack); there's no `groq` SDK dependency. The key is
`GROQ_API_KEY` in `.env`.

### Model

`GET https://api.groq.com/openai/v1/models` lists `openai/gpt-oss-120b`: active, `context_window` 131,072,
`max_completion_tokens` 65,536, `supported_features` [tools, json_mode, structured_outputs, reasoning]. The
listing's `pricing` field gives $0.15 per million prompt tokens and $0.60 per million completion tokens
(these apply to paid use).

### Call

```python
POST https://api.groq.com/openai/v1/chat/completions
{"model": "openai/gpt-oss-120b",
 "messages": [{"role": "system", ...}, {"role": "user", "content": prompt}],
 "response_format": {"type": "json_schema",
                     "json_schema": {"name": "output", "strict": true, "schema": strict_schema(gemini_schema(M))}},
 "reasoning_effort": "low" | "medium" | "high",
 "max_completion_tokens": 8192,
 "include_reasoning": false}
```

- **Strict mode** (constrained decoding) is supported on `gpt-oss-120b` (Groq structured-outputs docs). It
  needs every field required and `additionalProperties: false` on every object; `llm.strict_schema()` adds
  the latter. Best-effort mode can return HTTP 400 "Generated JSON does not match the expected schema".
- Response fields used:
  - `choices[0].message.content` (JSON text)
  - `choices[0].finish_reason` (only `stop` is usable; `length` and others are failures)
  - `usage.prompt_tokens`, `usage.completion_tokens` (**includes reasoning**), `usage.completion_tokens_details.reasoning_tokens`
  - `usage.prompt_tokens_details.cached_tokens`
- `llm.py` logs the output tokens as completion minus reasoning.
- **`include_reasoning: false` was accepted.** It removes `message.reasoning` (560 characters in the default
  run), but reasoning tokens are still used (100 vs 131 in that pair of runs).
- **`max_completion_tokens: 9000` was accepted (200)** even though the TPM is 8,000, so the cap isn't
  reserved against TPM up front. We use 8,192.
- Errors are HTTP status plus a JSON `error`. A bad key gives `401 invalid_api_key`. On 429 Groq sets
  `retry-after` in seconds, and `llm.py` honours it and moves to the next model. Other 4xx move straight to
  the next model with no same-model retry.

### Rate-limit headers (Groq rate-limits docs, confirmed live)

- `x-ratelimit-limit-requests` and `x-ratelimit-remaining-requests` are **RPD**, and `x-ratelimit-reset-requests`
  is when one request is back.
- `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens` and `x-ratelimit-reset-tokens` are **TPM**.
- **No TPD header**, so `llm.py` enforces TPD from its own rolling 24 h log.
- Groq's docs say cached tokens don't count toward rate limits.
- Live after one request: `limit-requests 1000, remaining 999, reset 1m26.4s; limit-tokens 8000,
  remaining 7006, reset 7.455s`. Region `bom`.

### Limits (user's Groq console screenshot, 28 Sep 2026)

`openai/gpt-oss-120b`: RPM 30, RPD 1,000, **TPM 8,000, TPD 200,000**. **TPD binds**: at about 4,000 tokens per
per-case verifier call, that's roughly 50 calls a day (`make budget`).

**TPM also caps a single request (verified 28 Sep 2026, learning-curve replays).**
- A request whose tokens exceed the 8,000 TPM limit is refused outright with HTTP 413 "Request too large for
  model", not a 429 with a wait.
- `llm.py` treats it like any other 4xx and moves to the next model.
- It happened twice, both on per-case verifier prompts late in a replay, when memory held the seeds plus about
  20 retained cases: TEST-032 (Hindsight replay) and TEST-019 (vector replay).
- Seed-only runs, meaning every benchmark arm and the demo, have stayed well under the cap.

### Measured (all strict, all schema-valid)

| Prompt | Effort | Latency | In / out / reasoning tokens | Verdicts |
|---|---|---|---|---|
| small (2 candidates) | low | 1.2 s | 453 / 154 / 126 | C1 partial, C2 no |
| small (2 candidates) | medium | 2.2 s | 501 / 123 / 613 | C1 partial, C2 no |
| per-case size (15 candidates, 3 violations) | low | 3.9 s | 1,489 / 1,282 / 133 | 15 of 15 |
| per-case size (15 candidates, 3 violations) | medium | 6.0 s | 1,537 / 1,313 / 1,177 | 15 of 15 |

- **4 of 4 attempts succeeded**, with 0 errors, a much better rate than Gemini's today.
- **Output tokens dominate:** about 1,300 per 15 verdicts. Short `reason`/`differences` fields are the
  biggest token lever after effort.
- Three raw spike requests (to capture headers and test `include_reasoning` and the 9,000 cap) went through
  `httpx` directly rather than `llm.py`, so they aren't in `llm_calls`. Every later call goes through `llm.py`.

### Data policy (https://console.groq.com/docs/your-data, read 28 Sep 2026)

- "By default, Groq does not retain customer data for inference requests." Data may be kept up to 30 days
  for reliability or abuse monitoring.
- Zero Data Retention can be enabled in Data Controls. Data is stored in US GCP.
- The page doesn't say whether API data is used for training, and it doesn't distinguish free from paid tiers.
- The CLAUDE.md data rule (synthetic data only) still applies. `docs/adoption.md` must describe the
  production setup: ZDR on, or the customer's own provider.
