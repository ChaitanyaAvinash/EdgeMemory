"""Every LLM call made by our code (CLAUDE.md rule 9).

Owns: the provider clients (Groq over its OpenAI-compatible HTTP API via httpx; Gemini via google-genai),
JSON-schema structured output, Pydantic validation, retries, the fallback chain, the RPM/TPM token buckets,
the per-model daily request and token counters (midnight Pacific), the output cache, and logging each
attempt to `llm_calls`.
Never: computes numbers for the UI, decides anything, or sees real (non-synthetic) data. Hindsight's own
LLM calls (retain, consolidation, reflect) don't pass through here; they run on Hindsight Cloud.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from api import ledger
from api.settings import config, load_env, pacific_date

log = logging.getLogger("edgememory.llm")
T = TypeVar("T", bound=BaseModel)

GROQ_URL = "https://api.groq.com/openai/v1"
# A 429 asking to wait at most this long is a per-minute limit: wait and retry the same model.
SHORT_429_S = 60.0

# Keys the structured-output schema may use: the Gemini subset (CLAUDE.md), which Groq strict mode also accepts.
ALLOWED_SCHEMA_KEYS = {
    "type",
    "title",
    "description",
    "properties",
    "required",
    "additionalProperties",
    "enum",
    "format",
    "minimum",
    "maximum",
    "items",
    "prefixItems",
    "minItems",
    "maxItems",
}
# Finish reasons / statuses that mean "no usable answer".
BAD_FINISH = {
    # Gemini generate_content FinishReason
    "SAFETY",
    "RECITATION",
    "BLOCKLIST",
    "PROHIBITED_CONTENT",
    "SPII",
    "OTHER",
    "MALFORMED_FUNCTION_CALL",
    "IMAGE_SAFETY",
    "LANGUAGE",
    # Gemini Interactions has no finish reason; only status "completed" is usable
    "failed",
    "cancelled",
    "incomplete",
    "budget_exceeded",
    "requires_action",
    "in_progress",
    "queued",
    # OpenAI-compatible (Groq): only "stop" is usable
    "length",
    "content_filter",
    "tool_calls",
    "function_call",
}


class LLMUnavailable(RuntimeError):
    """Every attempt on every model failed. Callers must escalate to a human (CLAUDE.md rule 11)."""


class QuotaExhausted(LLMUnavailable):
    """A daily request or token quota for a model is used up (per the counters in `quota_usage`)."""


class ProviderHTTPError(RuntimeError):
    """Non-2xx response from an HTTP provider (Groq)."""

    def __init__(self, code: int, body: str, headers: dict[str, str]):
        super().__init__(f"{code}: {body[:4000]}")
        self.code = code
        self.body = body
        self.headers = headers


# --- schema -------------------------------------------------------------------------------------


def gemini_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic model → JSON schema in the supported subset: $refs inlined, every field required.

    Raises ValueError on anything outside the subset (anyOf from Optional fields, defaults on
    non-required fields, and so on), so a bad schema fails in tests rather than at call time.
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node: Any, path: str) -> Any:
        if isinstance(node, list):
            return [walk(n, path) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(defs[node["$ref"].rsplit("/", 1)[-1]], path)
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "default":
                continue
            if key not in ALLOWED_SCHEMA_KEYS:
                raise ValueError(f"{model.__name__}{path}: unsupported schema key {key!r}")
            if key == "properties":
                out[key] = {name: walk(sub, f"{path}.{name}") for name, sub in value.items()}
            elif key in ("items", "prefixItems", "additionalProperties"):
                out[key] = walk(value, f"{path}[]")
            else:
                out[key] = value
        if "properties" in out:
            missing = set(out["properties"]) - set(out.get("required", []))
            if missing:
                raise ValueError(
                    f"{model.__name__}{path}: every field must be required; not: {sorted(missing)}"
                )
        return out

    return walk(raw, "")


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy of `schema` with `additionalProperties: false` on every object (Groq strict mode needs it)."""
    out = copy.deepcopy(schema)

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
            for v in node.values():
                walk(v)

    walk(out)
    return out


