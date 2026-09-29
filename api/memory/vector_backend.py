"""VectorBackend (arm D, SPEC §14.1): the same memories as Hindsight, searched by local embeddings and cosine.

Owns: a per-bank local store (data/vector_store/<bank>/items.json + vectors.npy), embedding with a local
sentence-transformers model (never an LLM API), tag filtering with Hindsight's `any_strict` semantics, and
cosine top-k within the same retrieved-context budget as recall (SPEC §14.2 item 4).
Deliberately has no consolidation, observations, temporal reasoning or reflect: overrides and the policy
memo are just more chunks. That is what arm C vs arm D isolates.
Never: calls an LLM, reads ground truth, or thresholds on scores (rule 7).
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from api.memory.backend import Hit, MemoryItem, RecallResult, ReflectResult
from api.settings import ROOT, config

STORE = ROOT / "data" / "vector_store"


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Local embeddings (CLAUDE.md: arm D never uses an LLM API). Loaded on first use."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


_default: SentenceTransformerEmbedder | None = None


def default_embedder() -> SentenceTransformerEmbedder:
    global _default
    if _default is None:
        _default = SentenceTransformerEmbedder(config("memory")["vector"]["model"])
    return _default


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n == 0, 1, n)


class VectorBackend:
    consolidates = False  # arm D: no observations, by design

    def __init__(self, bank_id: str, embedder: Embedder | None = None, root: Path = STORE):
        self.bank_id = bank_id
        self.embedder = embedder or default_embedder()
        self.dir = root / bank_id
        self.items: list[dict[str, Any]] = []
        self.vectors = np.zeros((0, 0), dtype=np.float32)
        self._load()

    # --- storage ---
    def _load(self) -> None:
        f = self.dir / "items.json"
        if f.exists():
            self.items = json.loads(f.read_text(encoding="utf-8"))
            self.vectors = np.load(self.dir / "vectors.npy")

    def _save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "items.json").write_text(json.dumps(self.items, ensure_ascii=False), encoding="utf-8")
        np.save(self.dir / "vectors.npy", self.vectors)

    # --- MemoryBackend ---
    async def bank_exists(self) -> bool:
        return (self.dir / "items.json").exists()

    async def ensure_bank(self) -> None:
        if not await self.bank_exists():
            self._save()

    async def delete_bank(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)
        self.items, self.vectors = [], np.zeros((0, 0), dtype=np.float32)

    async def retain(self, item: MemoryItem) -> None:
        """One chunk per memory; a repeat document_id replaces the old chunk (Hindsight's update_mode replace)."""
        vec = _unit(self.embedder.encode([item.content]))[0]
        keep = [i for i, it in enumerate(self.items) if it["document_id"] != item.document_id]
        self.items = [self.items[i] for i in keep]
        self.vectors = (
            self.vectors[keep] if len(keep) and self.vectors.size else np.zeros((0, vec.shape[0]), np.float32)
        )
        self.items.append(
            {
                "id": uuid.uuid4().hex,
                "text": item.content,
                "type": "world" if item.kind == "policy_change" else "experience",
                "tags": item.tags,
                "document_id": item.document_id,
                "metadata": item.metadata,
                "occurred_start": item.timestamp.isoformat(),
            }
        )
        self.vectors = np.vstack([self.vectors, vec[None, :]]) if self.vectors.size else vec[None, :]
        self._save()

    async def recall(
        self, query: str, tags: list[str] | None, query_timestamp: datetime | None = None
    ) -> RecallResult:
        """Cosine top-k within the recall token budget. `tags=None` searches everything (arm B's plain RAG)."""
        t0 = time.perf_counter()
        budget = int(config("memory")["recall"]["max_tokens"])
        if tags is None:
            idx = list(range(len(self.items)))
        else:
            wanted = set(tags)
            idx = [
                i for i, it in enumerate(self.items) if wanted & set(it["tags"])
            ]  # any_strict: no untagged
        hits: list[Hit] = []
        if idx:
            q = _unit(self.embedder.encode([query]))[0]
            sims = self.vectors[idx] @ q
            used = 0
            for j in np.argsort(-sims):
                it = self.items[idx[j]]
                cost = len(it["text"]) // 4
                if hits and used + cost > budget:
                    break
                used += cost
                hits.append(
                    Hit(
                        it["id"],
                        it["text"],
                        it["type"],
                        list(it["tags"]),
                        it["document_id"],
                        dict(it["metadata"]),
                        [],
                        it["occurred_start"],
                    )
                )
        return RecallResult(
            hits=hits,
            raw={"backend": "vector", "n": len(hits)},
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    async def reflect(self, query: str, tags: list[str], response_schema: dict[str, Any]) -> ReflectResult:
        return ReflectResult(
            None, error="vector backend has no reflect; arm D composes with one LLM call", supported=False
        )

    async def wait_consolidated(self) -> bool:
        return True  # nothing to consolidate

    async def observations(self, tag: str) -> list[dict[str, Any]]:
        return []  # no consolidation in arm D

    async def observation_history(self, observation_id: str) -> list[dict[str, Any]]:
        return []

    async def aclose(self) -> None:
        return None
