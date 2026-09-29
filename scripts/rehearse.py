"""Demo rehearsal (SPEC §18): reset, seed, and run every scripted beat through the API, printing what judges see.

Owns: driving the running API (make api) with data/demo/fixtures.json in order, applying each beat's scripted
decision, and printing the class, review mode, maturity, summary and procedure at every step.
Never: changes the engine or the fixtures. Synthetic data only.

Usage: python -m scripts.rehearse [--no-reset]
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

API = "http://localhost:8000"


def show(v: dict) -> None:
    print(
        f"   {v['request']['id']}: {v['class']} · {v['review_mode']} · {v['maturity'] or '-'} · {v['summary']}"
    )
    for x in v["violations"]:
        c = x["coverage"]
        print(f"     {x['check']} ({x['cause']}) → {c['status']} {c['maturity']} cases {c['case_ids'][:4]}")
    for c in v["interactions"]:
        print(f"     interaction {c['combo']} → {c['verdict']} cases {c['case_ids']}")
    steps = ", ".join(
        f"{s['code']}{'[floor]' if s.get('origin') == 'floor' else ''}" for s in v["procedure"]["steps"]
    )
    print(f"     procedure: {steps or '-'}")
    for r in v["procedure"]["removed_from_union"]:
        print(f"     removed from plain combination: {r['code']} ({', '.join(r['cited_case_ids'])})")
    if v["procedure"]["flags"]:
        print(f"     flags: {v['procedure']['flags']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-reset", action="store_true")
    args = ap.parse_args()
    c = httpx.Client(base_url=API, timeout=900)
    t0 = time.perf_counter()
    if not args.no_reset:
        print("reset:", c.post("/admin/reset").json())
        print("seed:", c.post("/admin/seed").json())
    for beat in c.get("/demo/fixtures").json()["beats"]:
        print(f"\n== {beat['title']} [{beat['claim']}]")
        tb = time.perf_counter()
        r = c.post(f"/demo/beat/{beat['key']}").json()
        print(f"   ({time.perf_counter() - tb:.1f} s to process)")
        if "detail" in r:
            print("   ERROR:", r["detail"])
            return 1
        if "replay" in r:
            rp = r["replay"]
            print(
                f"   replayed {rp['cases']}; clock → {rp['clock']}; consolidated: {rp['consolidation']['consolidated']};"
                f" snapshots {[s['cases'] for s in rp['consolidation']['snapshots']]}"
            )
            continue
        v = r["case"]
        show(v)
        d = beat.get("decision")
        if v["review_mode"] == "step_by_step" and not d:
            d = {
                "action": "confirm",
                "final_steps": [s["code"] for s in v["procedure"]["steps"]],
                "rationale": "",
                "outcome": "",
            }
        elif v["review_mode"] == "one_click" and not d:
            d = {
                "action": "approve",
                "final_steps": [s["code"] for s in v["procedure"]["steps"]],
                "rationale": "",
                "outcome": "",
            }
        if d and v["class"] != "unknown" or (d and d["action"] == "resolve"):
            td = time.perf_counter()
            out = c.post(f"/requests/{v['request']['id']}/decision", json=d).json()
            print(f"   ({time.perf_counter() - td:.1f} s to retain and consolidate)")
            cons = out.get("consolidation") or {}
            print(
                f"   decision {d['action']}: retained {[x['kind'] for x in out.get('retained', [])]};"
                f" consolidated {cons.get('consolidated')}"
            )
    print(f"\nrehearsal done in {time.perf_counter() - t0:.0f} s; quota: {c.get('/quota').json()['models']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
