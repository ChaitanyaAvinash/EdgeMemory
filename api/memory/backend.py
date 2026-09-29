"""MemoryBackend protocol and shared memory types (CLAUDE.md rule 8).

Owns: the interface every memory implementation provides (HindsightBackend now, VectorBackend for arm D in
Phase 3), and the backend-neutral shapes of what goes in and comes out.
Never: imports the Hindsight client (only hindsight_backend.py does), reads data/ground_truth/, or decides
coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


class MemoryUnavailable(RuntimeError):
    """Recall/retain failed after one retry. Callers show "Memory unavailable, escalating to a human" (rule 11)."""


@dataclass
class MemoryItem:
    """One memory to retain (SPEC §8.3)."""

    case_id: str
    kind: str  # experience | interaction | confirmation | override | policy_change
    content: str
    timestamp: datetime
    tags: list[str]
    document_id: str
    metadata: dict[str, str] = field(default_factory=dict)
    entities: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Hit:
    """One recalled memory: a fact (world/experience) or a consolidated observation."""

    id: str
    text: str
    type: str  # world | experience | observation
    tags: list[str] = field(default_factory=list)
    document_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    source_fact_ids: list[str] = field(default_factory=list)
    occurred_start: str | None = None


@dataclass
class RecallResult:
    hits: list[Hit]
    source_facts: dict[str, Hit] = field(default_factory=dict)  # observation source facts, by fact id
    source_facts_truncated: bool = False
    raw: dict[str, Any] = field(default_factory=dict)  # the backend's own response, for traces and fixtures
    latency_ms: int = 0


@dataclass
class ReflectResult:
    structured: dict[str, Any] | None
    text: str = ""
    based_on_ids: list[str] = field(default_factory=list)  # memory IDs the answer used
    error: str = ""
    latency_ms: int = 0
    supported: bool = True


class MemoryBackend(Protocol):
    bank_id: str

    async def ensure_bank(self) -> None:
        """Create and configure the bank if needed (missions, disposition, directives)."""

    async def retain(self, item: MemoryItem) -> None: ...

    async def recall(
        self, query: str, tags: list[str], query_timestamp: datetime | None = None
    ) -> RecallResult: ...

    async def reflect(self, query: str, tags: list[str], response_schema: dict[str, Any]) -> ReflectResult:
        """Reasoning over the bank with a JSON-schema answer (SPEC §8.5). Arm D's backend returns
        `supported=False` and the pipeline uses an LLM call instead."""

    async def observations(self, tag: str) -> list[dict[str, Any]]:
        """Current consolidated observations under a tag: [{id, text, case_ids}]. Empty for arm D."""

    async def observation_history(self, observation_id: str) -> list[dict[str, Any]]:
        """Earlier versions of an observation, newest last: [{previous_text, changed_at}]."""

    async def wait_consolidated(self) -> bool:
        """Wait until pending consolidation finishes; False on timeout."""

    async def bank_exists(self) -> bool: ...

    async def delete_bank(self) -> None: ...
