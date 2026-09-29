"""Classification (SPEC §5.3): class and novel-combination flag from per-violation coverage.

Owns: the deterministic class decision. Never calls an LLM or memory, and never reads ground truth.
Maturity and review mode (SPEC §5.4, §5.5) arrive in Phase 2.
"""

from __future__ import annotations

from api.engine.types import Classification, Coverage, InteractionCoverage, Violation


def classify(
    violations: list[Violation], coverage: list[Coverage], interaction: InteractionCoverage | None
) -> Classification:
    if not violations:
        return Classification(cls="normal")
    if len(coverage) != len(violations):
        raise ValueError("coverage must hold exactly one status per violation")
    uncovered = [c for c in coverage if c.status == "no"]
    if uncovered:
        # compose what is covered, escalate the rest
        return Classification(cls="unknown", uncovered=uncovered)
    if len(violations) > 1:
        return Classification(
            cls="composed",
            novel_combination=(interaction is None or interaction.status != "yes"),
        )
    return Classification(cls="known" if coverage[0].status == "yes" else "generalized")
