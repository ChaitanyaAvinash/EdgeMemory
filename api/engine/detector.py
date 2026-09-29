"""Detector (SPEC §5.1, §5.2, §8.4): per-violation and interaction recall, batched verification, coverage.

Owns: turning violations into one coverage status each (plus an interaction status):
  1. recall each violation's tag in parallel; recall interaction precedents by combo tag (api-notes D15);
  2. build candidates through citations (every case ID must be in the ledger), dedupe by case, top 5. A
     reviewer override that memory merged into a standard lesson's observation becomes its own candidate, so
     the verifier judges the override's context separately from the lesson it revised;
  3. one verifier LLM call per case (llm.py) over every candidate. If the prompt would pass the provider's
     single-request limit, the lowest-ranked standard candidates are dropped first (never an override, never
     below one per check) and the drop is flagged;
  4. code guards that can only make a verdict more conservative (the LLM proposes, code verifies);
  5. aggregate to one status per violation: best verdict, ties by precedent strength then recency.
Never: thresholds on recall scores (rule 7), reads ground truth, or calls memory except through the backend.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from api.engine.rules import inr
from api.engine.types import (
    VERDICT_RANK,
    Coverage,
    InteractionCoverage,
    RequestFacts,
    VendorRec,
    Violation,
    amount_band,
)
from api.llm import LLM
from api.memory.backend import Hit, MemoryBackend, RecallResult
from api.memory.citations import citations, resolve
from api.settings import CONFIG_DIR, IST, config

PROMPT_VERSION = "verifier-v5"
MAX_REQUEST_TEXT_CHARS = 1500
MAX_HIT_CHARS = 700


# --- ledger view -------------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerCase:
    """What the ledger records about a resolved case (the `lessons` row)."""

    case_id: str
    kind: str
    checks: tuple[str, ...]
    causes: dict
    steps: tuple[str, ...]
    resolved_at: date
    status: str  # active | overridden | predates_policy
    amount: int
    category: str
    urgency: str
    combo: str = ""
    overridden_by: str = ""


@dataclass(frozen=True)
class PolicyRec:
    id: str
    effective_date: date
    tag: str
    text: str


# --- candidates ----------------------------------------------------------------------------------


@dataclass
class Candidate:
    id: str
    hit: Hit
    case_ids: list[str]
    violation: int | None  # index into violations; None for interaction candidates
    combo: str = ""
    policy_ids: list[str] = field(default_factory=list)  # policy memos merged into this memory
    split_from: str = ""  # an override separated from this candidate's shared memory


@dataclass
class CitationStats:
    total: int = 0
    resolved: int = 0
    unresolved: list[str] = field(default_factory=list)

    def add(self, total: int, resolved: int, unresolved: list[str]) -> None:
        self.total += total
        self.resolved += resolved
        self.unresolved += unresolved


def summary(req: RequestFacts, vendor: VendorRec | None) -> str:
    name = f"{vendor.name} ({vendor.id})" if vendor else req.vendor_name_raw
    amt = inr(req.amount) if req.amount is not None else "unknown amount"
    return f"{amt} {req.category.replace('_', ' ')} request from {name}, cost centre {req.cost_centre}, urgency {req.urgency}."


def combos_for(violations: list[Violation]) -> list[str]:
    checks = sorted({v.check for v in violations})
    return ["+".join(c) for n in range(2, len(checks) + 1) for c in itertools.combinations(checks, n)]


def combo_of(hit: Hit) -> str:
    for t in hit.tags:
        if t.startswith("combo:"):
            return t[len("combo:") :]
    return hit.metadata.get("combo", "")


def select_candidates(
    result: RecallResult,
    known_cases: set[str],
    policy_ids: set[str],
    stats: CitationStats,
    prefix: str,
    violation: int | None,
    top: int,
    allowed_combos: set[str] | None = None,
    kinds: dict[str, str] | None = None,
    exclude: str = "",
) -> tuple[list[Candidate], list[Hit]]:
    """Candidates in recall order, deduplicated by case; policy memos returned separately as context.

    With `kinds`, a per-violation memory that merges override cases with standard ones yields two candidates:
    the standard cases, then the overrides (judged on their own context). `exclude` is the request itself: a
    request is never its own precedent, even if an earlier run of it was resolved and remembered."""
    chosen: list[Candidate] = []
    policy_hits: list[Hit] = []
    covered: set[str] = set()
    for hit in result.hits:
        cites, missing = citations(hit, result)
        cites = [c for c in cites if c.case_id != exclude]
        policy_cites = [c for c in cites if c.case_id in policy_ids]
        case_cites = [c for c in cites if c.case_id not in policy_ids]
        ok, bad = resolve(case_cites, known_cases)
        stats.add(len(cites) + len(missing), len(ok) + len(policy_cites), [c.case_id for c in bad] + missing)
        if policy_cites and not case_cites:
            policy_hits.append(hit)
            continue
        case_ids = [c.case_id for c in ok]
        if not case_ids or set(case_ids) <= covered:
            continue
        combo = combo_of(hit)
        if allowed_combos is not None and combo not in allowed_combos:
            continue
        if len(chosen) >= top:
            continue
        before = set(covered)
        covered |= set(case_ids)
        groups = [(case_ids, "")]
        if kinds is not None and violation is not None:
            ov = [c for c in case_ids if kinds.get(c) == "override"]
            rest = [c for c in case_ids if kinds.get(c) != "override"]
            if ov and rest:
                # An override already judged as an earlier candidate isn't split out again.
                new_ov = [c for c in ov if c not in before]
                groups = [(rest, "")] + ([(new_ov, f"{prefix}{len(chosen) + 1}")] if new_ov else [])
        for ids, split_from in groups:
            chosen.append(
                Candidate(
                    f"{prefix}{len(chosen) + 1}",
                    hit,
                    ids,
                    violation,
                    combo,
                    [c.case_id for c in policy_cites],
                    split_from,
                )
            )
    return chosen, policy_hits


def override_context(case_id: str, cases: dict[str, LedgerCase]) -> str:
    """The context an override recorded on the lessons it revised (import_history.override_note, retain)."""
    for c in cases.values():
        for note in c.overridden_by.split(" | "):
            if note.startswith(f"{case_id} "):
                return note
    return ""


# --- verifier ------------------------------------------------------------------------------------


class CandidateVerdict(BaseModel):
    candidate_id: str
    verdict: Literal["yes", "partial", "no"]
    differences: list[str] = Field(description="each at most 12 words; empty if none")
    reason: str = Field(description="at most 20 words")


class VerifierOut(BaseModel):
    verdicts: list[CandidateVerdict]


def verdict_guide() -> str:
    return (CONFIG_DIR / "verdict_guide.md").read_text(encoding="utf-8")


SYSTEM = (
    "You check whether past procurement exception precedents at Kaveri Precision Components (synthetic test "
    "data) apply to a new purchase request. Use only what is written below; the ledger lines are the exact "
    "record.\n"
    "Judge only these five things, using the verdict guide below: (1) the same failed check, (2) the same "
    "cause, (3) the precedent's situation conditions hold for the new request (for example the vendor's "
    "standing, whether a production line is down, the size of an overrun, whether a delegation is valid), "
    "(4) no later policy change affects it, (5) the same amount band and category.\n"
    "A precedent's steps, approvals, callbacks, evidence and outcome describe how that case was resolved. "
    "The new request has not been resolved yet, so it never shows them. Never list a missing step, missing "
    "evidence, a missing callback or an undocumented procedure as a difference, and never lower a verdict "
    "for that reason.\n"
    "Return one verdict for every candidate id, with short differences and a short reason.\n\n"
)


def _case_line(c: LedgerCase, policies: list[PolicyRec], override_note: str = "") -> str:
    causes = ", ".join(f"{k}={v}" for k, v in sorted(c.causes.items()))
    status = c.status
    if c.kind == "override":
        # A reviewer override applies only where the new request shares its context (SPEC §8.7).
        status += "; A REVIEWER OVERRIDE of an earlier lesson, which applies only in its context"
        if override_note:
            status += f": {override_note}"
    if c.overridden_by:
        # SPEC §5.2/§8.7: shown to the verifier, which judges whether the request shares the override's context.
        status += f"; OVERRIDDEN IN CONTEXT: {c.overridden_by}"
    later = [
        p
        for p in policies
        if p.effective_date > c.resolved_at and any(p.tag == f"step:{k}" for k in c.checks)
    ]
    note = "".join(f"; predates policy {p.id} of {p.effective_date.isoformat()}" for p in later)
    return (
        f"{c.case_id}: {inr(c.amount)} ({amount_band(c.amount)}), {c.category}, urgency {c.urgency}, "
        f"causes {causes}, resolved {c.resolved_at.isoformat()}, status {status}{note}; resolved with "
        f"(how it ended, not a condition): {', '.join(c.steps)}"
    )


def _cand_block(cand: Candidate, cases: dict[str, LedgerCase], policies: list[PolicyRec]) -> str:
    if cand.split_from:
        head = (
            f"{cand.id} [reviewer override recorded in the same memory as {cand.split_from}; judge whether the "
            "new request shares the override's context]"
        )
    else:
        text = " ".join(cand.hit.text.split())[:MAX_HIT_CHARS]
        head = f"{cand.id} [{cand.hit.type}{', combination ' + cand.combo if cand.combo else ''}]: {text}"
    lines = [
        f"    ledger {_case_line(cases[cid], policies, override_context(cid, cases))}"
        for cid in cand.case_ids
    ]
    return "\n".join([head, *lines])


def build_prompt(
    req: RequestFacts,
    vendor: VendorRec | None,
    violations: list[Violation],
    cands: list[Candidate],
    icands: list[Candidate],
    cases: dict[str, LedgerCase],
    policies: list[PolicyRec],
    policy_hits: list[Hit],
    request_text: str = "",
) -> str:
    vf = "not in vendor master"
    if vendor:
        vf = (
            f"status {vendor.status}, GST {vendor.gst_status}, {vendor.cert_name} certificate expiry "
            f"{vendor.cert_expiry.isoformat() if vendor.cert_expiry else 'none'}, bank details changed "
            f"{vendor.bank_changed_at.isoformat() if vendor.bank_changed_at else 'never recorded'}, "
            f"sole source {'yes' if vendor.sole_source else 'no'}"
        )
    amt = f"{inr(req.amount)} ({amount_band(req.amount)})" if req.amount is not None else "unknown"
    parts = [
        "NEW REQUEST",
        f"  {req.id}, submitted {req.submitted_on.isoformat()}, amount {amt}, category {req.category}, "
        f"urgency {req.urgency}, cost centre {req.cost_centre}",
        f"  vendor {req.vendor_id or req.vendor_name_raw}: {vf}",
    ]
    if request_text.strip():
        parts += [
            "",
            "REQUEST TEXT (what the requester wrote)",
            request_text.strip()[:MAX_REQUEST_TEXT_CHARS],
        ]
    parts += ["", "FAILED CHECKS"]
    for i, v in enumerate(violations, 1):
        parts.append(f"  V{i} {v.check} (cause: {v.cause}): {v.detail}")
    relevant = {v.tag for v in violations}
    pol = [p for p in policies if p.tag in relevant]
    if pol or policy_hits:
        parts += ["", "POLICY CHANGES ON RECORD"]
        parts += [f"  {p.id} effective {p.effective_date.isoformat()} ({p.tag}): {p.text}" for p in pol]
    for i, _ in enumerate(violations, 1):
        mine = [c for c in cands if c.violation == i - 1]
        parts += ["", f"CANDIDATES FOR V{i}"]
        parts += [_cand_block(c, cases, policies) for c in mine] or ["  (none recalled)"]
    if icands:
        parts += ["", "INTERACTION CANDIDATES (precedents where several checks failed together)"]
        parts += [_cand_block(c, cases, policies) for c in icands]
    ids = [c.id for c in cands + icands]
    parts += [
        "",
        "Remember: how a precedent was resolved is never a condition. Judge the situation only.",
        f"Return exactly one verdict for each of: {', '.join(ids)}.",
    ]
    return "\n".join(parts)


@dataclass
class VerdictRow:
    candidate_id: str
    verdict: str
    differences: list[str]
    reason: str
    guard: str = ""  # which code guard changed the LLM verdict


def apply_guards(
    llm_verdicts: list[CandidateVerdict],
    req: RequestFacts,
    violations: list[Violation],
    cands: list[Candidate],
    cases: dict[str, LedgerCase],
) -> dict[str, VerdictRow]:
    """Code checks on the verifier's verdicts. They only ever lower a verdict (C4: zero false confidence)."""
    by_id = {v.candidate_id: v for v in llm_verdicts}
    out: dict[str, VerdictRow] = {}
    for c in cands:
        v = by_id.get(c.id)
        if v is None:
            out[c.id] = VerdictRow(c.id, "no", [], "no verdict returned by the verifier", "missing_verdict")
            continue
        row = VerdictRow(c.id, v.verdict, list(v.differences), v.reason)
        cited = [cases[cid] for cid in c.case_ids]
        # Cause guard: a precedent needs the same cause for the same check in the ledger (SPEC §5.1 "no").
        checks = (
            [violations[c.violation]]
            if c.violation is not None
            else [x for x in violations if x.check in c.combo.split("+")]
        )
        for vi in checks:
            if not any(k.causes.get(vi.check) == vi.cause for k in cited):
                if row.verdict != "no":
                    row.verdict, row.guard = "no", "cause_mismatch"
                    row.differences.append(f"ledger cause for {vi.check} differs from {vi.cause}")
        # Band/category guard: "yes" needs a cited case in the same amount band and category.
        if row.verdict == "yes" and req.amount is not None:
            if not any(
                amount_band(k.amount) == amount_band(req.amount) and k.category == req.category for k in cited
            ):
                row.verdict, row.guard = "partial", "band_or_category"
                row.differences.append("no cited case in the same amount band and category")
        out[c.id] = row
    return out


