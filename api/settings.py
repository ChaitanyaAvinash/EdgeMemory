"""Configuration: loads .env and config/*.yaml, and owns Pacific-time quota dates.

Owns: reading configuration and computing the quota day. Never calls an external API.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DEFAULT_HINDSIGHT_BASE_URL = "https://api.hindsight.vectorize.io"
# Kaveri is in Hyderabad: request and resolution times are IST (no DST).
IST = timezone(timedelta(hours=5, minutes=30))


def _parse_env_value(raw: str) -> str:
    """Value of a KEY=VALUE line. A quoted value ends at its closing quote; anything after is ignored."""
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        return raw[1:end] if end != -1 else raw[1:]
    return raw.split(" #", 1)[0].strip()


def load_env(path: Path | None = None) -> None:
    """Load .env into os.environ without overriding variables already set."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _parse_env_value(value))


@cache
def config(name: str) -> dict[str, Any]:
    """Parsed config/<name>.yaml."""
    return yaml.safe_load((CONFIG_DIR / f"{name}.yaml").read_text(encoding="utf-8")) or {}


def db_path() -> Path:
    load_env()
    return ROOT / os.environ.get("EDGEMEMORY_DB", "data/edgememory.db")


def hindsight_base_url() -> str:
    load_env()
    return os.environ.get("HINDSIGHT_BASE_URL") or DEFAULT_HINDSIGHT_BASE_URL


# --- Pacific time (quota days) -------------------------------------------------------------------
# US Pacific: UTC-8, or UTC-7 from 02:00 local on the second Sunday of March until 02:00 local on the
# first Sunday of November (rule in force since 2007). Written out because Windows ships no tz database
# and tzdata isn't a listed dependency.


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def pacific_offset(at_utc: datetime) -> timedelta:
    at_utc = at_utc.astimezone(UTC)
    year = at_utc.year
    dst_start = datetime.combine(_nth_sunday(year, 3, 2), datetime.min.time(), UTC) + timedelta(hours=10)
    dst_end = datetime.combine(_nth_sunday(year, 11, 1), datetime.min.time(), UTC) + timedelta(hours=9)
    return timedelta(hours=-7) if dst_start <= at_utc < dst_end else timedelta(hours=-8)


def pacific_date(at_utc: datetime | None = None) -> str:
    """The quota day (ISO date) that a moment falls in; quotas reset at midnight Pacific."""
    at_utc = at_utc or datetime.now(UTC)
    return (at_utc.astimezone(UTC) + pacific_offset(at_utc)).date().isoformat()


def next_quota_reset(at_utc: datetime | None = None) -> datetime:
    """UTC moment of the next midnight Pacific."""
    at_utc = (at_utc or datetime.now(UTC)).astimezone(UTC)
    local = at_utc + pacific_offset(at_utc)
    midnight_local = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), UTC)
    # Offset at the reset moment itself (differs from now only on DST-change days).
    guess = midnight_local - pacific_offset(at_utc)
    return midnight_local - pacific_offset(guess)
