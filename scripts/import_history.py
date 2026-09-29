"""Import resolved exception history into the ledger and memory (SPEC §13; also the customer cold-start path).

Owns: turning history records into (1) ledger rows (`lessons`, `experiences`, `policy_changes`) and (2) memory
items in the SPEC §8.3 template, retained through a MemoryBackend. Reads the CSV format in
data/seed/history.csv (the format a customer exports to) or the JSON record lists used by the gates.
Seed text comes from a fixed template, not an LLM, so seeding costs no LLM quota.
Never: imports the Hindsight client directly (only through api.memory), or reads ground truth.

Usage: python -m scripts.import_history --csv data/seed/history.csv [--demo] [--bank kaveri-demo]
       [--db data/edgememory.db] [--ledger-only]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlmodel import Session

from api import ledger
from api.memory.backend import MemoryBackend
from api.memory.records import document_id, memory_item, render_content, tags_for  # noqa: F401

LIST_FIELDS = ("checks", "steps", "plain_union")


# --- reading -------------------------------------------------------------------------------------


def parse_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """One CSV row → a record. Lists are `A|B`; causes are `check=cause|check=cause`."""
    rec: dict[str, Any] = {k: (v or "").strip() for k, v in row.items()}
    for k in LIST_FIELDS:
        rec[k] = [x for x in rec.get(k, "").split("|") if x]
    rec["causes"] = dict(x.split("=", 1) for x in rec.get("causes", "").split("|") if "=" in x)
    rec["amount"] = int(rec["amount"]) if rec.get("amount") else 0
    rec["demo_bank"] = rec.get("demo_bank", "y").lower() != "n"
    return {k: v for k, v in rec.items() if v not in ("", None) or k in ("amount",)}


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as f:
        return [parse_csv_row(r) for r in csv.DictReader(f)]


# --- writing -------------------------------------------------------------------------------------


def ledger_rows(rec: dict[str, Any]) -> list[Any]:
    if rec["kind"] == "policy_change":
        return [
            ledger.PolicyChange(
                id=rec["case_id"],
                effective_date=date.fromisoformat(rec["effective_date"]),
                tag=rec["tag"],
                text=rec["text"],
            )
        ]
    return [
        ledger.Lesson(
            case_id=rec["case_id"],
            kind=rec["kind"],
            tags=tags_for(rec),
            combo="+".join(sorted(rec["checks"])) if rec["kind"] == "interaction" else "",
            checks=list(rec["checks"]),
            causes=dict(rec["causes"]),
            steps=list(rec["steps"]),
            resolved_at=date.fromisoformat(rec["resolved_at"]),
            status=rec.get("status", "active"),
            amount=int(rec["amount"]),
            category=rec["category"],
            urgency=rec["urgency"],
            vendor_id=rec.get("vendor_id", ""),
        )
    ]


def override_note(rec: dict[str, Any]) -> str:
    """The context an override records on the lessons it overrides (SPEC §8.7 step 3)."""
    return f"{rec['case_id']} on {rec['resolved_at']}: {rec['why']} Reviewer did: {', '.join(rec['steps'])}."


def import_to_ledger(records: list[dict[str, Any]], session: Session) -> None:
    for rec in records:
        for row in ledger_rows(rec):
            session.merge(row)
    session.flush()
    for rec in records:
        if rec["kind"] == "override":
            mark_overridden(
                session, re.findall(r"PR-\d{4}-\d{4}", rec.get("overrides", "")), override_note(rec)
            )
    session.commit()


def mark_overridden(session: Session, case_ids: list[str], note: str) -> list[str]:
    """Record an override's context on each overridden lesson (status stays; context is per case)."""
    marked = []
    for cid in case_ids:
        lesson = session.get(ledger.Lesson, cid)
        if lesson is not None and note not in lesson.overridden_by:
            lesson.overridden_by = (lesson.overridden_by + " | " if lesson.overridden_by else "") + note
            session.add(lesson)
            marked.append(cid)
    return marked


async def import_to_memory(records: list[dict[str, Any]], backend: MemoryBackend, session: Session) -> int:
    """Retain every record (sequentially, in date order) and log it in `experiences`. Returns the count."""
    ordered = sorted(records, key=lambda r: r.get("resolved_at") or r.get("effective_date"))
    for rec in ordered:
        item = memory_item(rec)
        await backend.retain(item)
        session.add(
            ledger.Experience(
                case_id=item.case_id,
                document_id=item.document_id,
                bank_id=backend.bank_id,
                kind=item.kind,
                edge_family=rec.get("family", ""),  # scoring only; never sent to memory or the engine
            )
        )
        session.commit()
    return len(ordered)


async def main() -> None:
    from api.memory.hindsight_backend import HindsightBackend

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=Path("data/seed/history.csv"))
    ap.add_argument("--demo", action="store_true", help="only rows with demo_bank=y (SPEC §18)")
    ap.add_argument("--bank", default="kaveri-demo")
    ap.add_argument("--db", help="ledger database URL (default: the main ledger)")
    ap.add_argument("--ledger-only", action="store_true", help="write the ledger rows, retain nothing")
    args = ap.parse_args()
    records = read_csv(args.csv)
    if args.demo:
        records = [r for r in records if r.get("demo_bank", True)]
    with Session(ledger.engine(args.db)) as s:
        import_to_ledger(records, s)
        print(f"ledger: {len(records)} records")
        if not args.ledger_only:
            backend = HindsightBackend(args.bank)
            await backend.ensure_bank()
            n = await import_to_memory(records, backend, s)
            print(
                f"retained {n} into {args.bank}; consolidation settled: {await backend.wait_consolidated()}"
            )
            await backend.aclose()


if __name__ == "__main__":
    asyncio.run(main())
