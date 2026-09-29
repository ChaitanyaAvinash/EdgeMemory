# Demo runbook (SPEC §18, 3:00)

> **Synthetic data.** Run from **Demo controls** (`/demo`). The beats, requests and pre-filled decisions are in
> `data/demo/fixtures.json`.

## Before going on stage (about 5 minutes; not part of the 3:00)

1. `make api` and `make web`. Open `/demo`.
2. **Reset**, then **Seed** (37 memories, about 3 minutes).
3. Warm up: run one recall. Opening the lesson panel for `step:bank` is enough.
4. **Pre-run the beats that don't depend on learning:**
   - **Hook** (₹4.8L), and **leave it undecided**;
   - **Related party**.
   - Both open instantly on stage, and the staged reveal (`?demo=1`) replays their stages.
5. Check `/quota`: Groq needs roughly 25K tokens for the live beats.

## On stage

| Time | Beat | How | Waits |
|---|---|---|---|
| 0:00–0:20 | Hook | Open the pre-run `PR-DEMO-HOOK` with `?demo=1`. Stop at stage 2, the failed checks | none |
| 0:20–0:40 | First exception | **Run** `e1_first` (unknown) → **Resolve** (pre-filled) → Save | pipeline, then retain and consolidation |
| 0:40–1:05 | Tentative → established | **Run** `e1_second` → confirm step by step. **Run** `replay`, then open the lesson panel (`step:vendor`) and show the diff. **Run** `e1_third`: one-click | three pipeline runs and one replay |
| 1:05–1:40 | Composed | Back to `PR-DEMO-HOOK`: **Replay reveal** through stages 3–7 | none |
| 1:40–2:05 | Override | **Run** `split_1` → **Reject** (pre-filled) → open the lesson panel (`step:duplicate`). **Run** `split_2` | two pipeline runs and one retain |
| 2:05–2:20 | Honest limit | Open the pre-run `PR-DEMO-U1-01` | none |
| 2:20–2:50 | Proof | `/benchmark`, with real counts only | none |
| 2:50–3:00 | Close | Pitch line | — |

**Timing.** The last full rehearsal (29 Sep 2026, after the override fixes) took **278 s end to end**. That
covers reset and seed, all 8 beats and 6 decisions, and used about 15.6K Groq tokens. The measured waits for
the live beats:

| Beat | Pipeline | Retain and consolidate |
|---|---|---|
| `e1_first` | 0.4 s | 6.8 s |
| `e1_second` | 10.4 s | 9.6 s |
| `replay` | 11.7 s | — |
| `e1_third` | 13.7 s | 6.5 s |
| `split_1` | 13.0 s | 6.4 s |
| `split_2` | 15.0 s | — |

That's about 93 s of waiting inside the 105 s live section (0:20–2:05), so talk over every wait. Pre-running
`e1_first` and its resolution saves about 7 s.

The live beats involve about 5 pipeline runs, 1 replay and 3 decisions. **Talk over the "checking, recalling
and composing…" state; don't wait in silence.**

`make rehearse` now prints seconds per beat. Run it once more to see whether the live section fits. If it
doesn't, pre-run `e1_first` and its resolution too. The learning then starts from the lesson panel, which
shows its whole history.

## Fallbacks

- If memory or the LLM fails, the app says "Memory unavailable, escalating to a human" and never shows an
  ungrounded procedure. Switch to the recorded video.
- Groq limits are per minute and per day. Don't rehearse right before the live slot.