# --- aggregation ---------------------------------------------------------------------------------


def _strength(case_ids: list[str], cases: dict[str, LedgerCase]) -> int:
    return len({cid for cid in case_ids if cases[cid].status != "overridden"})


def _recency(case_ids: list[str], cases: dict[str, LedgerCase]) -> date:
    return max((cases[cid].resolved_at for cid in case_ids), default=date.min)


def _best(
    cands: list[Candidate], rows: dict[str, VerdictRow], cases: dict[str, LedgerCase]
) -> Candidate | None:
    if not cands:
        return None
    return max(
        cands,
        key=lambda c: (
            VERDICT_RANK[rows[c.id].verdict],
            _strength(c.case_ids, cases),
            _recency(c.case_ids, cases),
        ),
    )


def aggregate(
    violations: list[Violation],
    cands: list[Candidate],
    icands: list[Candidate],
    rows: dict[str, VerdictRow],
    cases: dict[str, LedgerCase],
    policies: list[PolicyRec],
) -> tuple[list[Coverage], InteractionCoverage | None]:
    coverage = []
    for i, v in enumerate(violations):
        best = _best([c for c in cands if c.violation == i], rows, cases)
        if best is None:
            coverage.append(Coverage(v.check, "no", reason="no precedent recalled for this check"))
            continue
        r = rows[best.id]
        cov = Coverage(
            v.check, r.verdict, list(best.case_ids), _strength(best.case_ids, cases), r.differences, r.reason
        )
        if r.verdict != "no":
            # SPEC §8.8 backstop: flag ANY cited lesson dated before a policy change on the same tag (the
            # verifier can misread dates; an observation may merge pre- and post-policy cases).
            later = [
                p
                for p in policies
                if p.tag == v.tag and any(cases[c].resolved_at < p.effective_date for c in best.case_ids)
            ]
            cov.flags = [f"predates_policy:{p.id}" for p in later]
        coverage.append(cov)
    ibest = _best(icands, rows, cases)
    interaction = None
    if ibest is not None:
        r = rows[ibest.id]
        interaction = InteractionCoverage(
            r.verdict, ibest.combo, list(ibest.case_ids), r.differences, r.reason
        )
    return coverage, interaction


