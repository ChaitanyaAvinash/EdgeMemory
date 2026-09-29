"""SQLite ledger: SQLModel tables and deterministic statistics.

Owns: the exact record (SPEC §11). Never decides relevance and never calls an LLM or memory.
The LLM log, quota counters and cache (llm_calls, quota_usage, llm_cache) always live in the main database
(`engine()`), because Groq's rolling 24 h quota is counted from that log. A gate or benchmark run may keep its
case ledger (master data, requests, lessons, ...) in a separate database via `engine(url)`.
Deviations from SPEC §11 (recorded in docs/CHANGELOG.md): `approval_limits` table; `requests` gains
`vendor_name_raw`, `amount_raw`, `quotes_count` and uses `case_class` for the reserved word `class`; `vendors`
gains `cert_name`; `lessons` gains the ledger facts the verifier and guards need (amount, category, urgency,
vendor_id, causes per check).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Session, SQLModel, create_engine, select

from api.settings import db_path


def utcnow() -> datetime:
    return datetime.now(UTC)


class LlmCall(SQLModel, table=True):
    __tablename__ = "llm_calls"
    id: int | None = Field(default=None, primary_key=True)
    role: str
    model: str
    prompt_version: str
    call_style: str = ""
    attempt: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    finish_reason: str = ""
    latency_ms: int = 0
    cache_hit: bool = False
    error: str = ""
    raw_output: str = ""
    case_id: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class QuotaCalibration(SQLModel, table=True):
    """What the provider's own usage page reported at a moment (a user-supplied reading, never guessed).

    The rate limiter starts from the latest reading in the last 24 h instead of replaying older log rows,
    so the local estimate can't drift from the provider's figure (for example after a key change).
    """

    __tablename__ = "quota_calibrations"
    id: int | None = Field(default=None, primary_key=True)
    model: str = Field(index=True)
    at: datetime = Field(default_factory=utcnow)
    requests_used: int
    tokens_used: int
    source: str = ""


class QuotaUsage(SQLModel, table=True):
    """Feeds the daily request counter (per model, per Pacific day)."""

    __tablename__ = "quota_usage"
    __table_args__ = (UniqueConstraint("model", "pacific_date"),)
    id: int | None = Field(default=None, primary_key=True)
    model: str
    pacific_date: str
    requests: int = 0
    tokens: int = 0


class LlmCache(SQLModel, table=True):
    """Output cache, keyed by case ID, content hash, model and prompt version (used for extraction)."""

    __tablename__ = "llm_cache"
    __table_args__ = (UniqueConstraint("role", "cache_key", "content_hash", "model", "prompt_version"),)
    id: int | None = Field(default=None, primary_key=True)
    role: str
    cache_key: str
    content_hash: str
    model: str
    prompt_version: str
    output_json: str
    created_at: datetime = Field(default_factory=utcnow)


def _json(default: Any = None) -> Any:
    return Field(default_factory=lambda: [] if default is None else default, sa_column=Column(JSON))


# --- master data ---------------------------------------------------------------------------------


class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"
    id: str = Field(primary_key=True)
    name: str
    gstin: str
    gst_status: str = "active"  # active | cancelled
    status: str = "active"  # active | blacklisted | inactive
    cert_name: str = ""
    cert_expiry: date | None = None
    bank_changed_at: date | None = None
    sole_source: bool = False
    category: str = ""


class Employee(SQLModel, table=True):
    __tablename__ = "employees"
    id: str = Field(primary_key=True)
    name: str
    role: str
    cost_centre: str
    leave_from: date | None = None
    leave_to: date | None = None


class ApprovalLimit(SQLModel, table=True):
    """Who approves what: the lowest `max_amount` at or above the request amount wins."""

    __tablename__ = "approval_limits"
    id: int | None = Field(default=None, primary_key=True)
    cost_centre: str
    max_amount: int
    approver_id: str


class Delegation(SQLModel, table=True):
    __tablename__ = "delegations"
    id: int | None = Field(default=None, primary_key=True)
    approver_id: str
    delegate_id: str
    max_amount: int
    valid_from: date
    valid_to: date


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"
    id: int | None = Field(default=None, primary_key=True)
    cost_centre: str
    fiscal_year: str
    allocated: int
    spent: int


class PolicyChange(SQLModel, table=True):
    __tablename__ = "policy_changes"
    id: str = Field(primary_key=True)
    effective_date: date
    tag: str
    text: str


# --- cases -------------------------------------------------------------------------------------


class Request(SQLModel, table=True):
    __tablename__ = "requests"
    id: str = Field(primary_key=True)
    submitted_at: datetime
    vendor_id: str | None = None
    vendor_name_raw: str = ""
    amount: int | None = None
    amount_raw: str = ""
    cost_centre: str = ""
    category: str = ""
    urgency: str = ""
    requester_id: str = ""
    quotes_count: int = 0
    justification: str = ""
    email_thread: str = ""
    attachment_text: str = ""
    signals: list = _json()  # extracted signals with source spans (for highlighting)
    dropped_signals: list = _json()  # proposed by the LLM, failed the span check
    case_class: str = ""
    maturity: str = ""
    review_mode: str = ""
    novel_combination: bool = False
    status: str = "open"


class ViolationRow(SQLModel, table=True):
    __tablename__ = "violations"
    id: int | None = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    check: str
    cause: str
    detail: str
    source: str
    source_span: str = ""


class CoverageRow(SQLModel, table=True):
    """One row per verified candidate; is_interaction rows have no violation_id."""

    __tablename__ = "coverage"
    id: int | None = Field(default=None, primary_key=True)
    violation_id: int | None = None
    request_id: str = Field(index=True)
    candidate_id: str = ""
    memory_id: str = ""
    memory_type: str = ""
    memory_text: str = ""
    case_ids: list = _json()
    verdict: str = ""
    differences: list = _json()
    reason: str = ""
    guard: str = ""  # code guard that changed the LLM verdict, if any
    is_interaction: bool = False
    combo: str = ""


class Procedure(SQLModel, table=True):
    __tablename__ = "procedures"
    id: int | None = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    arm: str
    steps: list = _json()
    union_steps: list = _json()
    removed_from_union: list = _json()
    conflicts: list = _json()
    flags: list = _json()
    raw_output: str = ""


class Decision(SQLModel, table=True):
    __tablename__ = "decisions"
    id: int | None = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    reviewer: str
    action: str
    final_steps: list = _json()
    rationale: str = ""
    decided_at: datetime = Field(default_factory=utcnow)


class Lesson(SQLModel, table=True):
    """A resolved case as the ledger records it; memory citations must resolve to one of these."""

    __tablename__ = "lessons"
    case_id: str = Field(primary_key=True)
    kind: str  # experience | interaction | confirmation | override | policy_change
    tags: list = _json()
    combo: str = ""
    checks: list = _json()
    causes: dict = _json({})  # check -> cause
    steps: list = _json()
    resolved_at: date
    status: str = "active"  # active | overridden | predates_policy
    overridden_by: str = ""
    amount: int = 0
    category: str = ""
    urgency: str = ""
    vendor_id: str = ""


class Experience(SQLModel, table=True):
    __tablename__ = "experiences"
    id: int | None = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    document_id: str
    bank_id: str
    retained_at: datetime = Field(default_factory=utcnow)
    kind: str
    edge_family: str = ""  # scoring only; never sent to memory or the engine


class ObservationSnapshot(SQLModel, table=True):
    __tablename__ = "observation_snapshots"
    id: int | None = Field(default=None, primary_key=True)
    bank_id: str
    tag: str
    text: str
    source_case_ids: list = _json()
    fetched_at: datetime = Field(default_factory=utcnow)


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    arm: str
    split: str
    case_id: str
    predicted_class: str = ""
    predicted_steps: list = _json()
    review_mode: str = ""
    flags: list = _json()
    scores: dict = _json({})
    tokens: int = 0
    latency_ms: int = 0


_engines: dict[str, object] = {}


def engine(url: str | None = None):
    """Engine for the ledger (created on first use, with tables)."""
    if url is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    if url not in _engines:
        eng = create_engine(url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(eng)
        _engines[url] = eng
    return _engines[url]


def requests_today(session: Session, model: str, pacific_date: str) -> int:
    row = session.exec(
        select(QuotaUsage).where(QuotaUsage.model == model, QuotaUsage.pacific_date == pacific_date)
    ).first()
    return row.requests if row else 0
