"""Signal extractor (SPEC §4, §9 step 2): intake text → category, urgency and edge signals with source spans.

Owns: one cached LLM call per request (through llm.py) and the code checks on its output: every signal's
span must appear verbatim in the source it names, or the signal is dropped and flagged; amounts are parsed
and vendors matched in code (normalise.py).
Never: creates violations (rules.py does), computes numbers with the LLM, or reads ground truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from api.engine.normalise import match_vendor, parse_amount
from api.engine.types import RequestFacts, Signal, VendorRec
from api.llm import LLM

PROMPT_VERSION = "extractor-v2"

SYSTEM = """You read one purchase request at Kaveri Precision Components (a synthetic test case) and report
facts that are stated in its text. You never infer, guess or add facts.

category (decide by what the item is for, not by how urgent it is):
- direct_material: raw material or components that become part of the products Kaveri sells to customers
  (castings, bar stock, forgings, housings, fasteners or bearings built into the parts shipped).
- indirect_mro: spares, repair parts and consumables for Kaveri's own machines and production lines
  (motors, pumps, seals, belts, gearboxes, panels, coolant), plus tooling, gauges, PPE and packaging supplies,
  even when a line is down.
- capex: a new machine or equipment that is capitalised as an asset.
- services: labour, contracts, calibration, audits, logistics, consulting, facility work.

urgency: line_down only if the text says a production line or machine is stopped or down now; urgent if
there is a stated deadline or pressure but nothing is stopped; otherwise normal.

amount_mentioned: the rupee amount exactly as written in the text (for example "4.8L" or "Rs 1,20,000"),
or "" if none.

signals (report only if the text states it; otherwise return an empty list):
- bank_change_claimed: the text says the vendor has new or changed bank account details. A mention of a
  bank, payment or invoice alone is not a change.
- related_party: the text says the requester (or their family) has a personal, family or financial
  connection to the vendor.
Rules for signals: a certificate that expires in the future is not a problem; an amount close to an
earlier order is not a signal. For each signal give the source field it came from and a span copied
word for word from that field (at most 25 words)."""


class SignalOut(BaseModel):
    name: Literal["bank_change_claimed", "related_party"]
    source: Literal["justification", "email_thread", "attachment_text"]
    span: str = Field(description="copied word for word from the source field, at most 25 words")


class ExtractionOut(BaseModel):
    category: Literal["direct_material", "indirect_mro", "capex", "services"]
    urgency: Literal["line_down", "urgent", "normal"]
    amount_mentioned: str
    signals: list[SignalOut]


@dataclass
class IntakeForm:
    """What the analyst submits (SPEC §9 step 1). Synthetic data only."""

    request_id: str
    submitted_at: datetime
    requester_id: str
    cost_centre: str
    vendor_name: str
    amount_raw: str
    quotes_attached: int
    justification: str
    email_thread: str = ""
    attachment_text: str = ""


@dataclass
class Extraction:
    facts: RequestFacts
    dropped_signals: list[dict] = field(default_factory=list)  # proposed by the LLM, failed the span check
    model: str = ""
    cache_hit: bool = False


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def span_in_source(span: str, source_text: str) -> bool:
    span = _squash(span.strip(" \"'“”‘’."))
    return bool(span) and span in _squash(source_text)


def user_prompt(form: IntakeForm) -> str:
    return (
        f"justification:\n{form.justification.strip() or '(none)'}\n\n"
        f"email_thread:\n{form.email_thread.strip() or '(none)'}\n\n"
        f"attachment_text:\n{form.attachment_text.strip() or '(none)'}\n"
    )


def build_facts(
    form: IntakeForm, out: ExtractionOut, vendors: dict[str, VendorRec]
) -> tuple[RequestFacts, list[dict]]:
    """Code checks on the LLM's proposal (pure; unit-tested)."""
    sources = {
        "justification": form.justification,
        "email_thread": form.email_thread,
        "attachment_text": form.attachment_text,
    }
    kept: list[Signal] = []
    dropped: list[dict] = []
    for s in out.signals:
        if span_in_source(s.span, sources[s.source]):
            kept.append(Signal(s.name, s.source, s.span.strip()))
        else:
            dropped.append(
                {"name": s.name, "source": s.source, "span": s.span, "why": "span not found in source"}
            )
    amount = parse_amount(form.amount_raw)
    if amount is None:
        amount = parse_amount(out.amount_mentioned)
    facts = RequestFacts(
        id=form.request_id,
        submitted_on=form.submitted_at.date(),
        vendor_id=match_vendor(form.vendor_name, vendors),
        vendor_name_raw=form.vendor_name,
        amount=amount,
        cost_centre=form.cost_centre,
        category=out.category,
        urgency=out.urgency,
        requester_id=form.requester_id,
        quotes_count=form.quotes_attached,
        signals=kept,
    )
    return facts, dropped


async def extract(form: IntakeForm, vendors: dict[str, VendorRec], llm: LLM) -> Extraction:
    """One cached extraction call per request (cache key = request ID + content hash)."""
    r = await llm.call(
        "extractor",
        user_prompt(form),
        ExtractionOut,
        PROMPT_VERSION,
        system=SYSTEM,
        cache_key=form.request_id,
        case_id=form.request_id,
    )
    facts, dropped = build_facts(form, r.parsed, vendors)
    return Extraction(facts, dropped, r.model, r.cache_hit)
