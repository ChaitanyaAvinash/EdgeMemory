"""HindsightBackend: the only module that imports the Hindsight client (CLAUDE.md rule 8).

Owns: talking to Hindsight Cloud: bank setup (missions, disposition, directives), retain, tagged recall with
source facts, and waiting for consolidation. Calls are shaped by docs/api-notes.md (D1-D10).
Never: reads data/ground_truth/, computes UI numbers, or decides coverage. Reflect arrives in Phase 2.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any

from hindsight_client import Hindsight

from api.memory.backend import Hit, MemoryItem, MemoryUnavailable, RecallResult, ReflectResult
from api.settings import config, hindsight_base_url, load_env

log = logging.getLogger("edgememory.hindsight")


def make_client(timeout: float = 120.0, max_attempts: int = 2) -> Hindsight:
    """Hindsight Cloud client from .env (HINDSIGHT_API_KEY, HINDSIGHT_BASE_URL)."""
    load_env()
    return Hindsight(
        base_url=hindsight_base_url(),
        api_key=os.environ["HINDSIGHT_API_KEY"],
        timeout=timeout,
        max_attempts=max_attempts,
        user_agent="edgememory/0.0.1",
    )


def _dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dict(obj)


def _hit(d: dict[str, Any]) -> Hit:
    return Hit(
        id=d["id"],
        text=d.get("text", ""),
        type=d.get("type") or d.get("fact_type") or "",
        tags=list(d.get("tags") or []),
        document_id=d.get("document_id"),
        metadata=dict(d.get("metadata") or {}),
        source_fact_ids=list(d.get("source_fact_ids") or []),
        occurred_start=d.get("occurred_start"),
    )


def parse_recall(raw: dict[str, Any]) -> RecallResult:
    """Hindsight recall response (as a dict) → RecallResult. Pure; used on live responses and fixtures."""
    return RecallResult(
        hits=[_hit(r) for r in raw.get("results") or []],
        source_facts={k: _hit(v) for k, v in (raw.get("source_facts") or {}).items()},
        source_facts_truncated=bool(raw.get("source_facts_truncated")),
        raw=raw,
    )


class HindsightBackend:
    consolidates = True  # observations form after retain (SPEC §8.9)

    def __init__(self, bank_id: str, client: Hindsight | None = None):
        self.bank_id = bank_id
        self.cfg = config("memory")
        self.client = client or make_client()

    async def _retry_once(self, what: str, fn):
        """Retry once, then fail visibly (CLAUDE.md rule 11)."""
        for attempt in (1, 2):
            try:
                return await fn()
            except Exception as e:  # noqa: BLE001 - client raises ApiException and aiohttp errors
                log.warning("hindsight %s failed (attempt %d): %s", what, attempt, str(e)[:300])
                if attempt == 2:
                    raise MemoryUnavailable(f"{what}: {type(e).__name__}: {str(e)[:300]}") from e
                await asyncio.sleep(1.0)

    async def bank_exists(self) -> bool:
        banks = _dump(await self._retry_once("list_banks", lambda: self.client.banks.list_banks()))
        return any(b.get("bank_id") == self.bank_id for b in banks.get("banks", []))

    async def ensure_bank(self) -> None:
        c = self.cfg
        await self._retry_once(
            "create_bank",
            lambda: self.client.acreate_bank(
                self.bank_id,
                retain_mission=c["retain_mission"],
                observations_mission=c["observations_mission"],
                reflect_mission=c["reflect_mission"],
                retain_extraction_mode=c["retain_extraction_mode"],
            ),
        )
        d = c["disposition"]
        await self._retry_once(
            "update_bank_config",
            lambda: self.client.aupdate_bank_config(
                self.bank_id,
                disposition_skepticism=d["skepticism"],
                disposition_literalism=d["literalism"],
                disposition_empathy=d["empathy"],
                enable_observations=True,
                enable_auto_consolidation=True,
            ),
        )
        existing = _dump(await self.client.alist_directives(self.bank_id))
        names = {x.get("name") for x in existing.get("items", existing.get("directives", []))}
        for i, dv in enumerate(c["directives"]):
            if dv["name"] not in names:
                await self._retry_once(
                    "create_directive",
                    lambda dv=dv, i=i: self.client.acreate_directive(
                        self.bank_id,
                        name=dv["name"],
                        content=dv["content"],
                        priority=len(c["directives"]) - i,
                    ),
                )

    async def retain(self, item: MemoryItem) -> None:
        payload = {
            "content": item.content,
            "timestamp": item.timestamp,
            "context": self.cfg["context"],
            "document_id": item.document_id,
            "metadata": {k: str(v) for k, v in item.metadata.items()},
            "entities": item.entities or None,
            "resolve_entities": False,
            "tags": item.tags,
            "observation_scopes": self.cfg["observation_scopes"],
        }
        # Sync retain is never retried by the client (it could duplicate); one retry here uses the same
        # document_id with update_mode "replace", so a repeat overwrites rather than duplicates.
        await self._retry_once("retain", lambda: self.client.aretain_batch(self.bank_id, [payload]))

    async def recall(
        self, query: str, tags: list[str], query_timestamp: datetime | None = None
    ) -> RecallResult:
        rc = self.cfg["recall"]
        q = query[: rc["query_max_chars"]]
        t0 = time.perf_counter()
        resp = await self._retry_once(
            "recall",
            lambda: self.client.arecall(
                self.bank_id,
                q,
                types=rc["types"],
                prefer_observations=True,
                include_source_facts=True,
                max_source_facts_tokens=-1,
                budget=rc["budget"],
                max_tokens=rc["max_tokens"],
                tags=tags,
                tags_match="any_strict",
                query_timestamp=query_timestamp.isoformat() if query_timestamp else None,
            ),
        )
        out = parse_recall(_dump(resp))
        out.latency_ms = int((time.perf_counter() - t0) * 1000)
        return out

    async def reflect(self, query: str, tags: list[str], response_schema: dict[str, Any]) -> ReflectResult:
        """SPEC §8.5 with api-notes D4/D7: inlined schema, facts via include_facts, tags_match "any".
        A missing structured_output is retried once; after that the caller takes the §7.1 fallback."""
        rc = self.cfg["reflect"]
        err = ""
        for _ in (1, 2):
            t0 = time.perf_counter()
            resp = _dump(
                await self._retry_once(
                    "reflect",
                    lambda: self.client.areflect(
                        self.bank_id,
                        query,
                        budget=rc["budget"],
                        max_tokens=rc["max_tokens"],
                        response_schema=response_schema,
                        tags=tags,
                        tags_match="any",
                        include_facts=True,
                    ),
                )
            )
            ms = int((time.perf_counter() - t0) * 1000)
            based = [m.get("id") for m in ((resp.get("based_on") or {}).get("memories") or []) if m.get("id")]
            if resp.get("structured_output") is not None:
                return ReflectResult(resp["structured_output"], resp.get("text", ""), based, "", ms)
            err = resp.get("structured_output_error") or "no structured_output"
        return ReflectResult(None, "", [], err, ms)

    async def observations(self, tag: str) -> list[dict[str, Any]]:
        from api.memory.citations import citations

        resp = await self._retry_once(
            "recall_observations",
            lambda: self.client.arecall(
                self.bank_id,
                f"lesson for {tag}",
                types=["observation"],
                tags=[tag],
                tags_match="any_strict",
                include_source_facts=True,
                max_source_facts_tokens=-1,
                max_tokens=self.cfg["recall"]["max_tokens"],
            ),
        )
        r = parse_recall(_dump(resp))
        return [
            {"id": h.id, "text": h.text, "case_ids": [c.case_id for c in citations(h, r)[0]]} for h in r.hits
        ]

    async def observation_history(self, observation_id: str) -> list[dict[str, Any]]:
        raw = await self._retry_once(
            "observation_history",
            lambda: self.client.memory.get_observation_history(self.bank_id, observation_id),
        )
        items = raw if isinstance(raw, list) else _dump(raw).get("history", [])
        return [
            {"previous_text": x.get("previous_text", ""), "changed_at": x.get("changed_at", "")}
            for x in items
        ]

    async def wait_consolidated(self) -> bool:
        cc = self.cfg["consolidation"]
        t0, delay = time.perf_counter(), cc["poll_s"]
        while time.perf_counter() - t0 < cc["timeout_s"]:
            pending = 0
            for status in ("pending", "processing"):
                ops = _dump(
                    await self.client.operations.list_operations(
                        self.bank_id, status=status, type="consolidation"
                    )
                )
                pending += len(ops.get("operations") or ops.get("items") or [])
            if pending == 0:
                return True
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, cc["max_poll_s"])
        return False

    async def delete_bank(self) -> None:
        await self._retry_once("delete_bank", lambda: self.client.adelete_bank(self.bank_id))

    async def aclose(self) -> None:
        await self.client.aclose()
