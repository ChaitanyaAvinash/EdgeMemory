"""Record what a provider's own usage page reports, so the rate limiter starts from it (never a guess).

Owns: writing one `quota_calibrations` row. The limiter then replays only calls logged after that moment on top
of the reported usage (continuous refill for Groq). Use it when the local log and the provider disagree, for
example after changing an API key.

Usage: python -m scripts.quota_calibrate --model openai/gpt-oss-120b --requests 41 --tokens 51000
       [--at 2026-09-28T16:23:00Z] [--source "Groq usage page screenshot"]
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlmodel import Session

from api import ledger
from api.llm import RateLimiter
from api.settings import config


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--requests", type=int, required=True, help="requests the provider reports as used")
    ap.add_argument("--tokens", type=int, required=True, help="tokens the provider reports as used")
    ap.add_argument("--at", help="when the reading was taken (ISO 8601, UTC); default now")
    ap.add_argument("--source", default="provider usage page")
    a = ap.parse_args()
    at = datetime.fromisoformat(a.at.replace("Z", "+00:00")) if a.at else datetime.now(UTC)
    with Session(ledger.engine()) as s:
        s.add(
            ledger.QuotaCalibration(
                model=a.model, at=at, requests_used=a.requests, tokens_used=a.tokens, source=a.source
            )
        )
        s.commit()
    lim = RateLimiter(config("limits"))
    print(f"calibrated {a.model} at {at.isoformat()}: {a.requests} requests, {a.tokens} tokens used")
    print(
        f"now available: {lim.remaining_today(a.model)} requests, {lim.tokens_remaining_today(a.model)} tokens"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
