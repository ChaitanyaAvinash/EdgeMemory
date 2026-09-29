"""llm.py: schema subset, enum casing, retries, fallback chain, 429/4xx handling, quotas and cache (offline)."""

from __future__ import annotations

import asyncio
from typing import Literal

import pytest
from pydantic import BaseModel
from sqlmodel import Session, select

from api import ledger, llm
from api.llm import (
    LLM,
    LLMUnavailable,
    ProviderHTTPError,
    RawResponse,
    gemini_schema,
    normalise_enums,
    strict_schema,
)

MODELS = {
    "providers": {"p-model": "groq", "f-model": "gemini", "g-model": "gemini"},
    "fallbacks": ["f-model", "g-model"],
    "retries": 2,
    "gemini_call_style": "interactions",
    "max_output_tokens": 8192,
    "est_output_tokens": 100,
    "roles": {"verifier": {"model": "p-model", "effort": "medium"}},
}


class Step(BaseModel):
    code: Literal["HOLD_PO", "EXPEDITE_PO"]
    cited_case_ids: list[str]


class Out(BaseModel):
    steps: list[Step]
    note: str


class ApiErr(Exception):
    def __init__(self, code: int, details: dict | None = None):
        super().__init__(f"{code}")
        self.code = code
        self.details = details


class FakeLLM(LLM):
    """LLM with a scripted transport: each item is a RawResponse to return or an exception to raise."""

    def __init__(self, script, db_url, limits=None):
        super().__init__(
            client=object(), db_url=db_url, models_cfg=MODELS, limits_cfg=limits or {"models": {}}
        )
        self.script = list(script)
        self.sent: list[tuple[str, str]] = []

    async def _send(self, model, style, prompt, system, schema, effort):
        self.sent.append((model, style))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def ok(
    text='{"steps":[{"code":"hold_po","cited_case_ids":["PR-1"]}],"note":"x"}', finish="stop", headers=None
):
    return RawResponse(
        text=text,
        finish_reason=finish,
        input_tokens=10,
        output_tokens=5,
        thinking_tokens=3,
        headers=headers or {},
    )


def models_sent(f):
    return [m for m, _ in f.sent]


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'ledger.db'}"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", instant)


def run(coro):
    return asyncio.run(coro)


def test_schema_inlines_refs_and_keeps_subset():
    s = gemini_schema(Out)
    assert "$defs" not in str(s) and "$ref" not in str(s)
    step = s["properties"]["steps"]["items"]
    assert step["properties"]["code"]["enum"] == ["HOLD_PO", "EXPEDITE_PO"]
    assert set(step["required"]) == {"code", "cited_case_ids"}


def test_strict_schema_closes_every_object():
    s = strict_schema(gemini_schema(Out))
    assert s["additionalProperties"] is False
    assert s["properties"]["steps"]["items"]["additionalProperties"] is False
    assert "additionalProperties" not in gemini_schema(Out)  # original untouched


def test_schema_rejects_optional_fields():
    class Bad(BaseModel):
        a: str | None = None

    with pytest.raises(ValueError):
        gemini_schema(Bad)


def test_enum_case_normalised_before_validation():
    s = gemini_schema(Out)
    data = normalise_enums(s, {"steps": [{"code": "expedite_po", "cited_case_ids": []}], "note": "n"})
    assert Out.model_validate(data).steps[0].code == "EXPEDITE_PO"


def test_call_styles_follow_provider(db_url):
    f = FakeLLM([], db_url)
    assert f.call_style("p-model") == "groq_chat"
    assert f.call_style("f-model") == "interactions"
    assert f.call_style("f-model", "generate_content") == "generate_content"


def test_success_logs_tokens_and_counts_request(db_url):
    f = FakeLLM([ok()], db_url)
    r = run(f.call("verifier", "q", Out, "v1", case_id="PR-9"))
    assert r.parsed.steps[0].code == "HOLD_PO" and r.model == "p-model"
    with Session(ledger.engine(db_url)) as s:
        row = s.exec(select(ledger.LlmCall)).one()
        assert (row.input_tokens, row.output_tokens, row.thinking_tokens) == (10, 5, 3)
        assert row.raw_output.startswith('{"steps"') and row.finish_reason == "stop"
    assert f.limiter.requests_today("p-model") == 1 and f.limiter.tokens_today("p-model") == 18


def test_two_retries_then_fallback(db_url):
    f = FakeLLM([ApiErr(503), ok("not json"), ok(finish="length"), ok()], db_url)
    r = run(f.call("verifier", "q", Out, "v1"))
    assert f.sent == [("p-model", "groq_chat")] * 3 + [("f-model", "interactions")]
    assert r.model == "f-model"


def test_short_429_waits_and_retries_same_model(db_url):
    err = ProviderHTTPError(429, "{}", {"retry-after": "3"})  # a per-minute (TPM) limit
    f = FakeLLM([err, ok()], db_url)
    r = run(f.call("verifier", "q", Out, "v1"))
    assert models_sent(f) == ["p-model", "p-model"] and r.model == "p-model"
    assert f.limiter.requests_today("p-model") == 2  # a 429 still counts


def test_long_429_moves_to_next_model(db_url):
    err = ProviderHTTPError(429, "{}", {"retry-after": "3600"})  # a daily limit
    f = FakeLLM([err, ok()], db_url)
    r = run(f.call("verifier", "q", Out, "v1"))
    assert models_sent(f) == ["p-model", "f-model"] and r.model == "f-model"


