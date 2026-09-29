"""VectorBackend (arm D) with a deterministic fake embedder: tag filter, cosine order, budget, replace."""

from __future__ import annotations

import asyncio
from datetime import datetime

import numpy as np

from api.memory.backend import MemoryItem
from api.memory.citations import citations
from api.memory.vector_backend import VectorBackend

WORDS = ["bank", "certificate", "budget", "line", "delegate", "callback"]


class BagOfWords:
    def encode(self, texts):
        return np.array([[t.lower().count(w) + 0.01 for w in WORDS] for t in texts], dtype=np.float32)


def item(case_id, text, tags, kind="experience", doc=None):
    return MemoryItem(case_id, kind, text, datetime(2026, 3, 1), tags, doc or case_id, {"case_id": case_id})


def run(c):
    return asyncio.run(c)


def backend(tmp_path):
    b = VectorBackend("kaveri-test-D", BagOfWords(), tmp_path)
    run(b.ensure_bank())
    run(b.retain(item("PR-1", "bank change callback bank", ["step:bank"])))
    run(b.retain(item("PR-2", "certificate expired certificate", ["step:vendor"])))
    run(b.retain(item("PR-3", "bank details changed, callback done", ["step:bank"])))
    run(
        b.retain(
            item("PR-9", "bank and budget line down", ["interaction", "combo:bank+budget"], "interaction")
        )
    )
    return b


def test_tag_filter_is_any_strict(tmp_path):
    r = run(backend(tmp_path).recall("bank callback", ["step:bank"]))
    assert {h.document_id for h in r.hits} == {"PR-1", "PR-3"}
    assert run(backend(tmp_path).recall("anything", ["step:quotes"])).hits == []


def test_cosine_order_and_citation_through_document_id(tmp_path):
    b = backend(tmp_path)
    r = run(b.recall("bank bank callback", ["step:bank", "combo:bank+budget"]))
    assert r.hits[0].document_id == "PR-1"
    cites, _ = citations(r.hits[0], r)
    assert [c.case_id for c in cites] == ["PR-1"]


def test_store_persists_and_replace_by_document_id(tmp_path):
    b = backend(tmp_path)
    run(b.retain(item("PR-1", "certificate only now", ["step:vendor"])))
    again = VectorBackend("kaveri-test-D", BagOfWords(), tmp_path)
    assert len(again.items) == 4 and sum(it["document_id"] == "PR-1" for it in again.items) == 1
    assert run(again.recall("certificate", ["step:bank"])).hits[0].document_id == "PR-3"


def test_no_reflect_and_nothing_to_consolidate(tmp_path):
    b = backend(tmp_path)
    assert run(b.reflect("q", [], {})).supported is False and run(b.wait_consolidated())
    run(b.delete_bank())
    assert not run(b.bank_exists())
