"""citations.py against real Hindsight responses recorded in Phase 0 (tests/fixtures/hindsight)."""

from __future__ import annotations

import json
from pathlib import Path

from api.memory.backend import Hit, RecallResult
from api.memory.citations import citations, resolve
from api.memory.hindsight_backend import parse_recall

FIX = Path(__file__).parent / "fixtures" / "hindsight"


def load(name: str) -> RecallResult:
    return parse_recall(json.loads((FIX / name).read_text(encoding="utf-8")))


def test_observation_resolves_to_both_cases_through_source_facts():
    r = load("recall_violation_vendor.json")
    obs = [h for h in r.hits if h.type == "observation"]
    assert len(obs) == 1 and len(obs[0].source_fact_ids) == 9
    cites, missing = citations(obs[0], r)
    assert [c.case_id for c in cites] == ["PR-2026-0417", "PR-2026-0488"]
    assert all(c.via == "observation" and not c.from_override for c in cites) and missing == []


def test_fact_resolves_through_document_id():
    r = load("recall_violation_bank.json")
    facts = [h for h in r.hits if h.type != "observation"]
    assert facts, "fixture has raw facts"
    cites, _ = citations(facts[0], r)
    assert [(c.case_id, c.via) for c in cites] == [("PR-2026-0233", "fact")]


def test_every_citation_in_the_recorded_recalls_resolves():
    for name in (
        "recall_violation_vendor.json",
        "recall_violation_bank.json",
        "recall_interaction.json",
        "recall_observations_vendor.json",
    ):
        r = load(name)
        for h in r.hits:
            cites, missing = citations(h, r)
            assert cites and not missing, (name, h.id)


def test_interaction_tag_observation_has_no_combo_so_recall_targets_combo_tags():
    # With per_tag scopes, the observation formed under `interaction` carries only that tag (api-notes D15),
    # so it would merge every combination; the detector recalls by `combo:<checks>` tags instead.
    r = load("recall_interaction.json")
    assert [h.tags for h in r.hits] == [["interaction"]]
    assert {c.case_id for h in r.hits for c in citations(h, r)[0]} == {"PR-2026-0312"}


def test_override_suffix_is_stripped_and_flagged():
    fact = Hit(id="f1", text="t", type="world", document_id="PR-2026-0402-override-1")
    cites, _ = citations(fact, RecallResult(hits=[fact]))
    assert (cites[0].case_id, cites[0].from_override) == ("PR-2026-0402", True)


def test_metadata_case_id_used_when_document_id_missing():
    fact = Hit(id="f1", text="t", type="experience", metadata={"case_id": "PR-1"})
    assert citations(fact, RecallResult(hits=[fact]))[0][0].case_id == "PR-1"


def test_truncated_source_facts_are_reported_not_guessed():
    obs = Hit(id="o1", text="t", type="observation", source_fact_ids=["a", "b"])
    a = Hit(id="a", text="t", type="world", document_id="PR-1")
    cites, missing = citations(
        obs, RecallResult(hits=[obs], source_facts={"a": a}, source_facts_truncated=True)
    )
    assert [c.case_id for c in cites] == ["PR-1"] and missing == ["b"]


def test_resolve_drops_ids_not_in_ledger():
    obs_hit = Hit(id="f", text="t", type="world", document_id="PR-9")
    cites, _ = citations(obs_hit, RecallResult(hits=[obs_hit]))
    ok, bad = resolve(cites, {"PR-1"})
    assert ok == [] and [c.case_id for c in bad] == ["PR-9"]