# --- the whole step ------------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """A conservative token estimate for the prompt budget (ledger lines are dense with codes and numbers)."""
    return len(text) * 2 // 7  # about 3.5 characters per token


def trim_one(cands: list[Candidate], icands: list[Candidate], kinds: dict[str, str]) -> Candidate | None:
    """Drop the lowest-ranked standard candidate from the check with the most, keeping one per check; then
    interaction candidates down to one. Overrides are never dropped. Returns the dropped candidate."""
    standard: dict[int, list[Candidate]] = {}
    for c in cands:
        if not any(kinds.get(x) == "override" for x in c.case_ids):
            standard.setdefault(c.violation or 0, []).append(c)
    pick = max(standard, key=lambda v: len(standard[v]), default=None)
    if pick is not None and len(standard[pick]) > 1:
        victim = standard[pick][-1]
        cands.remove(victim)
        return victim
    if len(icands) > 1:
        return icands.pop()
    return None


@dataclass
class Detection:
    coverage: list[Coverage]
    interaction: InteractionCoverage | None
    candidates: list[Candidate]
    interaction_candidates: list[Candidate]
    verdicts: dict[str, VerdictRow]
    citations: CitationStats
    recall_ms: list[int]
    verifier_model: str = ""
    verifier_cache_hit: bool = False
    prompt: str = ""
    trimmed: list[str] = field(default_factory=list)  # candidates dropped to fit the prompt budget


