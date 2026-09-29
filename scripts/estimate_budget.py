"""Quota budget (SPEC §14.5): projects the week's LLM requests and tokens against the free-tier limits.

Owns: turning config/limits.yaml, the llm_calls log and docs/phase0_results.json into quota-days and a
full-vs-reduced (§14.6) recommendation. Each plan line is priced with the **measured** average tokens of the
roles it uses (extraction, verifier, arm D's composer, arms A and B, narratives), not one blanket figure.
Never calls an API and never guesses a limit: without the limits it prints the plan and says so.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime

from sqlmodel import Session, select

from api import ledger
from api.llm import RateLimiter
from api.settings import ROOT, config, next_quota_reset, pacific_date

# LLM requests per case by role, per arm (SPEC §14.1). Extraction is cached per case and counted once in the
# plan, so arms only pay for their own calls. Normal cases call no verifier, so only A and B pay for them.
ARM_ROLES_EXCEPTION = {
    "A": {"arm_a": 1},
    "B": {"arm_b": 1},
    "C": {"verifier": 1},
    "D": {"verifier": 1, "composer_d": 1},
    "E": {},
    "F": {},
}
ARM_ROLES_NORMAL = {"A": {"arm_a": 1}, "B": {"arm_b": 1}}
NORMAL_SHARE = 10 / 60  # SPEC §13 class mix
SEEDS, CASES, DEV, TEST, TEST_REDUCED = 45, 60, 20, 40, 24
DEV_ALLOWANCE = 400  # development, gates and rehearsals (SPEC §14.5 allowance), priced as verifier calls
DEFAULT_TOKENS = 2000  # a role with no measurement yet


def arm_roles(n_cases: int, arms: dict[str, int]) -> dict[str, float]:
    normal = round(n_cases * NORMAL_SHARE)
    exc = n_cases - normal
    out: dict[str, float] = defaultdict(float)
    for arm, runs in arms.items():
        for role, k in ARM_ROLES_EXCEPTION[arm].items():
            out[role] += runs * k * exc
        for role, k in ARM_ROLES_NORMAL.get(arm, {}).items():
            out[role] += runs * k * normal
    return dict(out)


def plan(reduced: bool) -> list[tuple[str, dict[str, float]]]:
    """Plan lines as {role: requests}. Replays retain seeds without the LLM, so only their cases cost tokens."""
    test_n = TEST_REDUCED if reduced else TEST
    dev_arms = {"A": 1, "B": 1, "C": 1 if reduced else 3, "D": 1 if reduced else 3, "E": 1}
    test_arms = {"A": 1, "B": 1, "C": 1, "D": 1, "E": 1} | ({} if reduced else {"F": 1})
    replay_cases = test_n
    return [
        ("Narratives (60 cases; seeds use the template)", {"narrative": CASES}),
        ("Extraction (cached, once per case)", {"extractor": CASES}),
        ("Dev runs", arm_roles(DEV, dev_arms)),
        ("Test runs", arm_roles(test_n, test_arms)),
        ("Learning curves (C and D; seeds cost no LLM)", arm_roles(replay_cases, {"C": 1, "D": 1})),
        ("Development, gates and rehearsals (allowance)", {"verifier": DEV_ALLOWANCE}),
    ]


def measured() -> dict:
    """Per model: attempts, successes, errors, tokens and latency from llm_calls (cache hits excluded)."""
    with Session(ledger.engine()) as s:
        rows = s.exec(select(ledger.LlmCall).where(ledger.LlmCall.cache_hit == False)).all()  # noqa: E712
    by_model: dict[str, dict] = defaultdict(
        lambda: {"attempts": 0, "ok": 0, "tokens": 0, "latency": [], "429": 0, "5xx": 0}
    )
    for r in rows:
        m = by_model[r.model]
        if r.error.startswith("quota:"):
            continue
        m["attempts"] += 1
        m["429"] += " 429" in r.error[:40]
        m["5xx"] += any(f" {c}" in r.error[:40] for c in ("500", "502", "503", "504"))
        if not r.error:
            m["ok"] += 1
            m["tokens"] += r.input_tokens + r.output_tokens + r.thinking_tokens
            m["latency"].append(r.latency_ms)
    return by_model


def role_tokens(primary: str) -> dict[str, tuple[float, int]]:
    """Measured mean tokens per successful call by role, on real cases (not SPIKE*), on the primary model."""
    with Session(ledger.engine()) as s:
        rows = s.exec(
            select(ledger.LlmCall).where(
                ledger.LlmCall.model == primary,
                ledger.LlmCall.error == "",
                ledger.LlmCall.cache_hit == False,  # noqa: E712
            )
        ).all()
    by: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.case_id and not r.case_id.startswith("SPIKE"):
            by[r.role].append(r.input_tokens + r.output_tokens + r.thinking_tokens)
    return {role: (sum(v) / len(v), len(v)) for role, v in by.items()}


def hindsight_credit(limits: dict, hs: dict) -> None:
    """Hindsight Cloud credit for the week's plan, from published prices and measured retain tokens."""
    price = limits.get("hindsight_cloud") or {}
    retains = [x for x in (hs.get("retain") or {}).get("concise", []) if x.get("usage")]
    print()
    if not price or not retains:
        print("Hindsight credit: run scripts/phase0_spike.py first (needs measured retain tokens).")
        return
    tok = sum(x["usage"]["input_tokens"] for x in retains) / len(retains)
    per_retain = tok * price["retain_per_million_input_tokens"] / 1e6
    per_recall = 2048 * price["recall_per_million_tokens"] / 1e6  # upper bound: max_tokens per recall
    exc_test = TEST - round(TEST * NORMAL_SHARE)
    exc_dev = DEV - round(DEV * NORMAL_SHARE)
    per_case = 2 * per_recall + price["reflect_per_call"]  # SPEC §8.4 recalls + one reflect (planning)
    rows = [
        ("C dev runs x3: seed 45 + recall/reflect", 3 * (SEEDS * per_retain + exc_dev * per_case)),
        ("C test run x1", SEEDS * per_retain + exc_test * per_case),
        ("Replay (hindsight): retain 85 + reflect", (SEEDS + TEST) * per_retain + exc_test * per_case),
        ("Demo resets x15 (37 demo seeds each)", 15 * 37 * per_retain),
        (
            "Development allowance (200 retains, 100 reflects)",
            200 * per_retain + 100 * price["reflect_per_call"],
        ),
    ]
    total = sum(v for _, v in rows)
    print(
        f"Hindsight Cloud credit (USD; measured {tok:.0f} input tokens per retain = ${per_retain:.4f}; "
        f"reflect ${price['reflect_per_call']:.2f}/call; recall <= ${per_recall:.4f}):"
    )
    for name, v in rows:
        print(f"  {name:<52} ${v:>6.2f}")
    print(f"  {'TOTAL':<52} ${total:>6.2f} of ${price['promo_credit_usd']} promo credit")
    print(
        "  Consolidation isn't priced separately on the pricing page (unverified); check the Cloud billing page."
    )