def normalise_enums(schema: dict[str, Any], data: Any) -> Any:
    """Map enum strings to the schema's own casing ("hold_po" → "HOLD_PO") before validation."""
    if isinstance(data, dict) and "properties" in schema:
        return {k: normalise_enums(schema["properties"].get(k, {}), v) for k, v in data.items()}
    if isinstance(data, list) and "items" in schema:
        return [normalise_enums(schema["items"], v) for v in data]
    if isinstance(data, str) and "enum" in schema:
        by_fold = {str(e).casefold(): e for e in schema["enum"]}
        return by_fold.get(data.strip().casefold(), data)
    return data


# --- rate limiting ------------------------------------------------------------------------------


class _Bucket:
    """Token bucket refilling `capacity` units per 60 s. The level may go negative after a true-up."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.level = float(capacity)
        self.stamp = time.monotonic()
        self.lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self.level = min(self.capacity, self.level + (now - self.stamp) * self.capacity / 60.0)
        self.stamp = now

    async def take(self, amount: float) -> None:
        amount = min(amount, self.capacity)
        async with self.lock:
            while True:
                self._refill()
                if self.level >= amount:
                    self.level -= amount
                    return
                await asyncio.sleep((amount - self.level) * 60.0 / self.capacity)

    def adjust(self, delta: float) -> None:
        """Charge (delta > 0) or refund (delta < 0) the difference between estimated and actual use."""
        self._refill()
        self.level = min(self.capacity, self.level - delta)


class RateLimiter:
    """Per model: RPM and TPM buckets, plus daily request (RPD) and token (TPD) counters in `quota_usage`.

    A limit that is null in config/limits.yaml is not enforced (it is never guessed); usage is still
    counted so that estimate_budget.py and the demo readout have real numbers.
    """

    def __init__(self, limits: dict[str, Any], db_url: str | None = None):
        self.limits = limits.get("models", {}) or {}
        self.db_url = db_url
        self._rpm: dict[str, _Bucket] = {}
        self._tpm: dict[str, _Bucket] = {}
        self._warned: set[tuple[str, str]] = set()

    def _limit(self, model: str, key: str) -> int | None:
        value = (self.limits.get(model) or {}).get(key)
        if value is None and (model, key) not in self._warned:
            self._warned.add((model, key))
            log.warning("limits.yaml has no %s for %s; not enforced", key, model)
        return value

    def _row(self, s: Session, model: str) -> ledger.QuotaUsage:
        day = pacific_date()
        return s.exec(
            select(ledger.QuotaUsage).where(
                ledger.QuotaUsage.model == model, ledger.QuotaUsage.pacific_date == day
            )
        ).first() or ledger.QuotaUsage(model=model, pacific_date=day)

    def _rolling(self, model: str) -> bool:
        """Groq's daily limits refill continuously (x-ratelimit-reset-requests = 86.4 s per request at 1,000 RPD),
        so they are counted over the last 24 h from llm_calls. Gemini's reset at midnight Pacific."""
        return (self.limits.get(model) or {}).get("daily_window") == "rolling_24h"

    def _rolling_usage(self, model: str) -> tuple[int, int]:
        """(requests, tokens) still counted against Groq's daily limits: spend not yet refilled.

        Groq refills its daily limits continuously (verified for requests: x-ratelimit-reset-requests was 86.4 s
        after one request at 1,000 RPD; assumed the same for tokens, which have no header). So this replays the
        last 24 h of logged calls as a bucket refilling at limit/86,400 per second, instead of a sliding 24 h sum,
        which held back quota Groq had already refilled. If Groq disagrees, its 429 (long retry-after) moves the
        call to the Gemini fallback.
        """
        lim = self.limits.get(model) or {}
        r_req = float(lim.get("rpd") or 0) / 86400
        r_tok = float(lim.get("tpd") or 0) / 86400
        now_aware = ledger.utcnow()
        since = now_aware - timedelta(hours=24)  # the query needs an aware datetime
        now = now_aware.replace(tzinfo=None)  # rows come back naive (UTC)
        with Session(ledger.engine(self.db_url)) as s:
            rows = s.exec(
                select(ledger.LlmCall).where(
                    ledger.LlmCall.model == model,
                    ledger.LlmCall.created_at >= since,
                    ledger.LlmCall.cache_hit == False,  # noqa: E712
                )
            ).all()
        sent = sorted((r for r in rows if not r.error.startswith("quota:")), key=lambda r: r.created_at)
        debt_r = debt_t = 0.0
        prev = None
        with Session(ledger.engine(self.db_url)) as s:
            cal = s.exec(
                select(ledger.QuotaCalibration)
                .where(ledger.QuotaCalibration.model == model, ledger.QuotaCalibration.at >= since)
                .order_by(ledger.QuotaCalibration.at.desc())
            ).first()
        if cal is not None:
            # Start from the provider's own reading; only calls after it are replayed.
            prev = cal.at.replace(tzinfo=None)
            debt_r, debt_t = float(cal.requests_used), float(cal.tokens_used)
            sent = [r for r in sent if r.created_at.replace(tzinfo=None) > prev]
        for r in sent:
            at = r.created_at.replace(tzinfo=None)
            if prev is not None:
                dt = (at - prev).total_seconds()
                debt_r, debt_t = max(0.0, debt_r - r_req * dt), max(0.0, debt_t - r_tok * dt)
            debt_r += 1
            debt_t += r.input_tokens + r.output_tokens + r.thinking_tokens
            prev = at
        if prev is not None:
            dt = (now - prev).total_seconds()
            debt_r, debt_t = max(0.0, debt_r - r_req * dt), max(0.0, debt_t - r_tok * dt)
        return round(debt_r), round(debt_t)

    def requests_today(self, model: str) -> int:
        if self._rolling(model):
            return self._rolling_usage(model)[0]
        with Session(ledger.engine(self.db_url)) as s:
            return self._row(s, model).requests

    def tokens_today(self, model: str) -> int:
        if self._rolling(model):
            return self._rolling_usage(model)[1]
        with Session(ledger.engine(self.db_url)) as s:
            return self._row(s, model).tokens

    def remaining_today(self, model: str) -> int | None:
        rpd = self._limit(model, "rpd")
        return None if rpd is None else max(0, rpd - self.requests_today(model))

    def tokens_remaining_today(self, model: str) -> int | None:
        tpd = self._limit(model, "tpd")
        return None if tpd is None else max(0, tpd - self.tokens_today(model))

    async def acquire(self, model: str, est_tokens: int) -> None:
        remaining = self.remaining_today(model)
        if remaining is not None and remaining <= 0:
            raise QuotaExhausted(f"daily request quota used up for {model}")
        tok_left = self.tokens_remaining_today(model)
        if tok_left is not None and tok_left < est_tokens:
            raise QuotaExhausted(f"daily token quota nearly used up for {model} ({tok_left} left)")
        rpm, tpm = self._limit(model, "rpm"), self._limit(model, "tpm")
        if rpm:
            await self._rpm.setdefault(model, _Bucket(rpm)).take(1)
        if tpm:
            await self._tpm.setdefault(model, _Bucket(tpm)).take(est_tokens)

    def sync_tpm(self, model: str, remaining: int) -> None:
        """Lower the TPM bucket to what the provider says is left this minute (never raises it)."""
        if model in self._tpm:
            b = self._tpm[model]
            b._refill()
            b.level = min(b.level, float(remaining))

    def true_up(self, model: str, est_tokens: int, actual_tokens: int) -> None:
        if model in self._tpm:
            self._tpm[model].adjust(actual_tokens - est_tokens)

    def record(self, model: str, tokens: int) -> None:
        with Session(ledger.engine(self.db_url)) as s:
            row = self._row(s, model)
            row.requests += 1
            row.tokens += tokens
            s.add(row)
            s.commit()

    def sync_requests(self, model: str, used_by_provider: int) -> None:
        """Raise today's request count to what the provider reports (never lower it). Pacific-day models only."""
        if self._rolling(model):
            return
        with Session(ledger.engine(self.db_url)) as s:
            row = self._row(s, model)
            if used_by_provider > row.requests:
                row.requests = used_by_provider
                s.add(row)
                s.commit()