async def detect(
    req: RequestFacts,
    vendor: VendorRec | None,
    violations: list[Violation],
    backend: MemoryBackend,
    llm: LLM,
    cases: dict[str, LedgerCase],
    policies: list[PolicyRec],
    use_cache: bool = True,
    request_text: str = "",
) -> Detection:
    rc = config("memory")["recall"]
    top = int(rc["top_candidates"])
    qts = datetime.combine(req.submitted_on, time(12, 0), IST)
    base = summary(req, vendor)
    queries = [
        backend.recall(f"{v.check} check failed ({v.cause}): {v.detail}. {base}", [v.tag], qts)
        for v in violations
    ]
    combos = combos_for(violations) if len(violations) >= 2 else []
    if combos:
        q = f"{' + '.join(sorted({v.check for v in violations}))} failed together, urgency {req.urgency}. {base}"
        queries.append(backend.recall(q, [f"combo:{c}" for c in combos], qts))
    results = await asyncio.gather(*queries)

    known = set(cases)
    policy_ids = {p.id for p in policies}
    stats = CitationStats()
    cands: list[Candidate] = []
    policy_hits: list[Hit] = []
    kinds = {cid: c.kind for cid, c in cases.items()}
    for i, _ in enumerate(violations):
        chosen, ph = select_candidates(
            results[i], known, policy_ids, stats, f"V{i + 1}-C", i, top, kinds=kinds, exclude=req.id
        )
        cands += chosen
        policy_hits += ph
    icands: list[Candidate] = []
    if combos:
        icands, _ = select_candidates(
            results[-1], known, policy_ids, stats, "I-C", None, top, set(combos), exclude=req.id
        )

    rows: dict[str, VerdictRow] = {}
    prompt = ""
    model, cache_hit = "", False
    trimmed: list[str] = []
    if cands or icands:
        system = SYSTEM + verdict_guide()
        budget = int(rc.get("verifier_max_prompt_tokens", 0))
        prompt = build_prompt(
            req, vendor, violations, cands, icands, cases, policies, policy_hits, request_text
        )
        while budget and estimate_tokens(system + prompt) > budget:
            dropped = trim_one(cands, icands, kinds)
            if dropped is None:
                break
            trimmed.append(dropped.id)
            prompt = build_prompt(
                req, vendor, violations, cands, icands, cases, policies, policy_hits, request_text
            )
        r = await llm.call(
            "verifier",
            prompt,
            VerifierOut,
            PROMPT_VERSION,
            system=system,
            cache_key=f"verify:{req.id}" if use_cache else None,
            case_id=req.id,
        )
        rows = apply_guards(r.parsed.verdicts, req, violations, cands + icands, cases)
        model, cache_hit = r.model, r.cache_hit
    coverage, interaction = aggregate(violations, cands, icands, rows, cases, policies)
    return Detection(
        coverage,
        interaction,
        cands,
        icands,
        rows,
        stats,
        [r.latency_ms for r in results],
        model,
        cache_hit,
        prompt,
        trimmed,
    )