def main() -> int:
    limits = config("limits")
    models = config("models")
    primary = models["roles"]["verifier"]["model"]
    chain = [primary, *[m for m in models.get("fallbacks", []) if m != primary]]
    lim = limits.get("models", {})
    limiter = RateLimiter(limits)

    print("EdgeMemory quota budget (SPEC §14.5)")
    print(
        f"  now: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC · Gemini quota day (Pacific): {pacific_date()}"
        f" · Gemini reset: {next_quota_reset():%Y-%m-%d %H:%M} UTC · Groq: continuous refill"
    )
    print()
    print("Limits (config/limits.yaml, copied by the user from the provider consoles):")
    missing = []
    for m in chain:
        v = lim.get(m) or {}
        print(f"  {m:<22} rpm={v.get('rpm')} tpm={v.get('tpm')} rpd={v.get('rpd')} tpd={v.get('tpd')}")
        missing += [f"{m}.{k}" for k in ("rpm", "tpm", "rpd") if v.get(k) is None]
    print()

    meas = measured()
    overhead: dict[str, float] = {}
    print("Measured so far (llm_calls, excluding cache hits):")
    for m, v in sorted(meas.items()):
        ok = v["ok"]
        lat = sorted(v["latency"])
        overhead[m] = v["attempts"] / ok if ok else float("inf")
        print(
            f"  {m:<22} attempts={v['attempts']} ok={ok} 429s={v['429']} 5xx={v['5xx']}"
            f"  attempts/ok={overhead[m]:.2f}  p50 latency={lat[len(lat) // 2] if lat else 0} ms"
        )
    rt = role_tokens(primary)
    print(
        "Measured tokens per call by role (real cases, "
        + primary
        + "): "
        + ", ".join(f"{r} {t:.0f} (n={n})" for r, (t, n) in sorted(rt.items()))
    )
    print()

    def tok(role: str) -> float:
        return rt[role][0] if role in rt else DEFAULT_TOKENS

    totals: dict[bool, tuple[float, float]] = {}
    for label, reduced in (("FULL benchmark", False), ("REDUCED benchmark (§14.6)", True)):
        rows = plan(reduced)
        print(f"{label}: LLM requests and tokens (SPEC §14.5 counts × measured tokens per role)")
        treq = ttok = 0.0
        for name, roles in rows:
            req = sum(roles.values())
            tks = sum(n * tok(r) for r, n in roles.items())
            treq, ttok = treq + req, ttok + tks
            print(f"  {name:<50} {req:>6.0f} req {tks / 1000:>7.0f}K tokens")
        print(f"  {'TOTAL':<50} {treq:>6.0f} req {ttok / 1000:>7.0f}K tokens")
        print()
        totals[reduced] = (treq, ttok)

    results_path = ROOT / "docs" / "phase0_results.json"
    hindsight_credit(
        limits, json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    )
    print()
    if missing:
        print(f"QUOTA-DAYS: cannot compute; missing limits: {', '.join(missing)} (never guessed).")
        return 2

    # Daily capacity: Groq by tokens (TPD) and requests (RPD); each Gemini fallback by RPD after its overhead.
    g = lim[primary]
    avg_tok = totals[True][1] / totals[True][0] if totals[True][0] else DEFAULT_TOKENS
    gem_req = sum(
        lim[m]["rpd"] / overhead.get(m, 1.0) for m in chain[1:] if overhead.get(m, 1.0) != float("inf")
    )
    tok_cap = float(g.get("tpd") or 10**12) / overhead.get(primary, 1.0) + gem_req * avg_tok
    req_cap = float(g["rpd"]) / overhead.get(primary, 1.0) + gem_req
    print(
        f"Daily capacity: {tok_cap / 1000:.0f}K tokens and {req_cap:.0f} requests "
        f"(Groq TPD {g.get('tpd')} + Gemini fallbacks ~{gem_req:.0f} requests)"
    )

    def days(t: tuple[float, float]) -> int:
        return math.ceil(max(t[0] / req_cap, t[1] / tok_cap))

    full_days, reduced_days = days(totals[False]), days(totals[True])
    print(f"Full: {full_days} quota-days · Reduced (§14.6): {reduced_days} quota-days")
    if full_days <= 4:
        print(f"Recommendation: FULL benchmark ({full_days} quota-days; threshold 4)")
    elif reduced_days <= 4:
        print(
            f"Recommendation: REDUCED (§14.6) benchmark ({reduced_days} quota-days; full needs {full_days})"
        )
    else:
        print(
            f"NEITHER PLAN FITS in 4 quota-days (full {full_days}, reduced {reduced_days}). Models and free tiers "
            "are fixed (CLAUDE.md), so this needs a scope decision before the benchmark runs."
        )
    for m in chain:
        v = lim[m]
        left = f"{m}: {max(0, v['rpd'] - limiter.requests_today(m))} of {v['rpd']} requests"
        if v.get("tpd"):
            left += f", {limiter.tokens_remaining_today(m)} of {v['tpd']} tokens"
        print(f"Available now: {left}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
