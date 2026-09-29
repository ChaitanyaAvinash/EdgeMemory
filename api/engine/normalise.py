"""Deterministic normalisation of extracted strings: rupee amounts and vendor names → ledger IDs.

Owns: turning "4.8L", "₹4,80,000", "Rs. 4,80,000/-" or "480000" into integer rupees (SPEC §4), and matching
a vendor name to a ledger vendor ID. Never calls an LLM; the LLM only extracts the raw string.
"""

from __future__ import annotations

import re

from api.engine.types import VendorRec

_UNITS = {
    "cr": 1_00_00_000,
    "crore": 1_00_00_000,
    "crores": 1_00_00_000,
    "l": 1_00_000,
    "lac": 1_00_000,
    "lacs": 1_00_000,
    "lakh": 1_00_000,
    "lakhs": 1_00_000,
    "k": 1_000,
    "thousand": 1_000,
}
_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k|thousand)?\b", re.IGNORECASE
)


def parse_amount(raw: str | None) -> int | None:
    """First rupee amount in `raw`, as integer rupees; None if there is none."""
    if not raw:
        return None
    text = raw.replace("/-", " ").strip()
    for m in _AMOUNT.finditer(text):
        num, unit = m.group(1).replace(",", ""), (m.group(2) or "").lower()
        if not num or num == ".":
            continue
        value = float(num) * _UNITS.get(unit, 1)
        if value > 0:
            return int(round(value))
    return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def match_vendor(raw: str, vendors: dict[str, VendorRec]) -> str | None:
    """Ledger vendor ID for a name or ID string; exact ID, then exact name, then a unique containment match."""
    if not raw:
        return None
    m = re.search(r"\bV-\d{3}\b", raw, re.IGNORECASE)
    if m and m.group(0).upper() in vendors:
        return m.group(0).upper()
    key = _norm(raw)
    exact = [v.id for v in vendors.values() if _norm(v.name) == key]
    if len(exact) == 1:
        return exact[0]
    contains = [v.id for v in vendors.values() if _norm(v.name) in key or (key and key in _norm(v.name))]
    return contains[0] if len(contains) == 1 else None