# --- calls --------------------------------------------------------------------------------------


@dataclass
class RawResponse:
    text: str
    finish_reason: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    cached_tokens: int = 0
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class LLMResult(Generic[T]):
    parsed: T
    raw: str
    model: str
    cache_hit: bool
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0


def _retry_delay_seconds(err: Exception) -> float:
    """Seconds to wait after a 429: `retry-after` header (Groq), Gemini RetryInfo, else 10."""
    headers = getattr(err, "headers", None) or {}
    ra = headers.get("retry-after") if hasattr(headers, "get") else None
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    text = json.dumps(getattr(err, "details", None) or getattr(err, "body", None) or str(err), default=str)
    m = re.search(r'retryDelay\\?"?\s*:\s*\\?"(\d+(?:\.\d+)?)s', text)
    return float(m.group(1)) if m else 10.0


def _status_code(err: Exception) -> int | None:
    return getattr(err, "code", None) or getattr(err, "status_code", None)


class LLM:
    def __init__(
        self,
        client: Any = None,
        db_url: str | None = None,
        models_cfg: dict | None = None,
        limits_cfg: dict | None = None,
    ):
        load_env()
        self.cfg = models_cfg or config("models")
        self.db_url = db_url
        self.limiter = RateLimiter(limits_cfg or config("limits"), db_url)
        self._gemini = client  # created lazily: a Groq-only run needs no Gemini key

    # --- providers ---
    def provider(self, model: str) -> str:
        return self.cfg.get("providers", {}).get(model, "gemini")

    @property
    def gemini(self) -> Any:
        if self._gemini is None:
            from google import genai

            self._gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        return self._gemini

    def call_style(self, model: str, override: str | None = None) -> str:
        if self.provider(model) == "groq":
            return "groq_chat"
        return override or self.cfg.get("gemini_call_style", "interactions")

    async def _send(
        self, model: str, style: str, prompt: str, system: str | None, schema: dict, effort: str
    ) -> RawResponse:
        if style == "groq_chat":
            return await self._groq(model, prompt, system, schema, effort)
        if style == "generate_content":
            return await self._generate_content(model, prompt, system, schema, effort)
        return await self._interactions(model, prompt, system, schema, effort)

    async def _groq(
        self, model: str, prompt: str, system: str | None, schema: dict, effort: str
    ) -> RawResponse:
        gcfg = self.cfg.get("groq", {})
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "output", "strict": True, "schema": strict_schema(schema)},
            },
            "reasoning_effort": effort.lower(),
            "max_completion_tokens": gcfg.get("max_completion_tokens", 4096),
        }
        body.update(gcfg.get("extra_body", {}))
        async with httpx.AsyncClient(timeout=gcfg.get("timeout_s", 120)) as http:
            resp = await http.post(
                f"{GROQ_URL}/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                json=body,
            )
        headers = {
            k.lower(): v for k, v in resp.headers.items() if k.lower().startswith(("x-ratelimit", "retry"))
        }
        self.last_headers = (
            headers  # the provider's own rate-limit view, for calibration and the demo readout
        )
        if resp.status_code >= 400:
            raise ProviderHTTPError(resp.status_code, resp.text, headers)
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        u = data.get("usage") or {}
        details = u.get("completion_tokens_details") or {}
        reasoning = int(details.get("reasoning_tokens") or 0)
        return RawResponse(
            text=(choice.get("message") or {}).get("content") or "",
            finish_reason=choice.get("finish_reason") or "",
            input_tokens=int(u.get("prompt_tokens") or 0),
            # completion_tokens includes reasoning; split it so thinking is logged separately
            output_tokens=int(u.get("completion_tokens") or 0) - reasoning,
            thinking_tokens=reasoning,
            cached_tokens=int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0),
            headers=headers,
        )

    async def _generate_content(
        self, model: str, prompt: str, system: str | None, schema: dict, effort: str
    ) -> RawResponse:
        from google.genai import types

        resp = await self.gemini.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_json_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_level=effort.upper()),
                max_output_tokens=self.cfg["max_output_tokens"],
                http_options=types.HttpOptions(timeout=int(self.cfg.get("gemini_timeout_s", 90) * 1000)),
            ),
        )
        u = resp.usage_metadata
        if resp.candidates:
            fr = resp.candidates[0].finish_reason
            finish = getattr(fr, "name", str(fr)) if fr is not None else ""
        else:
            br = getattr(resp.prompt_feedback, "block_reason", None)
            finish = f"BLOCKED:{getattr(br, 'name', br)}"
        return RawResponse(
            text=resp.text or "",
            finish_reason=finish,
            input_tokens=(u.prompt_token_count or 0) if u else 0,
            output_tokens=(u.candidates_token_count or 0) if u else 0,
            thinking_tokens=(u.thoughts_token_count or 0) if u else 0,
            cached_tokens=(u.cached_content_token_count or 0) if u else 0,
        )

    async def _interactions(
        self, model: str, prompt: str, system: str | None, schema: dict, effort: str
    ) -> RawResponse:
        body: dict[str, Any] = dict(
            model=model,
            input=prompt,
            response_format={"type": "text", "mime_type": "application/json", "schema": schema},
            generation_config={
                "thinking_level": effort.lower(),
                "max_output_tokens": self.cfg["max_output_tokens"],
            },
            store=False,
        )
        if system:
            body["system_instruction"] = system
        it = await self.gemini.aio.interactions.create(
            **body, timeout=float(self.cfg.get("gemini_timeout_s", 90))
        )
        u = it.usage
        return RawResponse(
            text=it.output_text or "",
            finish_reason=str(getattr(it.status, "value", it.status) or ""),
            input_tokens=(u.total_input_tokens or 0) if u else 0,
            output_tokens=(u.total_output_tokens or 0) if u else 0,
            thinking_tokens=(u.total_thought_tokens or 0) if u else 0,
            cached_tokens=(u.total_cached_tokens or 0) if u else 0,
        )

    def _sync_from_headers(self, model: str, headers: dict[str, str]) -> None:
        """Groq reports TPM left in x-ratelimit-remaining-tokens and RPD in x-ratelimit-*-requests."""
        try:
            self.limiter.sync_tpm(model, int(headers["x-ratelimit-remaining-tokens"]))
        except (KeyError, ValueError):
            pass
        try:
            limit = int(headers["x-ratelimit-limit-requests"])
            remaining = int(headers["x-ratelimit-remaining-requests"])
        except (KeyError, ValueError):
            return
        self.limiter.sync_requests(model, limit - remaining)

    # --- ledger ---
    def _log(self, **kw: Any) -> None:
        with Session(ledger.engine(self.db_url)) as s:
            s.add(ledger.LlmCall(**kw))
            s.commit()

    def _cache_get(self, role: str, key: str, h: str, model: str, pv: str) -> str | None:
        with Session(ledger.engine(self.db_url)) as s:
            row = s.exec(
                select(ledger.LlmCache).where(
                    ledger.LlmCache.role == role,
                    ledger.LlmCache.cache_key == key,
                    ledger.LlmCache.content_hash == h,
                    ledger.LlmCache.model == model,
                    ledger.LlmCache.prompt_version == pv,
                )
            ).first()
            return row.output_json if row else None

    def _cache_put(self, role: str, key: str, h: str, model: str, pv: str, out: str) -> None:
        with Session(ledger.engine(self.db_url)) as s:
            s.add(
                ledger.LlmCache(
                    role=role, cache_key=key, content_hash=h, model=model, prompt_version=pv, output_json=out
                )
            )
            s.commit()

    # --- the call ---
    async def call(
        self,
        role: str,
        prompt: str,
        schema: type[T],
        prompt_version: str,
        *,
        system: str | None = None,
        cache_key: str | None = None,
        case_id: str = "",
        call_style: str | None = None,
    ) -> LLMResult[T]:
        """Structured call: role model with retries, then each fallback once, else LLMUnavailable."""
        role_cfg = self.cfg["roles"][role]
        primary = role_cfg["model"]
        fallbacks = [m for m in self.cfg.get("fallbacks", []) if m != primary]
        effort = role_cfg.get("effort", "medium")
        js = gemini_schema(schema)
        content_hash = hashlib.sha256(json.dumps([system, prompt, js], sort_keys=True).encode()).hexdigest()[
            :24
        ]

        if cache_key:
            for model in [primary, *fallbacks]:
                hit = self._cache_get(role, cache_key, content_hash, model, prompt_version)
                if hit is not None:
                    self._log(
                        role=role,
                        model=model,
                        prompt_version=prompt_version,
                        call_style="cache",
                        cache_hit=True,
                        raw_output=hit,
                        case_id=case_id,
                        finish_reason="CACHE",
                    )
                    return LLMResult(schema.model_validate_json(hit), hit, model, True, 0)

        # TPM/TPD reservation: prompt estimate plus an allowance for output and reasoning, trued up after.
        est_tokens = (len(prompt) + len(system or "") + len(json.dumps(js))) // 4 + int(
            self.cfg.get("est_output_tokens", 1500)
        )
        plan = [(primary, 1 + int(self.cfg.get("retries", 2)))] + [(m, 1) for m in fallbacks]

        errors: list[str] = []
        for model, attempts in plan:
            style = self.call_style(model, call_style)
            for attempt in range(1, attempts + 1):
                base = dict(
                    role=role,
                    model=model,
                    prompt_version=prompt_version,
                    call_style=style,
                    attempt=attempt,
                    case_id=case_id,
                )
                try:
                    await self.limiter.acquire(model, est_tokens)
                except QuotaExhausted as e:
                    self._log(**base, error=f"quota: {e}")
                    errors.append(str(e))
                    break
                t0 = time.perf_counter()
                try:
                    r = await self._send(model, style, prompt, system, js, effort)
                except Exception as e:  # noqa: BLE001 - providers raise several unrelated error types
                    ms = int((time.perf_counter() - t0) * 1000)
                    code = _status_code(e)
                    self._log(**base, latency_ms=ms, error=f"{type(e).__name__} {code}: {str(e)[:4000]}")
                    errors.append(f"{model}#{attempt}: {type(e).__name__} {code}")
                    if code is not None:
                        # Any request that reached the API is counted, 429s and 5xx included: on 28 Sep
                        # AI Studio showed 19 used where a success-and-5xx-only count gave 17.
                        self.limiter.record(model, 0)
                        self._sync_from_headers(model, getattr(e, "headers", {}) or {})
                    if code == 429:
                        delay = _retry_delay_seconds(e)
                        await asyncio.sleep(delay)
                        if delay <= SHORT_429_S and attempt < attempts:
                            continue  # a per-minute limit (e.g. Groq TPM): same model again after the wait
                        break  # a long (daily) limit: move to the next model
                    if code is not None and 400 <= code < 500:
                        break  # a bad request won't improve on retry; try the next model
                    if attempt < attempts:
                        # 5xx ("high demand") and network errors: exponential backoff with full jitter
                        await asyncio.sleep(random.uniform(0, min(30.0, 2.0 * 2**attempt)))
                    continue
                ms = int((time.perf_counter() - t0) * 1000)
                used = r.input_tokens + r.output_tokens + r.thinking_tokens
                self.limiter.record(model, used)
                self.limiter.true_up(model, est_tokens, used)
                self._sync_from_headers(model, r.headers)
                usage = dict(
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                    thinking_tokens=r.thinking_tokens,
                    finish_reason=r.finish_reason,
                    latency_ms=ms,
                    raw_output=r.text,
                )
                problem = ""
                parsed = None
                if (
                    not r.text.strip()
                    or r.finish_reason in BAD_FINISH
                    or r.finish_reason.startswith("BLOCKED")
                ):
                    problem = f"empty or blocked (finish={r.finish_reason})"
                else:
                    try:
                        data = normalise_enums(js, json.loads(r.text))
                        parsed = schema.model_validate(data)
                    except (json.JSONDecodeError, ValidationError) as e:
                        problem = f"{type(e).__name__}: {str(e)[:500]}"
                self._log(**base, **usage, error=problem)
                if parsed is None:
                    errors.append(f"{model}#{attempt}: {problem}")
                    continue
                out = parsed.model_dump_json()
                if cache_key:
                    self._cache_put(role, cache_key, content_hash, model, prompt_version, out)
                return LLMResult(
                    parsed, r.text, model, False, ms, r.input_tokens, r.output_tokens, r.thinking_tokens
                )
        raise LLMUnavailable("; ".join(errors) or "no attempt made")

    # --- model listings (metadata only; no generation quota) ---
    def list_gemini_models(self) -> list[dict[str, Any]]:
        out = []
        for m in self.gemini.models.list():
            out.append(
                {
                    "name": m.name,
                    "display_name": getattr(m, "display_name", None),
                    "input_token_limit": getattr(m, "input_token_limit", None),
                    "output_token_limit": getattr(m, "output_token_limit", None),
                    "supported_actions": getattr(m, "supported_actions", None),
                    "thinking": getattr(m, "thinking", None),
                }
            )
        return out

    def list_groq_models(self) -> list[dict[str, Any]]:
        resp = httpx.get(
            f"{GROQ_URL}/models",
            headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise ProviderHTTPError(resp.status_code, resp.text, dict(resp.headers))
        return resp.json().get("data", [])

    # Kept for the Phase 0 spike, which recorded Gemini's listing under this name.
    list_models = list_gemini_models
