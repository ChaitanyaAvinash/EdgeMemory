"""Case generator (SPEC §13 step 1): structured case specs → messy intake narratives, through llm.py.

Owns: prompting the narrative role (Groq gpt-oss-120b, effort low, cached per case) with a spec's facts,
and checking in code that every `must_mention` phrase appears verbatim in the generated text (one retry
with feedback, then the case is flagged, never silently accepted). Writes intake forms to
data/cases/<split>/<case_id>.json.
Never: writes ground truth (the data owner does, blind, from the specs; SPEC §13 step 2), sends the spec's
`family` or any label to the LLM, or reads data/ground_truth/. Synthetic data only.

Spec format (list in a JSON file under "specs"):
  case_id, split (dev|test|examples), submitted_at, requester_id, cost_centre, vendor_name, amount_raw,
  quotes_attached, story (the situation, in plain words), must_mention (exact phrases that must appear;
  write each answer-deciding fact in full, e.g. "line 3 is down", not "line 3"),
  email_messages (0-6), certificate_snippet (bool), hinglish (bool), family (scoring only; never sent).
The benchmark specs (data/cases/specs.json) also carry vendor_id, amount, category, urgency, text_signals,
scenario_checks and ledger for the labeller and scripts/check_specs.py; none of them is sent either.

Usage: python -m scripts.generate_cases data/cases/specs.json [--only ID,ID]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from api.llm import LLM, LLMUnavailable
from api.settings import ROOT

PROMPT_VERSION = "narrative-v2"
OUT = ROOT / "data" / "cases"

SYSTEM = """You write realistic, messy synthetic purchase-request text for a fictional Hyderabad manufacturer,
Kaveri Precision Components. Everything you write is synthetic test data.
Write like busy shop-floor and purchase staff: short sentences, some typos, Indian English, and Hinglish
phrases when asked (Hindi or Telugu words mixed into English). Amounts may be written in lakh or with
Indian digit grouping. An email thread is several short messages separated by lines of "---", each starting
with "From: <sender>". A certificate snippet looks like OCR output (odd spacing, a mis-read character or two).
Include every required phrase exactly as given, word for word. State only the facts in the story. Never add
a stopped production line, urgency or a deadline, bank or payment-account changes, a personal or family
connection, or any other problem unless the story says so."""

# Facts that change a case's correct answer. If the generated text mentions one that the story doesn't, the
# case is retried with feedback, then flagged (never silently accepted).
UNSUPPORTED = {
    "a stopped production line": (
        ("line down", "band hai", "stopped", "breakdown", "not running"),
        ("line", "stopped", "down", "breakdown"),
    ),
    "urgency": (
        ("urgent", "asap", "immediately", "jaldi"),
        ("urgent", "today", "deadline", "asap", "stopped"),
    ),
    "a bank-account change": (("new bank", "bank details", "changed our bank", "new account"), ("bank",)),
    "a personal or family connection": (
        ("brother", "sister", "cousin", "relative", "family", "bava", "in-law"),
        ("brother", "sister", "cousin", "relative", "family", "in-law"),
    ),
}


class Narrative(BaseModel):
    justification: str = Field(description="the requester's justification, 1-4 sentences")
    email_thread: str = Field(description='"" if no emails are asked for')
    attachment_text: str = Field(description='certificate or document OCR text, or ""')


def prompt_for(spec: dict[str, Any], feedback: str = "") -> str:
    lines = [
        f"Request: {spec['amount_raw']} to {spec['vendor_name']}, cost centre {spec['cost_centre']}, "
        f"{spec['quotes_attached']} quote(s) attached, submitted {spec['submitted_at'][:10]}.",
        f"Story: {spec['story']}",
        "Required phrases (copy each exactly): " + " | ".join(spec.get("must_mention", [])),
        f"Email thread: {spec.get('email_messages', 0)} messages."
        if spec.get("email_messages")
        else "Email thread: none.",
        "Attachment: a certificate snippet." if spec.get("certificate_snippet") else "Attachment: none.",
        "Use some Hinglish." if spec.get("hinglish") else "Plain Indian English.",
    ]
    if feedback:
        lines.append(f"Fix your previous answer: {feedback}")
    return "\n".join(lines)


def unsupported_facts(spec: dict[str, Any], n: Narrative) -> list[str]:
    """Answer-changing facts present in the text but absent from the story."""
    text = " ".join([n.justification, n.email_thread, n.attachment_text]).casefold()
    story = (spec["story"] + " " + " ".join(spec.get("must_mention", []))).casefold()

    def has(words: tuple[str, ...], s: str) -> bool:
        # Whole words only: "deadline" must not count as "line" (it switched the stopped-line guard off).
        return any(re.search(rf"\b{re.escape(w)}\b", s) for w in words)

    return [
        name
        for name, (in_text, in_story) in UNSUPPORTED.items()
        if has(in_text, text) and not has(in_story, story)
    ]


def missing_phrases(spec: dict[str, Any], n: Narrative) -> list[str]:
    text = " ".join([n.justification, n.email_thread, n.attachment_text]).casefold()
    return [p for p in spec.get("must_mention", []) if p.casefold() not in text]


def intake(spec: dict[str, Any], n: Narrative) -> dict[str, Any]:
    keys = ("submitted_at", "requester_id", "cost_centre", "vendor_name", "amount_raw", "quotes_attached")
    return {"request_id": spec["case_id"], **{k: spec[k] for k in keys}, **n.model_dump()}


async def generate(spec: dict[str, Any], llm: LLM) -> tuple[dict[str, Any] | None, list[str]]:
    feedback = ""
    for attempt in (1, 2):
        r = await llm.call(
            "narrative",
            prompt_for(spec, feedback),
            Narrative,
            PROMPT_VERSION,
            system=SYSTEM,
            cache_key=f"{spec['case_id']}#{attempt}",
            case_id=spec["case_id"],
        )
        missing = missing_phrases(spec, r.parsed)
        invented = unsupported_facts(spec, r.parsed)
        if not missing and not invented:
            return intake(spec, r.parsed), []
        problems = [f"include exactly: {p}" for p in missing] + [
            f"remove {f}; the story doesn't say it" for f in invented
        ]
        feedback = " | ".join(problems)
    return None, problems


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", type=Path)
    ap.add_argument("--only")
    ap.add_argument("--split", choices=["dev", "test", "examples"], help="generate one split only")
    args = ap.parse_args()
    specs = json.loads(args.specs.read_text(encoding="utf-8"))["specs"]
    if args.split:
        specs = [s for s in specs if s["split"] == args.split]
    if args.only:
        keep = set(args.only.split(","))
        specs = [s for s in specs if s["case_id"] in keep]
    llm = LLM()
    failed = []
    for spec in specs:
        try:
            form, missing = await generate(spec, llm)
        except LLMUnavailable as e:
            form, missing = None, [f"LLM unavailable: {e}"]
        if form is None:
            failed.append((spec["case_id"], missing))
            print(f"FLAGGED {spec['case_id']}: missing {missing}", flush=True)
            continue
        out = OUT / spec["split"] / f"{spec['case_id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(form, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}", flush=True)
    print(f"{len(specs) - len(failed)} of {len(specs)} generated; {len(failed)} flagged")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
