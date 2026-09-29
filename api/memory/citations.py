"""Citations (SPEC §8.6): recalled memory → the case IDs behind it.

Owns: mapping a fact to its case (document_id, else metadata.case_id) and an observation to its cases (through
source_fact_ids and the response's source facts), stripping `-override-n`, and dropping IDs the ledger
doesn't know. Never guesses a case ID and never reads ground truth.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from api.memory.backend import Hit, RecallResult

log = logging.getLogger("edgememory.citations")
_OVERRIDE = re.compile(r"^(?P<case>.+?)-override-\d+$")


@dataclass(frozen=True)
class Citation:
    case_id: str
    memory_id: str  # the fact that names the case
    via: str  # fact | observation
    from_override: bool


def _case_of(fact: Hit) -> tuple[str, bool] | None:
    raw = fact.document_id or fact.metadata.get("case_id")
    if not raw:
        return None
    m = _OVERRIDE.match(raw)
    return (m.group("case"), True) if m else (raw, False)


def citations(hit: Hit, result: RecallResult) -> tuple[list[Citation], list[str]]:
    """(citations, unresolved source-fact IDs) for one hit. Order-preserving, deduplicated by case."""
    out: list[Citation] = []
    missing: list[str] = []
    seen: set[str] = set()

    def add(fact: Hit, via: str) -> None:
        found = _case_of(fact)
        if found is None:
            missing.append(fact.id)
            return
        case_id, from_override = found
        if case_id not in seen:
            seen.add(case_id)
            out.append(Citation(case_id, fact.id, via, from_override))

    if hit.type == "observation":
        for fid in hit.source_fact_ids:
            fact = result.source_facts.get(fid)
            if fact is None:
                missing.append(fid)  # truncated or absent: never guessed
            else:
                add(fact, "observation")
    else:
        add(hit, "fact")
    return out, missing


def resolve(cites: list[Citation], known_case_ids: set[str]) -> tuple[list[Citation], list[Citation]]:
    """Split citations into (in the ledger, not in the ledger). Unknown ones are logged and must be dropped."""
    ok = [c for c in cites if c.case_id in known_case_ids]
    bad = [c for c in cites if c.case_id not in known_case_ids]
    for c in bad:
        log.warning("citation %s (memory %s) is not in the ledger; dropped", c.case_id, c.memory_id)
    return ok, bad