def test_tpm_bucket_follows_provider_headers(db_url):
    h = {"x-ratelimit-remaining-tokens": "100"}
    f = FakeLLM([ok(headers=h)], db_url, {"models": {"p-model": {"tpm": 8000}}})
    run(f.call("verifier", "q", Out, "v1"))
    assert f.limiter._tpm["p-model"].level <= 100.5


def test_4xx_is_not_retried_on_same_model(db_url):
    f = FakeLLM([ProviderHTTPError(400, "bad schema", {}), ok()], db_url)
    run(f.call("verifier", "q", Out, "v1"))
    assert models_sent(f) == ["p-model", "f-model"]


def test_retry_delay_sources():
    assert llm._retry_delay_seconds(ProviderHTTPError(429, "", {"retry-after": "7"})) == 7.0
    assert llm._retry_delay_seconds(ApiErr(429, {"error": {"details": [{"retryDelay": "31s"}]}})) == 31.0
    assert llm._retry_delay_seconds(ApiErr(429, None)) == 10.0


def test_all_fail_raises_unavailable(db_url):
    f = FakeLLM([ApiErr(500)] * 3 + [ok("")] + [ok("", finish="failed")], db_url)
    with pytest.raises(LLMUnavailable):
        run(f.call("verifier", "q", Out, "v1"))


def test_daily_request_quota_moves_to_fallback(db_url):
    f = FakeLLM([ok(), ok()], db_url, {"models": {"p-model": {"rpd": 1}}})
    run(f.call("verifier", "q", Out, "v1"))
    r = run(f.call("verifier", "q2", Out, "v1"))
    assert models_sent(f) == ["p-model", "f-model"] and r.model == "f-model"


def test_daily_token_quota_moves_to_fallback(db_url):
    f = FakeLLM([ok()], db_url, {"models": {"p-model": {"tpd": 50}}})  # estimate alone exceeds 50
    r = run(f.call("verifier", "q", Out, "v1"))
    assert models_sent(f) == ["f-model"] and r.model == "f-model"


def test_provider_headers_raise_request_count(db_url):
    h = {"x-ratelimit-limit-requests": "1000", "x-ratelimit-remaining-requests": "990"}
    f = FakeLLM([ok(headers=h)], db_url)
    run(f.call("verifier", "q", Out, "v1"))
    assert f.limiter.requests_today("p-model") == 10


def test_cache_hit_costs_no_request(db_url):
    f = FakeLLM([ok()], db_url)
    a = run(f.call("verifier", "q", Out, "v1", cache_key="PR-1"))
    b = run(f.call("verifier", "q", Out, "v1", cache_key="PR-1"))
    assert not a.cache_hit and b.cache_hit and len(f.sent) == 1
    c = FakeLLM([ok()], db_url)
    run(c.call("verifier", "q", Out, "v2", cache_key="PR-1"))  # new prompt version → miss
    assert len(c.sent) == 1


def test_rolling_window_counts_last_24h_from_log(db_url):
    limits = {"models": {"p-model": {"tpd": 1000, "daily_window": "rolling_24h"}}}
    f = FakeLLM([ok(), ok()], db_url, limits)
    run(f.call("verifier", "q", Out, "v1"))
    assert f.limiter.tokens_today("p-model") == 18 and f.limiter.requests_today("p-model") == 1
    run(f.call("verifier", "q", Out, "v1"))
    assert f.limiter.tokens_today("p-model") == 36 and models_sent(f) == ["p-model", "p-model"]
    # a pacific-day model with the same log is unaffected by the rolling window
    assert not f.limiter._rolling("f-model")


def test_groq_daily_bucket_refills_continuously(db_url):
    from datetime import timedelta

    from api import ledger as L

    limits = {"models": {"p-model": {"tpd": 86_400, "rpd": 864, "daily_window": "rolling_24h"}}}
    f = FakeLLM([], db_url, limits)
    now = L.utcnow()
    with Session(L.engine(db_url)) as s:
        # 20,000 tokens spent 2 h ago: at 1 token/s refill, 7,200 have come back
        s.add(
            L.LlmCall(
                role="verifier",
                model="p-model",
                prompt_version="v",
                input_tokens=20_000,
                created_at=now - timedelta(hours=2),
            )
        )
        s.commit()
    assert abs(f.limiter.tokens_today("p-model") - 12_800) <= 2
    assert f.limiter.requests_today("p-model") == 0  # 1 request refilled after 100 s


def test_provider_calibration_replaces_older_log_rows(db_url):
    from datetime import timedelta

    from api import ledger as L

    limits = {"models": {"p-model": {"tpd": 86_400, "rpd": 864, "daily_window": "rolling_24h"}}}
    f = FakeLLM([], db_url, limits)
    now = L.utcnow()
    with Session(L.engine(db_url)) as s:
        # an old key's heavy usage in the log, then the provider says only 1,000 tokens are used
        s.add(
            L.LlmCall(
                role="verifier",
                model="p-model",
                prompt_version="v",
                input_tokens=80_000,
                created_at=now - timedelta(hours=3),
            )
        )
        s.add(
            L.QuotaCalibration(
                model="p-model",
                at=now - timedelta(seconds=100),
                requests_used=5,
                tokens_used=1_000,
                source="usage page",
            )
        )
        s.add(
            L.LlmCall(
                role="verifier",
                model="p-model",
                prompt_version="v",
                input_tokens=500,
                created_at=now - timedelta(seconds=50),
            )
        )
        s.commit()
    # 1,000 - 50 s refill (1 token/s) + 500 - 50 s refill = ~1,400
    assert abs(f.limiter.tokens_today("p-model") - 1_400) <= 3
