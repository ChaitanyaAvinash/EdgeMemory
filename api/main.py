"""FastAPI routes (SPEC §12) for the demo: the case pipeline, human decisions, lessons, trace, audit, eval.

Owns: HTTP handling and demo state (the demo ledger in data/demo.db, the `kaveri-demo` bank, the demo clock).
The LLM log and quota counters stay in the main ledger database, so `/admin/reset` never touches them.
Never: releases money (no route does), computes numbers outside code, or reads ground truth.
Run: `make api` (uvicorn on :8000).
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from api import ledger, views
from api.engine.extractor import IntakeForm
from api.engine.pipeline import load_master_json, run_case
from api.engine.precedence import library
from api.engine.retain import ACTIONS, retain_decision
from api.llm import LLM
from api.memory.backend import MemoryUnavailable
from api.memory.hindsight_backend import HindsightBackend
from api.metrics import replay_summary
from api.settings import IST, ROOT, config, pacific_date

DEMO_DB = ROOT / "data" / "demo.db"
DEMO_BANK = "kaveri-demo"
MASTER = ROOT / "data" / "master" / "master.json"
SEEDS = ROOT / "data" / "seed" / "history.csv"

app = FastAPI(
    title="EdgeMemory API",
    version="0.1.0",
    description="Exception copilot for procurement. SYNTHETIC DATA. It recommends; a human decides.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict[str, Any] = {"clock": None, "llm": None, "backend": None}


def demo_engine():
    return ledger.engine(f"sqlite:///{DEMO_DB}")


def llm() -> LLM:
    if _state["llm"] is None:
        _state["llm"] = LLM()
    return _state["llm"]


def backend() -> HindsightBackend:
    if _state["backend"] is None:
        _state["backend"] = HindsightBackend(DEMO_BANK)
    return _state["backend"]


def today() -> date:
    return _state["clock"] or datetime.now(IST).date()


# --- models --------------------------------------------------------------------------------------


class RequestIn(BaseModel):
    requester_id: str
    cost_centre: str
    vendor_name: str
    amount_raw: str
    quotes_attached: int = 0
    justification: str
    email_thread: str = ""
    attachment_text: str = ""
    request_id: str | None = None
    submitted_at: datetime | None = None


class DecisionIn(BaseModel):
    action: str  # approve | confirm | edit | reject | resolve
    final_steps: list[str]
    rationale: str = ""
    reviewer: str = "Ananya Rao"
    outcome: str = ""


class ClockIn(BaseModel):
    date: date


# --- requests ------------------------------------------------------------------------------------


def _next_id(s: Session) -> str:
    n = len(s.exec(select(ledger.Request.id).where(ledger.Request.id.startswith("PR-DEMO-"))).all())
    return f"PR-DEMO-{n + 1:04d}"


@app.post("/requests")
async def submit_request(body: RequestIn) -> dict[str, Any]:
    with Session(demo_engine()) as s:
        rid = body.request_id or _next_id(s)
        at = body.submitted_at or datetime.combine(today(), time(10, 0), IST)
        form = IntakeForm(
            rid,
            at if at.tzinfo else at.replace(tzinfo=IST),
            body.requester_id,
            body.cost_centre,
            body.vendor_name,
            body.amount_raw,
            body.quotes_attached,
            body.justification,
            body.email_thread,
            body.attachment_text,
        )
        await run_case(form, s, backend(), llm(), arm="C")
        return views.case_view(s, rid)


@app.get("/requests/{request_id}")
def get_request(request_id: str) -> dict[str, Any]:
    with Session(demo_engine()) as s:
        view = views.case_view(s, request_id)
    if view is None:
        raise HTTPException(404, f"no request {request_id}")
    return view


@app.post("/requests/{request_id}/decision")
async def decide(request_id: str, body: DecisionIn) -> dict[str, Any]:
    if body.action not in ACTIONS:
        raise HTTPException(422, f"action must be one of {ACTIONS}")
    unknown = [c for c in body.final_steps if c not in library()]
    if unknown:
        raise HTTPException(422, f"steps outside the step library: {unknown}")
    with Session(demo_engine()) as s:
        if s.get(ledger.Request, request_id) is None:
            raise HTTPException(404, f"no request {request_id}")
        try:
            out = await retain_decision(
                s,
                backend(),
                request_id,
                body.action,
                body.final_steps,
                body.rationale,
                body.reviewer,
                body.outcome,
                today(),
            )
        except MemoryUnavailable as e:
            raise HTTPException(503, f"Memory unavailable, the decision was not retained: {e}") from e
        return out | {"case": views.case_view(s, request_id)}


@app.get("/queue")
def get_queue() -> dict[str, Any]:
    with Session(demo_engine()) as s:
        return views.queue(s)


# --- memory --------------------------------------------------------------------------------------


@app.get("/lessons")
async def lessons(tag: str) -> dict[str, Any]:
    try:
        obs = await backend().observations(tag)
        for o in obs:
            o["history"] = await backend().observation_history(o["id"])
    except MemoryUnavailable as e:
        raise HTTPException(503, f"Memory unavailable: {e}") from e
    with Session(demo_engine()) as s:
        rows = [x for x in s.exec(select(ledger.Lesson)).all() if tag in x.tags]
        snaps = s.exec(select(ledger.ObservationSnapshot).where(ledger.ObservationSnapshot.tag == tag)).all()
        return {
            "tag": tag,
            "observations": obs,
            "cases": [
                {
                    "case_id": x.case_id,
                    "kind": x.kind,
                    "steps": x.steps,
                    "status": x.status,
                    "resolved_at": x.resolved_at.isoformat(),
                    "overridden_by": x.overridden_by,
                }
                for x in rows
            ],
            "snapshots": [
                {"text": x.text, "source_case_ids": x.source_case_ids, "fetched_at": x.fetched_at.isoformat()}
                for x in snaps
            ],
        }


@app.get("/memory/trace/{request_id}")
def trace(request_id: str) -> dict[str, Any]:
    with Session(demo_engine()) as s:
        view = views.case_view(s, request_id)
    if view is None:
        raise HTTPException(404, f"no request {request_id}")
    return {
        "request_id": request_id,
        "violations": [
            {"check": v["check"], "cause": v["cause"], "coverage": v["coverage"], "recalled": v["candidates"]}
            for v in view["violations"]
        ],
        "interaction_candidates": view["interactions"],
    }


# --- audit, eval, quota --------------------------------------------------------------------------


@app.get("/audit/export.csv", response_class=PlainTextResponse)
def audit_csv() -> str:
    with Session(demo_engine()) as s:
        rows = views.audit_rows(s)
    buf = io.StringIO()
    cols = [
        "request_id",
        "submitted_at",
        "class",
        "review_mode",
        "record",
        "item",
        "detail",
        "citations",
        "note",
        "guard",
    ]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _result_kind(name: str) -> str:
    for prefix in ("gate1", "report", "replay"):
        if name.startswith(prefix):
            return prefix
    return "run"


@app.get("/eval/benchmark")
def eval_benchmark() -> dict[str, Any]:
    """The latest scored report per split (eval/report.py) and the latest test learning curve per backend
    (eval/replay.py). Every number comes from those files or `metrics.replay_summary`; none is computed here."""
    res = ROOT / "eval" / "results"

    def latest(pattern: str) -> tuple[str, dict] | None:
        files = sorted(res.glob(pattern))
        return (files[-1].name, json.loads(files[-1].read_text(encoding="utf-8"))) if files else None

    reports = {}
    for split in ("dev", "test"):
        if found := latest(f"report-{split}-*.json"):
            reports[split] = {"file": found[0], "arms": found[1]["arms"]}
    replays = {}
    for backend in ("hindsight", "vector"):
        if found := latest(f"replay-{backend}-test-*.json"):
            replays[backend] = {
                "file": found[0],
                "curves": found[1]["curves"],
                "summary": replay_summary(found[1]["rows"]),
            }
    return {"reports": reports, "replays": replays}


@app.get("/eval/results")
def eval_results() -> dict[str, Any]:
    out = []
    for f in sorted((ROOT / "eval" / "results").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append(
            {
                "file": f.name,
                "kind": _result_kind(f.name),
                "summary": d.get("summary"),
                "arm": d.get("arm"),
                "rows": d.get("rows") or d.get("cases"),
            }
        )
    return {
        "results": out,
        "note": "Per-case results. Benchmark metrics (M1-M11) are computed by eval/report.py.",
    }


@app.get("/quota")
def quota() -> dict[str, Any]:
    m = llm()
    return {
        "pacific_date": pacific_date(),
        "models": {
            name: {
                "requests_left": m.limiter.remaining_today(name),
                "tokens_left": m.limiter.tokens_remaining_today(name),
                "window": (config("limits")["models"].get(name) or {}).get("daily_window", "pacific_day"),
            }
            for name in [config("models")["roles"]["verifier"]["model"], *config("models")["fallbacks"]]
        },
    }


# --- admin and demo ------------------------------------------------------------------------------


@app.post("/admin/reset")
async def admin_reset() -> dict[str, Any]:
    """Delete and recreate the demo bank and demo ledger (the LLM log is untouched)."""
    b = backend()
    if await b.bank_exists():
        await b.delete_bank()
    url = f"sqlite:///{DEMO_DB}"
    eng = ledger._engines.pop(url, None)
    if eng is not None:
        eng.dispose()
    Path(DEMO_DB).unlink(missing_ok=True)
    with Session(demo_engine()) as s:
        load_master_json(s, json.loads(MASTER.read_text(encoding="utf-8")))
    return {"reset": True, "bank": DEMO_BANK}


@app.post("/admin/seed")
async def admin_seed() -> dict[str, Any]:
    """Seed the demo ledger and bank with the demo_bank=y seeds (SPEC §18): every seed except E1 and the E4 override."""
    from scripts.import_history import import_to_ledger, import_to_memory, read_csv

    records = [r for r in read_csv(SEEDS) if r.get("demo_bank", True)]
    b = backend()
    with Session(demo_engine()) as s:
        load_master_json(s, json.loads(MASTER.read_text(encoding="utf-8")))
        import_to_ledger(records, s)
        retained = 0
        if not await b.bank_exists():
            await b.ensure_bank()
            retained = await import_to_memory(records, b, s)
    settled = await b.wait_consolidated()
    return {"ledger_records": len(records), "retained": retained, "bank": DEMO_BANK, "consolidated": settled}


@app.post("/demo/clock")
def set_clock(body: ClockIn) -> dict[str, str]:
    _state["clock"] = body.date
    return {"date": body.date.isoformat()}


@app.get("/demo/clock")
def get_clock() -> dict[str, str]:
    return {"date": today().isoformat()}


@app.post("/demo/replay")
async def demo_replay(weeks: int = 3) -> dict[str, Any]:
    """Fast-forward scripted resolutions (SPEC §18 beat 3): retain them, snapshot the lessons, move the clock.

    Uses the same import path as seeding (no LLM calls); dates are relative to the demo clock.
    """
    from datetime import timedelta

    from api.engine.retain import take_snapshots
    from scripts.import_history import import_to_ledger, import_to_memory

    start = today()
    script = json.loads((ROOT / "data" / "demo" / "replay.json").read_text(encoding="utf-8"))["records"]
    records = [
        r | {"resolved_at": (start + timedelta(days=int(r["days_after"]))).isoformat()}
        for r in script
        if int(r["days_after"]) <= weeks * 7
    ]
    b = backend()
    with Session(demo_engine()) as s:
        fresh = [r for r in records if s.get(ledger.Lesson, r["case_id"]) is None]
        import_to_ledger(fresh, s)
        n = await import_to_memory(fresh, b, s)
        tags = sorted({f"step:{c}" for r in fresh for c in r["checks"]})
        cons = await take_snapshots(s, b, tags, fresh[-1]["case_id"] if fresh else None)
    _state["clock"] = start + timedelta(weeks=weeks)
    return {
        "replayed": n,
        "cases": [r["case_id"] for r in fresh],
        "clock": _state["clock"].isoformat(),
        "consolidation": cons,
    }


def _fixtures() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "demo" / "fixtures.json").read_text(encoding="utf-8"))


@app.get("/demo/fixtures")
def demo_fixtures() -> dict[str, Any]:
    """The SPEC §18 demo script: ordered beats, their requests and pre-filled decisions."""
    return _fixtures()


@app.post("/demo/beat/{key}")
async def demo_beat(key: str) -> dict[str, Any]:
    """Run one scripted beat: set the clock if the beat has a date, then submit its request (or replay)."""
    beat = next((b for b in _fixtures()["beats"] if b["key"] == key), None)
    if beat is None:
        raise HTTPException(404, f"no demo beat {key}")
    if beat.get("clock"):
        _state["clock"] = date.fromisoformat(beat["clock"])
    if beat.get("replay_weeks"):
        return {"beat": key, "replay": await demo_replay(int(beat["replay_weeks"]))}
    case = await submit_request(RequestIn(**beat["request"]))
    return {"beat": key, "case": case}


@app.get("/boundary-map")
def boundary_map() -> dict[str, str]:
    raise HTTPException(501, "Boundary map is a stretch goal (SPEC §16).")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "synthetic_data": True, "bank": DEMO_BANK}
