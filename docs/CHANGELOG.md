# Change log

A record of every change to EdgeMemory's code, config and docs, and every decision, with the reason and who
made it. Newest first. Record each entry as it happens (CLAUDE.md, "How to work").
The detailed API behaviour behind each change is in `docs/api-notes.md`.

Entry format: **date · phase · area**, then what changed, why, and whether it was the user's decision
(**decided by user**) or a verified API behaviour (**verified**).

---

## 2026-09-29 · Submission · `.gitignore` for the public repo (decided by user)

- **`.gitignore` now excludes `.env`** (and any `.env.*` except `.env.example`, plus `web/.env*`). Before, `.env`
  was committed deliberately for a private repo. The user is making the repo public for the hackathon, and a
  committed `.env` would publish the Groq, Gemini and Hindsight keys.
- The keys were never pushed (the folder wasn't a git repo yet), so they don't need rotating.
- A scan of the rest of the project, including every SQLite database, found no other key strings. The databases
  (synthetic data only) are still committed.
- Anyone who clones the repo copies `.env.example` to `.env` and adds their own keys, as the README already says.

## 2026-09-29 · Submission · demo video and voiceover script (requested by user)

- **`demo-video/edgememory-demo.mp4`:** 4:50, 1920×1080, 30 fps, no audio (the user records the voiceover).
  - **Recorded from the running app** with no app code changed. A headless Edge was driven by Playwright,
    screencast frames were piped into ffmpeg, and both tools were installed in a scratch folder, not the
    project.
  - **Overlays** (injected at record time): a visible cursor, a chapter chip, LIVE/RECALL/RETAIN callouts, and
    highlight boxes. A gate on the case page's 1.5 s stage timer paced the reveal.
  - **Waits:** long API waits are cut, and each cut is labelled on screen with its length. The third
    certificate case (one-click) and two loading gaps were cut afterwards to stay under 5 minutes.
- **`demo-video/voiceover-script.md`:** a timecoded narration of about 640 words, matched to the video.
- **Demo state:** the demo bank was reset and seeded, `hook` and `related_party` were pre-run, and then
  e1_first, e1_second, replay, e1_third and split_1 ran live. Reset and seed again before a live demo.
- **Observed on this run:**
  - `split_1` (PR-DEMO-E4-01) came out **unknown and escalated**, not with a link-to-master-PO recommendation.
    The verifier refused the usual lesson because the vendor has a past duplicate-invoice incident. The
    rejection was retained as a separate lesson under `step:duplicate`.
  - On `PR-DEMO-HOOK`, the approver+budget interaction (I1) was rejected, so code dropped
    `ROUTE_NEXT_LEVEL_APPROVER` and restored `ROUTE_DELEGATE`.
  - Both differ from SPEC §18. The script narrates what happened.

## 2026-09-29 · Docs · technical blog article (requested by user)

- **`article.md`** (repo root): a first-person engineering article. Its thread is that several checks failing
  together need their own procedure, not the union of the single-check lessons, learned through per-tag
  Hindsight observations and enforced by the removal rule and the risk floor. It quotes `records.tags_for`,
  the Hindsight recall call, `composer.validate` and `precedence.floor_required`. Its numbers come from
  `docs/benchmark.md` (test split, 24 cases), and it states the override weakness and the small sample.
  Written to the user's brief, which asked for the finished-product framing. **Decided by user.**

---

## 2026-09-29 · Docs · user guide PDF (requested by user), and fixes the screenshots exposed

- **`docs/EdgeMemory-Guide.pdf`** (26 pages, about 2.6 MB), built by `docs/guide/build.py` from
  `docs/guide/guide.src.html`, in plain language. Sections:
  - what EdgeMemory is and what it never does;
  - how it works (five steps, four ideas, the five kinds of case, the safety floor);
  - where to use it (from `docs/adoption.md`, with other domains marked as not built or tested);
  - setup on Windows, with make shortcuts;
  - a tour of every screen;
  - an 8-step guided walkthrough with "you'll see / do" and an "it's working if…" checklist;
  - what to expect: speed from the rehearsal timings, and test results and learning-curve counts copied from
    `report-test-20260928T222947.json` and the replay files;
  - troubleshooting and a glossary.
- **How the PDF is made:**
  - Screenshots are taken from the running app with headless Edge (1440 px, light theme, reduced motion) into
    `docs/guide/img`.
  - Bands are cropped to JPEG with Windows' System.Drawing, and the page is printed to PDF with headless Edge.
    No new packages.
  - The demo was reset and seeded for them, then run through the live API with only the decisions later beats
    depend on (e1_first, e1_second, split_1), so the other screens show their decision buttons. That used about
    16K Groq tokens and one demo seed.
- **Fixes found while taking the screenshots:**
  - **A request cited itself as its own precedent.** `PR-DEMO-HOOK`, re-run after its earlier decision was
    remembered, recalled that decision and the verifier matched it ("approver+bank+budget: precedent applies,
    cases PR-DEMO-HOOK").
    - `select_candidates(..., exclude=req.id)` now drops the request's own ID from every candidate.
    - Test added; 170 pass.
    - The running API server needs a restart to pick this up.
  - **`CountUp` could show a wrong number.** It started at 0, so when the animation didn't run (headless
    capture), the hero showed "0 of 22" for 8 of 22. It now renders the true value until the animation actually
    runs.
  - **Hero:** it was clipped to the content column, so the glow looked like a boxed panel. It's now full-bleed
    (`mx-[calc(50%-50vw)]`), and the body uses `overflow-x: clip` so the sticky header still works. The headline
    is smaller, so the second line no longer wraps.
  - **Dev badge:** Next's on-screen dev indicator is off (`devIndicators: false`), because it showed in
    screenshots and recordings.

## 2026-09-29 · UI · light/dark/system theme switch (requested by user)

- **Before:** the theme followed the operating system only, with no way to choose.
- **`components/theme-toggle.tsx`:** a Light / Dark / System segmented switch in the header.
  - The choice is kept in `localStorage` (`edgememory-theme`). That's a per-viewer convenience; if storage is
    blocked, the choice still applies for the page.
  - "System" follows live changes in the operating system's setting.
  - Where the View Transitions API exists, the new theme spreads as a circle from the click point (a clip-path
    on `::view-transition-new(root)`). With reduced motion, or in other browsers, it switches instantly.
- **No flash:** `lib/theme.ts` holds an inline pre-paint script, rendered in the root layout's `<head>`, that
  sets `data-theme` before first paint.
  - It's a plain module on purpose: a string exported from a `"use client"` file would reach the server layout
    as a client reference, not as text.
  - `<html suppressHydrationWarning>` covers the attribute the script adds.
- **CSS:**
  - Dark tokens now key off `:root[data-theme="dark"]`, with `prefers-color-scheme` kept as the no-JavaScript
    fallback.
  - `color-scheme` is set per theme, so native controls follow it.
  - Tailwind's `dark:` variant follows the chosen theme: `@custom-variant dark (&:where([data-theme="dark"], …))`.
  - Colours transition smoothly.
- **Checked:** `tsc` and `eslint` are clean on the changed files. The pages return 200, the server HTML carries
  the pre-paint script, and the dev log shows no errors.

## 2026-09-29 · UI · editorial redesign with motion (requested by user: "look like awwwards.com")

- **Look:**
  - Warm paper and ink tokens, light and dark, with one vermilion `--signal` colour for what EdgeMemory adds.
  - Instrument Serif display type through `next/font/google`, which is built into Next, so no new package.
  - Film grain in pure CSS.
  - Pill buttons that turn signal-coloured on hover, rounded cards, and pill badges. The risk-floor badge uses
    the signal colour.
- **Motion:** no animation library, so no new dependency (CLAUDE.md). Everything is in `components/motion.tsx`
  and `app/globals.css`, and all of it is off under `prefers-reduced-motion`.
  - `Reveal`: scroll-triggered fade, lift and un-blur, with stagger.
  - `SplitWords`: word-by-word headline rise; `{…}` segments are italic and signal-coloured.
  - `Parallax` and `FadeOnScroll`: the hero's light, grid and outlined word move at different speeds, and the
    hero content fades and blurs out on scroll.
  - `Marquee`: the six checks.
  - `CountUp`: headline numbers count up. The values come from `/eval/benchmark`, never from the page (rule 3).
  - `PageHeader`: shared by every page.
- **Page transitions:**
  - `app/template.tsx` wraps pages in React's `<ViewTransition>`: the old page fades out and lifts, the new one
    fades in from below. This follows Next 16's view-transitions guide in `node_modules/next/dist/docs`.
  - The header is anchored with `viewTransitionName`, and the overlay lets clicks through.
  - Browsers without the View Transitions API swap pages instantly.
- **Header:** sticky glass that tightens on scroll, animated underline on the active link, and a pulsing
  "synthetic data" dot. The footer has a large wordmark and the synthetic-data statement.
- **Home:**
  - A full-height hero with the pitch line and the test benchmark's headline counts for EdgeMemory: false
    confidence, floor violations, and one-click reviews against vector memory.
  - Then the checks marquee, a four-step "how it works" (detect, recall, compose, decide & remember), and the
    queue as editorial rows with a hover sweep.
- **Other pages:**
  - Case view: serif case ID, the summary as a pull-quote, and stages with large numerals.
  - Lessons, New, Demo and Benchmark: the shared header, animated cards, and Benchmark's EdgeMemory column and
    Hindsight line in the signal colour.
- **Checked:**
  - `tsc` is clean.
  - `eslint` is clean on every changed file. Three errors remain in demo/lessons code that this change didn't
    touch (`react-hooks/purity`, `set-state-in-effect`).
  - All six pages return 200, with no errors in the dev log.
  - The dev server's compile worker had crashed from memory pressure (HTTP 500 on the case view), so the
    server was restarted.
- **Not checked:** the result in a real browser. There's no browser available in this session, so the user
  checks it visually.

## 2026-09-29 · Demo · full rehearsal on the fixed code, fifth Groq key

- **New Groq key (supplied by user):**
  - **Verified:** a 152-token probe reported `x-ratelimit-remaining-requests` 999 of 1,000.
  - **Calibrated** at 23:03:16 UTC.
- **Full rehearsal:** `scripts/rehearse.py`, unchanged, driven in-process through the same FastAPI routes, which
  saved starting servers on a low-memory machine.
  - All 8 beats and 6 decisions ran with no error, in 278 s, using about 15.6K tokens.
  - Hook: composed, with I1 applied (ROUTE_NEXT_LEVEL_APPROVER in place of ROUTE_DELEGATE) and payment held
    until the bank callback.
  - E1: unknown, then tentative, then established with one click.
  - Override: `split_2` recommends REJECT_REQUEST + ESCALATE_AUDIT after the reject.
  - Related party: escalated, with DECLARE_CONFLICT_OF_INTEREST added by the floor.
- **Fix found by the rehearsal:** `PR-DEMO-E1-01`, with nothing covered, was flagged `empty_procedure`, which
  would have made the case view claim "a precedent matched".
  - The flag now needs at least one covered check.
  - Test added; 169 pass.
- The per-beat timings are in `docs/demo-runbook.md`. The demo ledger and bank hold the rehearsal's state, so
  run Reset and Seed before recording (runbook step 2).

## 2026-09-29 · Phase 5 · override fixes and verifier prompt budget (decided by user: "fix them")

**The test split was not re-run.** The published test numbers are from the code before these fixes
(`docs/benchmark.md` says so).

- **`api/engine/detector.py`, verifier-v5:**
  - **Override split:** `select_candidates(..., kinds=)` splits a per-violation memory that merges override
    cases with standard ones into two candidates. The override candidate carries `split_from`.
    - An override already judged as an earlier candidate isn't split out again.
    - Interaction candidates are never split.
  - **Override context in the prompt:** an override case's ledger line reads "A REVIEWER OVERRIDE of an earlier
    lesson, which applies only in its context", followed by the note its reviewer recorded
    (`override_context()`).
  - **Prompt budget:**
    - If the estimated verifier prompt (system prompt included, about 3.5 characters a token) exceeds
      `recall.verifier_max_prompt_tokens` (5,500 in `config/memory.yaml`), `trim_one()` drops the lowest-ranked
      standard candidate from the check with the most.
    - It never drops an override, never goes below one per check, and trims interaction candidates to one
      after that.
    - The pipeline flags `verifier_candidates_trimmed:<ids>`.
    - 5,500 is below the largest accepted verifier prompt measured (5,572 tokens). Groq counted 8,353 and 8,500
      "requested" on the two 413s.
- **`api/engine/composer.py`:**
  - `single_lesson` builds the lesson from verified overrides when any are present, because an override revises
    the lesson in its context.
  - An exception case whose final procedure is empty is flagged `empty_procedure`, and `review_mode` escalates it.
- **UI:** the case view explains an `empty_procedure` escalation in plain words.
- **Tests:** 7 new tests (split, context in the prompt, no double split, trim rule, override lesson, override
  precedence, empty-procedure escalation). 168 pass.
- **Dev check** (`run-bench-dev-C-dev4ovr.json`, the 4 dev cases whose checks have override seeds: DEV-005,
  014, 015, 018):
  - Classes and steps were identical to `dev3` and to the ground truth.
  - The split fired in all four, and the verifier said "no" to each override whose context didn't apply.
  - The `kaveri-dev-c-dev3` bank no longer existed, so it was re-seeded identically.
- **Demo check** (in-process, same routes as the UI): reset and seed, clock set to 2026-10-20 (where the full
  sequence puts these beats), then `split_1` and `split_2`.
  - `split_1` is generalized, recommends LINK_MASTER_PO + ALLOW_SPLIT_DELIVERY, and is rejected; the override is
    retained and consolidated.
  - `split_2` is **known, tentative: REJECT_REQUEST + ESCALATE_AUDIT, citing PR-DEMO-E4-01**.
  - An earlier attempt at the reset clock (29 Sep, before the 6 Oct order) didn't fire the duplicate check. That
    was a test-setup error, and the demo was reset again afterwards.
  - The demo ledger and bank now hold those two beats. Run `make reset seed` before recording.

## 2026-09-29 · Phase 5 · benchmark page shows the results

- **API:**
  - New `GET /eval/benchmark` returns the latest scored report per split (`report-<split>-*.json`), plus the
    latest test learning curve per backend with a summary from `metrics.replay_summary`, which is new and
    unit-tested. The endpoint computes no numbers itself (rule 3).
  - `GET /eval/results` now labels files `gate1`, `report`, `replay` or `run`. Before, report and replay files
    were labelled `run`, and the replay's rows, which have no steps, would have crashed the page's per-case
    table.
- **`web/app/benchmark`:**
  - an arm comparison table for test and for dev, with EdgeMemory's column highlighted and "lower/higher is
    better" on each measure;
  - learning-curve charts (Recharts) of Hindsight against the vector store: one-click reviews in the last 10
    exception cases, and running reviewer effort per case;
  - the G1 table, and per-case run files as collapsible sections;
  - plain-language notes on where EdgeMemory is behind, the dev split's tuning caveat, and the 413
    infrastructure escalations.
- **Glossary:** added false confidence, interaction, override, one-click review and learning curve.
- **Checked:** `tsc` and `eslint` are clean, and the page compiles on the running dev server. It wasn't viewed
  with data, because the API server isn't running. A full `next build` was skipped while the dev server holds
  `.next`.

## 2026-09-29 · Phase 5 · test benchmark complete (A–E), results published

- Arms A and B finished at 22:29 UTC: 24 of 24 each, all on `openai/gpt-oss-120b`, with no
  `llm_unavailable` rows. All six test jobs are done.
- Final report `eval/results/report-test-20260928T222947.json`. The table, per-case lists and the check against
  the pre-run expectations are in `docs/benchmark.md` ("Test results"); a summary is in the README.
- **Expectations that held:**
  - C beats E on interaction cases (3 of 8 exact against 0 of 8) and on outdated-lesson use (0 of 3 against 3
    of 3).
  - C beats D on outdated-lesson use (0 of 3 against 2 of 3) and on learning speed (8 of 22 one-click against
    4 of 22).
- **Didn't hold:**
  - C and D both score 0 of 3 on post-override correctness.
  - B beats C on post-override correctness (3 of 3), on known-case F1 (0.971 against 0.571) and on macro F1
    (0.843 against 0.798).
  - B has 1 of 5 false confidence and 4 of 9 floor violations; C has 0 of each.
- **Root cause of the override misses, from C's run ledger (diagnosis only; nothing changed):**
  - **TEST-013 and TEST-027:** the verifier correctly said "no" to the original lesson, because the override
    condition applies. The override's own resolution wasn't recalled as a separate candidate, so the case was
    escalated.
  - **TEST-020:** the verifier said "yes" to the override precedent PR-2026-0735. But `composer.single_lesson`
    uses only experience and confirmation cases, so the override-only lesson had no steps. The result was an
    empty union and an empty procedure with no flag. That's a mismatch with `verified_cases`, which deliberately
    admits override-only candidates judged "yes".
- README "Results" and "Limits" were updated. `benchmark.md`'s quota section now states that the reduced plan
  was used, when the runs happened, and that four user-supplied keys were used.

## 2026-09-29 · Quota · fourth Groq key (supplied by user)

- **Verified:** a 152-token probe reported `x-ratelimit-remaining-requests` 999 of 1,000.
- **Calibrated** at 22:10:29 UTC to 1 request and 152 tokens. The token figure is inferred.
- The driver's quota wait was ended early, and arm A started at 22:10:34 UTC.

## 2026-09-29 · Phase 5 · learning curves complete (Hindsight and vector)

- `replay-hindsight-test-test1.json` and `replay-vector-test-test1.json`: 24 of 24 cases each (22 exception
  cases).

| Measure | Hindsight (C) | Vector (D) |
|---|---|---|
| False confidence | 0 of 22 | 0 of 22 |
| One-click reviews | 8 of 22 | 4 of 22 |
| Mean reviewer effort per case | 2.82 | 3.77 |
| Escalations | 5 | 6 |
| Classes correct | 20 of 24 | 19 of 24 |

- **Maturity (C3), Hindsight:**
  - The I2 lesson went from tentative (TEST-015, after TEST-011) to established (TEST-030).
  - After one resolved related-party case and one resolved GST case, the follow-ups (TEST-036, TEST-037) got
    tentative step-by-step procedures instead of an escalation.
- **Verified provider behaviour, HTTP 413 "Request too large":**
  - Groq rejects a single request above the per-minute token limit (8,000).
  - In a replay, memory grows, so a case's batched verifier prompt grows with it. Two verifier calls went over:
    TEST-032 in the Hindsight replay and TEST-019 in the vector replay.
  - Both Gemini fallbacks were out of daily quota, so each case was escalated as "LLM unavailable". That's safe
    (fail visibly), but it's an infrastructure escalation, not a judgement, and it's disclosed in the results.
    One case per backend was affected.
  - The benchmark arms, which use seed-only memory, never hit it.
  - Recorded in `docs/api-notes.md`. A fix, either capping candidates per check or splitting the verifier call
    when the prompt is too large, changes the verifier batching decision, so it's for the user.
- Token use: 46 replay verifier calls averaged about 3,400 tokens, above dev's ~2,500, because memory grew.
- Claude Code reported the driver as stopped for low memory (about 1.2 GB free of 15.5 GB), but the driver and
  the vector replay kept running and finished. The driver now waits for quota for arm A.

## 2026-09-29 · Quota · another new Groq key (supplied by user)

- **Verified:** a 151-token probe reported `x-ratelimit-remaining-requests` 999 of 1,000.
- **Calibrated** at 20:54:47 UTC to 1 request and 151 tokens. The token figure is inferred.
- The driver's 15-minute quota wait was ended early, and the Hindsight replay (RH) started at 20:54:58 UTC.

## 2026-09-29 · Phase 5 · arm D complete on the test set

- `run-bench-test-D-test1.json`: 24 of 24 cases, all on `openai/gpt-oss-120b`, with no `llm_unavailable` rows.
- Scored in `eval/results/report-test-20260928T205133.json`.
- C and D tie on:
  - false confidence (0 of 5),
  - floor violations (0 of 9),
  - classes (21 of 24),
  - exact interaction procedures (3 of 8),
  - post-override correctness (0 of 3),
  - procedure F1 (0.798 against 0.797).
- C is ahead on:
  - outdated-lesson use: 0 of 3, against D's 2 of 3;
  - review effort per 10 cases: 28.3 against 39.6;
  - tokens per case: 3,699 against 6,931.
- D is ahead on:
  - unnecessary escalations: 1 of 17, against C's 3 of 17;
  - estimated minutes per 10 exception cases: 166.4 against 189.5, because each escalation costs 40 minutes.

## 2026-09-29 · Phase 5 · arms C and E complete on the test set

- `run-bench-test-C-test1.json`: 24 of 24 cases, all on `openai/gpt-oss-120b`, with no `llm_unavailable` rows.
- Scored against the frozen ground truth: `eval/results/report-test-20260928T202819.json`. The results go into
  `docs/benchmark.md` once every arm is in.
- **Defect found on the test run (TEST-020):** C classed it `known` but produced an **empty step list**, with no
  flag and no escalation. That breaks "fail visibly".
  - It's recorded as a test result, not fixed and re-run: the test split runs once per arm (CLAUDE.md rule 10).
  - Any product fix is a separate change and needs its own dev check.

## 2026-09-29 · Phase 5 · test ground truth frozen, replay fixes, new Groq key

- **Test ground truth frozen as-is** in `data/labelling/FROZEN.json` (SHA-256 `8a9ae646…`). No test prediction
  had been scored or shown to the user.
  - The file may be re-frozen only if the user changes a label *before* any test score is shown.
- **The labeller's 7 items** (`test_labeller_notes.md`): all follow the labelling guide, so none changes a label.
  1. **TEST-037 has no `REQUEST_RENEWED_CERT`.**
     - `rules.check_vendor` takes the most severe problem as the cause (`gst_cancelled`).
     - The guide gives an uncovered check its family row's human answer (U2), and DEV-011 was labelled the
       same way.
     - U2's `REQUEST_MORE_INFO` covers the certificate question.
  2. **TEST-036 keeps `COLLECT_QUOTES`.** It's part of the U1 answer, and matches DEV-010 and DEV-019.
  3. **TEST-024 is `unknown`.** No blacklisted precedent exists, and the class rule decides. `REJECT_REQUEST`
     comes from policy.md §2.
  4. **TEST-007 is `generalized`.** Its precedents are in a different category (capex), which the verdict guide
     makes a partial match.
  5. **TEST-015, 030 and 032 are novel against the seed history.** That's correct for the benchmark arms,
     which retain nothing. The replay doesn't score M5, but the point exposed a replay bug (below).
  6. **Adversarial:** used only for reporting.
  7. **One labeller, from the model family that builds the system.** This is stated as a limit in
     `docs/benchmark.md`. A human spot-check of these items is recommended.
- **Reduced-set groups vs labels:** `test_reduced.json`'s groups came from spec families before labelling.
  Where a label differs (TEST-024, TEST-007), the frozen label governs scoring.
- **Fix, `eval/replay.py`:**
  - **False confidence is now relative to the replay.** The ground truth's `uncovered_checks` are relative to
    the seed history, but a replay retains each resolved case. So correctly reusing TEST-016's related-party
    resolution on TEST-036 would have counted as false confidence.
    - `still_uncovered()` drops a check once an earlier replayed case with the same check and cause was
      resolved.
    - Each row records `uncovered_in_replay`, and a unit test was added.
  - **Labelled cases only:** before, the replay walked all 40 cases and would have retained empty resolutions
    for the 16 unlabelled ones.
  - **Resume:** `--run ID --resume` works like `run_arms`: it skips processed events, saves after every event,
    and stops cleanly on quota. The log no longer prints predictions.
- **Two drivers were running.** The driver Claude Code reported as stopped for low memory was still alive
  beside the restarted one. Both were stopped before either resumed (C still at 11 of 24).
  - `eval/drive_test.sh` now takes a lock directory (`data/runs/drive_test.lock`).
  - It also runs the replays, in the order C, D, RH (Hindsight replay), RV (vector replay), A, B.
- **New Groq key (supplied by user):**
  - **Verified:** a 155-token probe reported `x-ratelimit-remaining-requests` 999 of 1,000.
  - **Calibrated** at 20:21:54 UTC to 1 request and 155 tokens. The token figure is inferred.

## 2026-09-29 · Phase 5 · test ground truth labelled blind (reduced set)

- Labelled the 24 cases in `data/cases/test_reduced.json` into `data/ground_truth/test.json`. The other 16 are left
  blank, and `frozen_at` is empty until the data owner freezes the file.
- Labeller: Claude (Opus 5.5). Labels come only from the worksheet, the seed history, the policy, the verdict
  guide and the family rules. No system output was opened.
- Reasoning per case, and 7 items to confirm before freezing, are in `data/labelling/test_labeller_notes.md`.
- Two labels differ from the reduced set's pre-labelling groups:
  - TEST-024 is `unknown`: the blacklisted vendor has no precedent.
  - TEST-007 is `generalized`: a capex bank change has no capex precedent.
- **Decided by user** (asked for blind labelling); label choices are the labeller's, pending the data owner's review.

## 2026-09-28 · Phase 5 · test runs started (reduced set), runner resume

- **Decided by user:** run the test arms now and "go as far as possible". The test ground truth isn't written
  yet, so the runs produce predictions only; scoring waits for the frozen ground truth.
  - Blindness is kept: per-case test predictions aren't shown to the user (the labeller) until the ground truth
    is frozen. The runner's per-case lines are filtered out of the console log.
- **Reduced test set (SPEC §14.6):**
  - `make budget` puts the whole project plan at 12 quota-days full or 9 reduced, over the §14.6 threshold of
    4, so the reduced set applies.
  - Most of that is already spent (narratives, dev runs, development). What's left is the reduced test runs
    (310K tokens) plus the learning curves (158K), against 217K of daily capacity.
  - `data/cases/test_reduced.json` lists 24 of the 40 test cases, chosen by spec family before any test ground
    truth existed. It keeps all 8 interaction cases, the 3 M6 capex cases, the 3 override cases and the 4
    unknowns.
- **`eval/run_arms.py` resume (`--run ID --resume`):**
  - skips cases already in the run's results file and keeps the run's ledger and memory bank;
  - saves after every case;
  - stops cleanly before a case when the primary model has under 6,000 tokens left (`CASE_MARGIN_TOKENS`,
    about D's measured per-case cost), or when a call fails on quota.
  - A quota stop records nothing for that case, so it can never be scored as an escalation. Before this, a run
    that hit the quota wrote `llm_unavailable` escalations for the remaining cases.
- **Run order:** C (which also writes E), then D, then A and B. All use run ID `test1`.
- **First C session:** 11 of 24 cases, all on `openai/gpt-oss-120b`, with no `llm_unavailable` rows. It
  stopped cleanly before TEST-016 with 4,739 tokens left.
  - One Hindsight retain batch during seeding returned HTTP 500. The single retry succeeded; seeds use fixed
    document IDs with replace mode, so the resend can't duplicate.
- **`eval/drive_test.sh`:**
  - waits until Groq has 30,000 tokens, resumes the arm, and repeats until all 24 cases are done, then moves to
    the next arm (C, D, A, B);
  - checks the quota every 15 minutes, and gives up after 40 attempts per arm;
  - keeps per-case predictions out of its log.
  - Claude Code stopped the first driver while it was waiting, because the machine was low on memory; no case
    was lost. **Restarted on the user's request** (29 Sep), with C still at 11 of 24.

## 2026-09-28 · Phase 5 · dev results for all arms, metric fixes, TEST-016

- **Arms A and B on dev** (`run-bench-dev-A-dev1.json`, `run-bench-dev-B-dev1.json`), each one Groq call per
  case. The full dev table (A to E) is in `docs/benchmark.md` under "Dev results":
  - False confidence: 3 of 4 for A and B, 0 of 4 for C, D and E.
  - Floor violations: A 6 of 8, B 4 of 8, and 0 of 8 for C, D and E.
  - Dev is the tuning split, and the doc says so.
- **Fix, M3 case list:** `correct.cases` listed the *misclassified* cases, unlike every other count, where
  `cases` lists what's counted in x. It now lists the correct cases, and a new `misclassified` field lists the
  rest. The numbers were unaffected.
- **Fix, M11 tokens:**
  - C and E showed 0 tokens per case, because their extraction and verifier calls were cache hits.
  - `eval/run_arms._cost` now charges a cache hit the tokens of the original call it replays: the latest
    earlier uncached call with the same role, case, model and prompt version.
  - Arm E is charged the same as C, since it needs the same calls.
  - The existing dev run files were re-costed by a one-off script, with a backup kept in the scratchpad. C
    and E moved from 0 to 3,078 tokens per case, D from 4,273 to 5,345, and A and B were unchanged.
  - Hindsight Cloud's own LLM usage isn't included. `docs/benchmark.md` says so.
- **TEST-016 narrative:**
  - It was flagged because Groq returned HTTP 400 `json_validate_failed`: the model output a refusal ("I'm
    sorry, but I can't help with that.") in place of JSON, probably triggered by the related-party wording
    ("is my sister").
  - Both Gemini models were over quota at the time.
  - A plain retry succeeded, and the narrative contains its `must_mention` phrase.
  - The test worksheet and skeleton were rebuilt (40 cases).

## 2026-09-28 · Quota · new Groq key (supplied by user)

- The user replaced the Groq API key.
- **Verified:** a 149-token probe through `llm.py` (`SPIKE-QUOTA-PROBE`) succeeded, and Groq's headers reported
  `x-ratelimit-remaining-requests` 999 of 1,000, so this key's daily allowance was unused.
- **Calibrated:** 1 request and 149 tokens as of 17:13 UTC. Groq sends no daily-token header, so the token
  figure is **inferred** from the request count.
- **Earlier caution still stands:** if the new key belongs to a different Groq account, extra free-tier
  accounts may conflict with the provider's terms. That's the user's decision.
- `llm.py` keeps the provider's last rate-limit headers (`LLM.last_headers`) for calibration and the demo
  readout.
- Started in the background: test narratives (40), the test labelling worksheet, arms A and B on dev, then the
  dev report.

## 2026-09-28 · Phase 4 · arm D on dev

`run-bench-dev-D-dev1.json` (fresh vector store `kaveri-dev-d-dev1`, 45 seeds, local embeddings, one
`composer_d` LLM call), run with `--force`: the guard's 120K estimate was conservative, ~88K was available,
and the run used ~73K.

| Arm | False confidence | Floor violations | Classes correct | Procedure F1 | Effort per 10 | Minutes per 10 exception cases | Tokens per case |
|---|---|---|---|---|---|---|---|
| C | 0 of 4 | 0 of 8 | **20 of 20** | **0.923** | **21.0** | **132.5** | 3,073 (dev1)* |
| D | 0 of 4 | 0 of 8 | 19 of 20 | 0.872 | 22.0 | 136.9 | 4,273 |
| E | 0 of 4 | 0 of 8 | 20 of 20 | 0.923 | 24.5 | 145.0 | 0 (reuses C) |

- \*C's dev3 run reused cached verifier outputs, so its own tokens-per-case figure reads 0. The real cost is
  dev1's measured 3,073.
- D's one class miss: DEV-013 came out generalized (ground truth: known).
- On dev, C ≥ D on every metric, at fewer LLM tokens per case (reflect runs on Hindsight's credit, not the
  Groq quota). This is a small dev sample, and the test split is where C vs D is scored.

## 2026-09-28 · Phase 4 · first dev runs (arms C and E) and dev-only fixes

**Dev run 1** (`run-bench-dev-C-dev1.json`, fresh bank `kaveri-dev-c-dev1` seeded with the 45 seeds), scored by
`eval/report.py` against the frozen dev ground truth:

| Arm | False confidence | Floor violations | Classes correct | Procedure F1 | Effort per 10 cases |
|---|---|---|---|---|---|
| C | 1 of 4 | 0 of 8 | 19 of 20 | 0.589 | 26.5 |
| E | 1 of 4 | 0 of 8 | 19 of 20 | 0.73 | 26.0 |

- DEV-017: Hindsight reflect returned HTTP 504 twice. The composer took the documented §7.1 fallback and flagged
  it (visible degradation).

**Diagnosis and fixes** (dev split only, as SPEC §14.2 allows; each is general, not case-specific):

1. **False confidence, DEV-020.** The approver was on leave and the only delegate's limit (₹1,00,000) was below
   the amount. The verifier matched the E3 "route to the delegate" lesson anyway.
   - **Fix, `rules.check_approver`:** when no valid delegation covers the amount on the date, the cause is
     `approver_on_leave_no_valid_delegate`. The existing cause guard then rejects E3 precedents (code
     verifies the lesson's condition).
   - DEV-020's `scenario_checks` in `data/cases/specs.json` were updated to the new cause (rule vocabulary; the
     frozen `dev.json` is untouched).
2. **Reflect searched interaction memories on single-check cases** (DEV-003, DEV-005). It pulled in I1 steps
   citing unverified cases; they were dropped and the routing was lost. **Fix:** the `interaction` and
   `combo:` tags are passed to reflect only when a verified interaction precedent applies.
3. **An override merged into a standard lesson counted as verified support** (DEV-014, DEV-015). Hindsight
   consolidated the E6 override PR-2026-0746 into the sole-source observation, and reflect then swapped the
   category-head sign-off for "collect quotes".
   - **Fix:** override cases inside a mixed candidate aren't verified support.
   - An override-only candidate counts **only with verdict `yes`**: its context is its condition (DEV-005 and
     DEV-018 had the E4 override at "partial").
4. **Removals and additions must be grounded** (SPEC §7.1: every cited case must be verified).
   - A removal of any step needs a verified citation; before, a routing or convenience removal only needed a
     reason.
   - **Interpretation, recorded:** a step added beyond the plain union must cite a verified case whose ledger
     final steps include that step (DEV-003 added `EXPEDITE_PO` citing a case that only used
     `ROUTE_DELEGATE`).
5. **Metric M4 convention.** SPEC §9 gives normal cases `STANDARD_APPROVAL`; the adjudicated ground truth writes
   `[]`. M4 ignores `STANDARD_APPROVAL` on both sides for every arm.

**Dev runs 2 and 3** reused `kaveri-dev-c-dev1` (new `--bank` option). Evaluation runs never retain, and it holds
exactly the 45 seed documents (checked), so it's equivalent to a fresh identically seeded bank (SPEC §14.2).

| Run | Arm | False confidence | Floor violations | Classes correct | Procedure F1 | Effort per 10 | Minutes per 10 exception cases |
|---|---|---|---|---|---|---|---|
| dev2 | C | 0 of 4 | 0 of 8 | 20 of 20 | 0.862 | 24.0 | 138.8 |
| **dev3** | **C** | **0 of 4** | **0 of 8** | **20 of 20** | **0.923** | **21.0** | **132.5** |
| dev3 | E | 0 of 4 | 0 of 8 | 20 of 20 | 0.923 | 24.5 | 145.0 |

- Minutes use the ASSUMPTIONS in `config/assumptions.yaml`; the baseline is 400 per 10 exception cases.
- On dev, C equals E on procedures and needs less review effort. **All 8 interaction cases are in the test
  split,** so dev can't show C vs E on interactions.
- **Gate G1 regression:** unchanged (false confidence 0 of 15; classes 13 of 15; citations 52 of 52).
- **Tests:** 159 in total (+7).
- **Next:** arm D on dev needs ~78K Groq tokens; ~87K were available, and the runner's guard asks for 120K, so
  it waits for the refill. Then arms A and B.

## 2026-09-28 · Quota · calibrate the limiter to the provider's own usage figures

- **Why:** Groq's usage page (the user's screenshot, 21:53 IST) showed 41 requests and ~51K tokens used today,
  so ~149K left. The limiter, replaying every Groq call in the local log, showed ~14K left. The log includes
  usage that Groq doesn't count against the current quota (for example after a key change), so the local
  estimate had drifted.
- **New `quota_calibrations` table** and `scripts/quota_calibrate.py`. A reading records "at time T the
  provider reports X requests and Y tokens used".
  - `RateLimiter` starts from the latest reading in the last 24 h, drops older log rows, then applies the
    continuous refill and adds calls logged after T. Test added (153).
- **Applied:** `openai/gpt-oss-120b` at 2026-09-28 16:23 UTC, 41 requests and 51,000 tokens. The 51,000
  counts cached tokens, which Groq's docs say don't count, so it's conservative. Available afterwards: 960
  requests and 149,256 tokens.
- **Dev run started:** arm C (with E) on the 20 dev cases, run id `dev1`, after `make budget`.

## 2026-09-28 · Gate G2 (dev) · ground truth validated and frozen

- **`data/ground_truth/dev.json` validated structurally:**
  - it covers exactly the 20 dev case IDs;
  - every class is valid and every step is in the library;
  - `uncovered_checks` is non-empty exactly when the class is `unknown`;
  - `causes` keys match `failed_checks`.
  Answers were not reviewed or changed.
- **Frozen by hash, not by editing the data owner's file:** `data/labelling/FROZEN.json` records its SHA-256
  (`df6bb542…`) and the freeze time. `eval/report.py` now refuses to score a split that isn't frozen (exit 2)
  or whose ground truth changed after freezing (exit 3).
- `docs/benchmark.md` Limits now state the dev-labelling caveats:
  - the engine-building session was the first labeller, having read case-design notes;
  - the second labeller was a Claude subagent, not a person;
  - agreement was 11 of 20 cases on every field before adjudication, and 20 of 20 on class, checks, causes
    and uncovered checks; 20 of 20 after adjudication.
- **Gate G2 status (dev):** ground truth committed and frozen ✓; labeller agreement reported ✓; composer tests
  green ✓. The test split's ground truth and narratives are still to come.
- Dev runs are quota-bound. All arms on dev need ~250K Groq tokens (extraction 17K, C 40K, D 78K, A 40K,
  B 82K), and ~14K were available at the freeze.

## 2026-09-28 · Phase 2 data · dev ground truth and second labelling

**Decided by user:** Claude Code labels the 20 dev cases, and an independent subagent labels them a second time.

- `data/ground_truth/LABELLING_GUIDE.md`: `config/verdict_guide.md` word for word, plus the family rules from
  SPEC §4, §5.3, §6.3, §7.2 and §13.
- `data/ground_truth/dev.json`: 4 normal, 5 known, 2 generalized, 5 composed and 4 unknown. Reasoning for each
  case is in `data/labelling/dev_labeller_notes.md`.
- The second labelling is in `data/labelling/dev_second_labeller.json`, with its notes. The subagent started
  with a fresh context and was barred from `dev.json`, run outputs, engine code and this changelog.
- **Agreement before adjudication: 11 of 20 cases on every field.** Class, failed checks, causes and uncovered
  checks agreed in 20 of 20. The two conventions that differed: normal-case steps (16 of 20) and
  `novel_combination` on composed cases with no interaction precedent (15 of 20).
- **Decided by user (adjudication):** normal cases get `[]`, and `novel_combination` is true on any composed
  case that no verified interaction precedent covers (SPEC §5.3). After adjudication: 20 of 20.
- **Limits:** the first labeller is the session that builds the engine, and it had read part of this changelog's
  case-design notes. So the labels are not blind in SPEC §13's sense. The second labeller is also a Claude
  model, so the agreement shows consistency with the rules, not two independent human judgements.
  `docs/benchmark.md` should state both. `frozen_at` stays blank until Gate G2.

## 2026-09-28 · Phase 2 data · specs verified; generator fix; dev narratives

**Specs verified independently in this session:**

- `make specs` reports **0 problems across 60 specs (20 dev, 40 test)**; `make test` passes (152).
- A scan of the fields the generator sends to the LLM (`story`, `must_mention`) found **no leaked labels**: no
  class words, step codes or family IDs.
- Every spec with a text-only signal states it in its required phrases or story. TEST-036's related party is
  financial ("sleeping partner … through a family investment"), which is valid.

**Fixed the open item:** `generate_cases.unsupported_facts` now matches whole words, so "deadline" no longer
counts as "line" and no longer switches off the stopped-line guard. Test added.

**`generate_cases.py --split dev|test`:** narratives are generated one split at a time, so each batch fits
Groq's token window and every narrative stays on `gpt-oss-120b` rather than spilling onto the Gemini fallback.
The dev batch ran first; the test batch waits for the quota to refill.

**Dev narratives: 20 of 20 generated, 0 flagged** (`data/cases/dev/`).

- Spot-checked the risky ones. DEV-013's bank change appears only in the vendor accounts team's last email,
  as the spec intends.
- DEV-010's "my cousin" remark landed in the justification rather than the email the story names. That's
  harmless: the extractor checks each quote against whichever field it came from.
- Groq tokens available afterwards: ~12K, so the test batch (40 narratives, ~32K tokens) waits.

**`scripts/labelling_worksheet.py`** writes `data/labelling/<split>_worksheet.md`: for each case, the
generated request text, the ledger facts on that date, and the checks it was built to fail. It also writes
`<split>_skeleton.json`, the ground-truth format with every answer blank. It suggests no answers and never
writes to `data/ground_truth/`. The dev worksheet is generated.

## 2026-09-28 · Phase 2 data · the 60 benchmark case specs (SPEC §13)

**Decided by user:** Claude Code writes the 60 case specs. That closes one of the open questions from
Phase 2 → 3. The blind ground truth and the second labelling on dev are still open and still belong to a data
owner who doesn't build the engine. `docs/benchmark.md` now states under Limits that the specs came from
the engine-building session.

**`data/cases/specs.json`: 60 synthetic specs, 20 dev and 40 test,** in the SPEC §13 mix: 10 normal,
12 known, 6 generalized, 16 composed, 10 unknown and 6 adversarial.

- Specs are numbered in date order within each split (`DEV-001`…, `TEST-001`…), so IDs don't group cases
  by class. Dates run from 15 Sep to 26 Nov 2026: after every seed, inside FY 2026-27.
- **In test only:** all 8 interaction cases (2 I1, 2 I3, 4 held-out I2), the 3 post-July capex
  approver-away cases (M6), and the 3 after-override cases (one each for the E2, E4 and E6 overrides; M7).
  SPEC §14.6 keeps all 8 interaction cases in the test set, and M5, M6 and M7 are scored there.
- **Composed:** 4 where the plain union should hold (E1+E3, E4+E3, E1+E4, E2+E4) and 4 with a bank change
  (E5+E3, E5+E6, E5+E4, E5+E1).
- **Unknown:** 4 U1, 3 U2, and 3 with one uncovered check among covered ones. In each of those three a
  precedent exists for the same check but the request contradicts its condition, or no precedent exists:
  - the delegate's limit (₹1,00,000) is below the amount;
  - a 12% overrun with the line down, where E2 allows up to 10%;
  - a blacklisted vendor.

  SPEC gives no human answer for these, so the data owner decides them from the policy.
- **U2 variant:** one U2 vendor also has an expired certificate. The cause is `gst_cancelled`, which tests
  that the E1 precedents aren't matched.
- **Adversarial:** three lures (certificate expiring next month, an amount 6% off a recent order, an email
  saying the bank details are *unchanged*) and three bank changes stated only in the email thread.
- **New spec fields** besides the generator's own, none sent to the LLM:
  - `vendor_id`, `amount`, `category` and `urgency`: SPEC §13 step 1's structured facts.
  - `text_signals`: the signals the narrative must carry.
  - `scenario_checks`: the checks the scenario is built to fail. This is how the case was built, not a
    ground-truth label.
  - `ledger`: master-data facts in plain words, for the labeller.
- Stories avoid label words, and avoid "deadline" (see the open item below).
- A few vendor names carry "M/s" or "Pvt. Ltd."; `normalise.match_vendor` resolves them.

**`data/master/master.json` extended to SPEC §13's 40 vendors and 25 employees.**

- Vendors V-117 to V-139, with Telangana GSTINs that carry a valid check character. They include recently
  expired certificates, recent bank changes, GST cancellations and sole-source flags.
- Employees: E-116 and E-117 (delegates), E-302 (Finance Controller), E-303 (category head), and requesters
  E-406 to E-411.
- **Changed existing records:** E-110 is on leave 23 Nov – 4 Dec and E-111 on leave 9–20 Nov, with
  delegations to E-117 (up to ₹2,00,000) and E-116 (up to ₹1,00,000).
- 7 earlier requests (PR-2026-0812 to PR-2026-1012) for the split-shipment cases and the 6%-off lure.
- Every other existing record is unchanged. **Verified:** all 7 demo beats resolve to the same vendors and
  fire the same checks as before. The demo's dates end in October, before the new leave windows.
- Constraint the specs work around: the demo spends CC-MACH's whole budget, so every CC-MACH request fails
  the budget check. Only E2, I1, I3 and the 12%-overrun case use CC-MACH.

**`scripts/check_specs.py` (`make specs`) and `tests/test_specs.py` (4 tests, 151 in total).**

- For each spec, the checker rebuilds the request facts (amount parsed and vendor matched in code, the
  spec's text signals injected) and runs `rules.run_checks` against the master data plus that split's other
  requests. The result must equal `scenario_checks`.
- It also checks the SPEC §13 family counts, splits, dates, form fields, label words in stories, and that
  each `ledger` summary still matches the master data. A later master edit (for example for the demo) that
  breaks a benchmark case fails `make test`.
- **Flagged for the user:** this runs the deterministic ledger checks on the test split's own specs. No
  LLM, memory, verifier, classifier or composer is involved, and it shows nothing about the system's
  answers. It was judged data QA, not the "running anything against the test split" that CLAUDE.md asks to
  stop for. Say if you want it limited to dev.
- New `make cases` runs `generate_cases.py` on the specs. **Not run:** it sends synthetic specs to Groq,
  about 60 calls or roughly 47K tokens at the measured 787 tokens per narrative, plus retries.

**Open item found (not fixed):** `generate_cases.unsupported_facts` matches substrings, so a story containing
"deadline" contains "line" and switches off the stopped-line guard. The specs avoid the word. A word-boundary
match would fix it.

## 2026-09-28 · Phase 6 · demo script, full rehearsal, docs

**Demo script.**

- `data/demo/fixtures.json` holds the SPEC §18 demo as 8 ordered beats (hook, first exception, second
  certificate case, replay, established case, split shipment with rejection, similar case, related party),
  each with a demo date, a request, and a pre-filled decision where the script needs one.
- API: `GET /demo/fixtures` and `POST /demo/beat/{key}`.
- UI: the Demo controls page has a "Demo script" list with Run buttons; in demo mode the case page pre-fills
  the resolution form or the rejection from the fixture (SPEC §15).

**Data for the ₹4.8L hook** (demo only; the benchmark hasn't used it):

- Demo master: CC-MACH budget 80,00,000 allocated and spent, so ₹4.8L is exactly 6% over. Plant head E-201 on
  leave 21 Sep – 2 Oct, with delegate E-205 up to ₹10,00,000.
- Seeds: I1 PR-2026-0620 is now ₹4,60,000 and I3 PR-2026-0690 is now ₹4,40,000. Without a 2–10L interaction
  precedent, the verifier and the band guard would call both interactions "partial" and the hook's PO couldn't
  be released.

**Full rehearsal** (`scripts/rehearse.py`, `make rehearse`) from reset: **all 8 beats in 358 s**, about half
of it reset and seed.

- **Hook:** "3 of 3 problems have precedents · 2 interaction precedents apply · payment held until the bank
  callback". `HOLD_PO` was removed citing I3 (PR-2026-0312, 0484, 0690); `ROUTE_DELEGATE` was replaced by
  `ROUTE_NEXT_LEVEL_APPROVER` citing I1 (PR-2026-0360, 0515, 0620); `EXPEDITE_PO` kept; the callback and
  payment hold kept.
- **First exception:** unknown → resolved → the `step:vendor` lesson formed.
- **Second certificate case:** generalized, not the scripted known and tentative. The fixture's "assembly jigs"
  is Kaveri's own tooling, so indirect MRO. **The fixture now says fasteners that ship inside the product.**
- **Replay:** the lesson was consolidated from 4 cases. **Next case: known, established, one-click.**
- **Split shipment:** partial, adding `REQUEST_MORE_INFO`, because the lesson's condition "no duplicate-invoice
  history" can't be confirmed from the request (SPEC §5.1: correct). Reviewer rejected. **Similar case →
  `REJECT_REQUEST` + `ESCALATE_AUDIT`.**
- **Related party:** unknown, escalated, with the floor adding `DECLARE_CONFLICT_OF_INTEREST`.
- `scripts/rehearse.py` now prints seconds per beat and per decision.

**Docs:**

- `README.md`: problem, persona, how it works, how Hindsight is used (real call snippets), the G1 counts from
  `eval/results/gate1-20260928T132132.json` labelled as a development gate, setup and limits. The benchmark is
  marked "not run yet".
- `docs/memory-design.md`: the SPEC §8 design with **verbatim** observation text and history from the rehearsal
  bank (the E1 lesson growing from 1 to 5 cases; the override's context-specific lesson; the I1 and I3 lessons).
- `docs/adoption.md`, `docs/benchmark.md` (protocol, the arm C vs D model confound stated in advance, honest
  expectations, limits), `docs/content/outlines.md`, `docs/demo-runbook.md` (stage plan).

**Environment:** Claude Code stopped the background API and web servers because the machine ran low on
memory. They were not restarted.

## 2026-09-28 · Phase 4 · memory dynamics: overrides, snapshots, replay, policy flag, metrics

The user said to continue without answering the open questions, so the defaults hold: G1 data stays frozen,
conflicts follow SPEC's class order, and the ground truth waits for its author.

**Overrides (SPEC §8.7).**

- Interpretation, recorded here: the ledger records the override's **context** on each overridden lesson
  (`lessons.overridden_by`: "<case> on <date>: <reason>. Reviewer did: …") and **keeps `status` active**.
  Flipping cases to `overridden` would erase a context-specific lesson everywhere, so it isn't done. SPEC
  §5.2 still applies: cases with `status=overridden` count for nothing in strength.
- The verifier sees "OVERRIDDEN IN CONTEXT: …" on the cited case and judges whether the request shares that
  context.
- Seeded overrides mark the cases named in their `overrides` field (`import_history.mark_overridden`). Live
  edits and rejects mark the verified cases the recommendation cited.

**Observation snapshots (SPEC §8.9).**

- `retain.take_snapshots` polls each tag's observations **until one cites the newly retained case**, with
  backoff to the 60 s limit, then stores `observation_snapshots`.
- "No pending consolidation operations" isn't used as the signal: in Phase 0 it was true at 0.7 s, before
  the observation updated at 4.1 s.
- On timeout it reports `consolidated: false` with the pending tags. Arm D skips (`consolidates = False`).
- The deadline check is `>=`: on Windows the monotonic clock ticks about every 15 ms, which made a
  zero-timeout test flaky.

**`/demo/replay?weeks=3` (SPEC §18 beat 3).**

- Retains the scripted resolutions in `data/demo/replay.json` (2 E1 confirmations, dated relative to the
  demo clock) through the seed-import path, with **no LLM calls**; then takes snapshots and moves the clock
  forward.
- The demo-controls button is wired.

**Policy backstop (SPEC §8.8) fixed.**

- It now flags a coverage if **any** cited case predates a policy change on the same tag (was: all). That is
  SPEC's wording.
- Found live: a capex approver-away case cited an observation merging pre- and post-July E3 cases. The
  verifier wrote "no later policy change", and the old rule never fired, so the case got one-click review.
  The recommendation was still correct (`ROUTE_DELEGATE` + `ADD_CONTROLLER_SIGNOFF`, citing PR-2026-0758).

**Groq daily-quota model corrected.** `RateLimiter` now replays the last 24 h of logged calls as a **bucket
refilling at limit/86,400 per second**, not a sliding 24 h sum.

- Continuous refill is verified for requests (header `x-ratelimit-reset-requests`) and assumed for tokens,
  which have no header.
- If that assumption is wrong, Groq's long-retry 429 moves calls to Gemini.
- Result: the tokens available went from 18K (sliding sum) to 44K.

**Metrics and evaluation (SPEC §10, §14.4).**

- `api/metrics.py`: M1–M11 as pure functions with counts ("x of n"), the simulated reviewer for M8/M9, and
  floor requirements (F1, F3, F4) derived from the ground truth.
- `docs/ground_truth_format.md`: the ground-truth schema for the data owner.
- `eval/report.py`: scores each arm's latest runs against `data/ground_truth/<split>.json`; refuses
  without it.
- `eval/replay.py`: the learning curve from an empty bank, seeds and cases in date order. The simulated
  reviewer retains the ground-truth resolution through the UI's decision path. It outputs the four series
  (rolling one-click share, review effort, false confidence, maturity per family). **It hasn't been run:
  there's no ground truth yet.**

**Found and fixed:** the case view chose its "best precedent" by case count, not the detector's SPEC §5.2
rule (verdict, then strength, then recency), so it could show a different citation than the one the
detector used. It now uses the same rule.

**Live beats against the demo bank** (clock 24 Sep → 15 Oct 2026)

- **Beat 3, maturity.** "Replay 3 weeks" consolidated the `step:vendor` lesson from 3 cases (PR-DEMO-E1B,
  R001, R002; 2 revisions in Hindsight's history; snapshot stored). The next expired-certificate case was
  **known, established (3 cases), one-click**.
- **Beat 5, override.**
  - A split-shipment case for vendor V-116 got the E4 lesson (`LINK_MASTER_PO`, `ALLOW_SPLIT_DELIVERY`). The
    reviewer **rejected** it (a duplicate-invoice incident in 2025).
  - Retained: an experience and an override. The ledger marked PR-2026-0477 overridden in context.
  - Hindsight formed a new `step:duplicate` observation: "when the vendor has a history of duplicate
    invoicing, the standard split-shipment procedure is overridden … REJECT_REQUEST and ESCALATE_AUDIT".
  - **The next split shipment from the same vendor got `REJECT_REQUEST` + `ESCALATE_AUDIT`.** The verifier
    marked the original E4 lesson `no`: "precedent requires no duplicate history, but vendor has one".
- **Policy memo:** the capex approver-away case got `ROUTE_DELEGATE` + `ADD_CONTROLLER_SIGNOFF` (M6 would
  score it correct); the flag fix above came from this run.
- Demo master data gained V-115 and V-116 and prior request PR-2026-0950.

**UI:** the lesson panel shows an "overridden in context" badge, with the context on hover.

**Tests:** 147 in total; new `test_metrics` (5) and `test_replay` (2), plus snapshot, override-context,
policy-flag and bucket tests.

**`scripts/estimate_budget.py` rewritten to be role-weighted.**

- It priced every request at the costliest role's average; that became arm B (4,094 tokens: policy document
  plus retrieved cases) and put the plan at 21 and 15 quota-days.
- Each plan line now uses the measured average of its roles: extraction 842, verifier 2,340, composer_d
  2,272, arm_a 1,980, arm_b 4,094, narrative 787 tokens.
- Learning curves no longer charge LLM calls for seeds (replay retains them through the template).
- The demo reseed count is corrected to 37.
- Result: **full 11, reduced 8 quota-days**. The SPEC §14.5 placeholder allowance of 400 development and
  rehearsal calls is 936K of the reduced plan's 1,697K tokens. The reduced benchmark itself is about 761K
  tokens, roughly 4 quota-days.

## 2026-09-28 · Phase 3 · frontend, and Gate G1 re-run under the new prompts

**Frontend** (`web/`: Next.js 16, React 19, Tailwind 4, TypeScript; `make web`)

- **shadcn/ui components are hand-written** in shadcn style (button, card, badge, tooltip, sheet, checkbox,
  input and textarea) on Radix primitives with CVA, clsx and tailwind-merge. The shadcn CLI couldn't run:
  npm 11 refuses its `--allow-scripts` install ("not allowed in project-scoped installs"). Also installed:
  lucide-react and recharts.
- One install script stays unapproved (`unrs-resolver`, an ESLint helper). The build doesn't need it.
- Screens (SPEC §15):
  - **queue**: grouped by class, with maturity, novel-combination and review-mode badges;
  - **case view**: the summary line; a **7-stage reveal** (request with signal spans highlighted → failed
    checks → precedents with verdict and maturity → plain union → interaction changes struck through with
    citations → safety floor → final procedure), auto-advancing every 1.5 s with `?demo=1`, plus a Replay
    button; a **"Why this step?" drawer** (cited ledger cases, recalled memory text, verdict and
    differences, observation source count, code-guard notes, flags); actions by review mode (Approve,
    per-step ticks plus Confirm, Resolve), with Edit and Reject always available; a **resolution form**
    (covered vs not covered, step picker by class, rationale and outcome, "Save as edge experience");
  - **new request**: pre-filled synthetic example, with a "checking, recalling and composing from past
    cases…" state;
  - **lesson panel**: the current Hindsight observation, its case count and IDs, a word-level before/after
    diff from Hindsight's observation history, and the ledger cases under the tag;
  - **benchmark**: G1 runs and per-case arm results as counts; the M1–M11 metrics come with
    `eval/report.py` in Phase 5;
  - **demo controls**: clock, reset, seed, a disabled "replay 3 weeks" (Phase 4), LLM quota left, and API
    latency.
- Glossary tooltips (`web/lib/glossary.ts`): GSTIN, delegation matrix, line-down, sole-source, PO, lakh,
  capex, controller, cost centre, MRO, precedent, safety floor. ₹ uses Indian grouping; the "Synthetic
  data" footer is on every page.
- **Verified:** `npm run build` passes (all 7 routes); every page serves 200 from the dev server; CORS
  preflight from :3000 passes. **Not verified here:** how the pages look in a browser.

**Gate G1 re-run** with `extractor-v2` and `verifier-v4` (`eval/results/gate1-20260928T132132.json`)

- **PASS:** false confidence 0 of 15; classes 13 of 15; citations 52 of 52; checks 15 of 15.
- **Regression:** the novel-combination flag is right on 3 of 5 (was 5 of 5). C1 and C2's interaction
  precedents are now "partial" on category.
- **Cause:** the frozen G1 history labels line-down spares `direct_material` (the same mislabel fixed in
  `data/seed/history.csv`), while `extractor-v2` now calls them indirect MRO. K4 and K5 stay generalized
  for the same reason.
- **Open (for the user):** correct the G1 history's categories (a data correction, not a label or case
  change; about $0.39 to reseed plus ~45K tokens to re-run), or keep G1 frozen as recorded.

## 2026-09-28 · Phase 3 · API, arms, arm D memory, and prompt fixes found live

**Arm D and the runner**

- `api/memory/vector_backend.py`:
  - a local store per bank (`data/vector_store/<bank>/`), one chunk per memory, embedded with
    `sentence-transformers/all-MiniLM-L6-v2` (local; never an LLM API);
  - the `any_strict` tag filter, cosine top-k within the same 2,048-token recall budget, and replace by
    `document_id`;
  - no consolidation, observations or reflect (that is what C vs D isolates); `tags=None` is used by arm B.
  - `sentence-transformers` 6.1.0 and torch 2.14.0+cpu are installed and uncommented in `requirements.txt`.
- `eval/run_arms.py`, one runner for every arm:
  - C, D and E share `pipeline.py` (no fork); **E is computed from C's coverage in the same run**.
  - A and B are one LLM call each, given the policy document, a factual ledger extract (vendor, budget,
    approver and leave, delegations, earlier requests; no rule results) and the request text. B adds the
    top-k retrieved seed narratives.
  - Each run gets a fresh ledger (`data/runs/`) and its own bank or store. The quota guard refuses a run
    that would exceed Groq's remaining tokens unless `--force`.
  - Results go to `eval/results/run-*.json` and `eval_runs`.
- `data/seed/policy.md`: the synthetic two-page procurement policy v1 and the 1 Jul 2026 memo (SPEC §13),
  used by arms A and B.
- **Smoke run** of every arm on 3 gate cases (K1, C2, U2). There are no dev cases until the specs exist.
  - All arms run.
  - Early signal: arm B (plain RAG) classed the related-party case **normal with standard approval**, and
    arm A called it "known"; C escalated it. Arm E kept `HOLD_PO` on C2; C released it.
  - This is 3 cases, not a benchmark result.

**API** (`api/main.py`, `api/views.py`, `api/engine/retain.py`, `api/memory/records.py`)

- Every SPEC §12 route. `/demo/replay` (Phase 4) and `/boundary-map` (stretch) answer 501. `/quota` and
  `/health` were added for the demo controls.
- **The demo ledger is its own database, `data/demo.db`**, so `/admin/reset` never touches the LLM log or
  the quota counters.
- `data/master/master.json`: the demo and API master data, started as a copy of the Gate G1 master; it is to
  be extended to SPEC §13's 40 vendors and 25 employees.
- `retain.py` (SPEC §9 stage 9): resolve → experience; unchanged approval of a single check → confirmation;
  multi-check differing from the union → interaction; edit or reject → override plus the reviewer's own
  decision. §8.7 step 3 and the §8.9 snapshots are Phase 4.
- `api/memory/records.py`: the §8.3 record template, moved out of `scripts/import_history.py` so the seed
  import and the live retain share it.
- The ledger now stores each request's extracted signals, its dropped signals, and each candidate's memory
  text.
- `MemoryBackend` gains `observations(tag)` and `observation_history(id)`; arm D returns none.
- `make api`, `make seed` (through `/admin/seed`), `make reset`, `make eval`.

**Found live against the demo bank, and fixed**

- **Verifier `verifier-v3`, then `verifier-v4`.** The verifier kept listing a precedent's resolution
  ("no bank callback evidence", "procedure steps not documented") as differences, so exact matches became
  "partial".
  - v3 names the five things to judge, and says steps, evidence, callbacks and approvals are never
    differences.
  - v4 adds **the request text** to the prompt, since SPEC §5.1 judges conditions "from the request" and
    the verifier previously saw only structured facts. It also labels ledger steps "resolved with (how it
    ended, not a condition)" and ends with a reminder.
- **Extractor `extractor-v2` (still the extractor, per the user's decision).** The category was unstable:
  "coolant + pump kit" came out `indirect_mro` in G1, while "pump assemblies" and "spindle motor" came out
  `direct_material`. The v1 prompt listed "pumps built into parts" under direct material. v2 defines
  categories by what the item is for: components shipped to customers are direct material; spares, repair
  parts and consumables for Kaveri's own machines are indirect MRO, even when a line is down.
- **Seed data fix:** 12 rows in `data/seed/history.csv` (E2, I1, I3 and the E2 override PR-2026-0701) are
  line-down machine spares, labelled `direct_material` by mistake; now `indirect_mro`. These seeds had not
  been used for any scoring. **The Gate G1 data is unchanged**, left frozen as recorded.
- The demo bank was reset and re-seeded after the fix (about $0.89 again).

**Live results through the API** (demo bank, clock 2026-09-24)

- **I3 case:** composed; budget, bank and interaction all `yes`, each on 3 or more cases. `EXPEDITE_PO`,
  with `HOLD_PO` removed citing PR-2026-0312, PR-2026-0484 and PR-2026-0690, and payment held until the
  callback.
- **I1 case:** `-ROUTE_DELEGATE +ROUTE_NEXT_LEVEL_APPROVER` citing PR-2026-0360, PR-2026-0515 and
  PR-2026-0620.
- **E1 case:** unknown and escalated (no E1 precedent in the demo bank, by design). After the analyst
  resolved it, the experience was retained, and within about 6 s Hindsight consolidated a `step:vendor`
  observation citing PR-DEMO-E1B.
- Trace, queue, audit CSV (21 rows), eval results and clock all work.
- **Tests:** 133 in total; new `test_vector_backend` (4) and `test_retain` (5).

## 2026-09-28 · Phase 2 → 3 · decisions (decided by user)

- **Category source: the extractor (SPEC §9 unchanged).** The user compared it with the vendor master and a
  hybrid, and kept the extractor. The G1 misses K4 and K5 therefore stand as recorded.
- The user said to continue to Phase 3, which covers the `sentence-transformers` install (listed in
  CLAUDE.md) and seeding the demo bank.
- Still open: whether `REJECT_REQUEST` should beat convenience steps (implemented as SPEC reads); who
  writes the 60 case specs, the blind ground truth and the second labelling; the benchmark scope cuts
  (before Phase 4).

## 2026-09-28 · Phase 2 · seeds, CSV import, case generator (SPEC §13)

- **`data/seed/history.csv`: the 45 synthetic seed items of SPEC §13**, generated from compact definitions
  by a one-off script (not kept in the repo; the CSV is the artifact).
  - E1 ×7, E2 ×6, E3 ×6 (4 pre-July; 2 post-July capex with `ADD_CONTROLLER_SIGNOFF`), E4 ×5, E5 ×6,
    E6 ×5, I1 ×3, I3 ×3, overrides ×3 (E2, E4, E6) and the 1 Jul 2026 policy memo.
  - `demo_bank=n` on the 7 E1 seeds and the E4 override (PR-2026-0735), because both happen live in the
    demo (SPEC §18). That leaves 37 in the demo bank.
  - PR-2026-0417 (E1) and PR-2026-0312 (I3) keep the IDs the demo script uses.
- **Decision:** seed text comes from the SPEC §8.3 template in code, not LLM narratives. Seeds are
  resolution records, not messy intake, and this saves ~45 LLM requests (the SPEC §14.5 plan counted
  105 narratives; now 60).
- `scripts/import_history.py`:
  - reads the CSV (lists as `A|B`, causes as `check=cause|…`, `demo_bank` y/n);
  - renders overrides (§8.3 kind `override`, document ID `<case>-override-1`, the overridden lesson's
    tags; content states what the lesson recommended, the context, what the reviewer did instead and why);
  - writes `experiences.edge_family` for scoring only;
  - has a CLI (`--csv`, `--demo`, `--bank`, `--db`, `--ledger-only`).
  - The override *semantics* (marking the lesson overridden in context, retaining the reviewer's decision
    as an experience, SPEC §8.7) are Phase 4.
- `make seed`: imports the 37 demo seeds into `kaveri-demo` (not run yet; about $0.89 of Hindsight credit).
- `scripts/generate_cases.py` (prompt `narrative-v2`):
  - spec → messy intake text on the narrative role, cached per case;
  - code checks that every `must_mention` phrase appears verbatim;
  - **new guard:** answer-changing facts the story doesn't state (a stopped line, urgency, a bank change, a
    family connection) are caught. Either kind of failure gets one retry with feedback, then the case is
    flagged, never silently accepted.
  - The spec's `family` is never sent to the LLM.
  - Found in testing: narrative-v1 invented "line 3 band hai / asap" in a routine order, because its own
    Hinglish example primed it. v2 removes fact-bearing examples and forbids unstated facts.
  - Also found: a required phrase must state the deciding fact in full ("line 3 is down", not "line 3").
    This is now documented in the spec format.
- `data/cases/specs.example.json` (2 example specs) and `data/cases/examples/EX-001.json` and `EX-002.json`
  (generated; both pass the checks).
- **Not done here (P4's lane, blind):** the 60 benchmark case specs, `data/ground_truth/` and its
  `LABELLING_GUIDE.md` (to copy `config/verdict_guide.md`), and the second labeller on dev.
- **Tests:** 124 in total; new `test_import_history` (6) and `test_generate_cases` (5).
- `scripts/estimate_budget.py`: the narratives line counts the 60 cases only. `make budget` now gives
  **full 11 quota-days, reduced 8** (measured: narrative ~787 tokens, n=5).
- Regression: `make gate1` after all Phase 2 changes gives identical G1 numbers (false confidence 0 of 15,
  classes 13 of 15, citations 52 of 52; `eval/results/gate1-20260928T122704.json`).

## 2026-09-28 · Phase 2 · composition, conflicts, floor, maturity, review mode (SPEC §5.4, §5.5, §6, §7)

**Engine**

- `api/engine/precedence.py`:
  - `resolve_conflicts` (SPEC §6.2): default class priority. A verified interaction precedent that chose the
    lower-priority step keeps it, unless the floor requires the other step. Every conflict is recorded with
    its reason ("default priority", "precedent PR-…" or "floor Fx").
  - `apply_floor` (SPEC §6.3):
    - F1 bank change → `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT`;
    - F2 a delegate route with no valid delegation for this amount and date → `ROUTE_NEXT_LEVEL_APPROVER`;
    - F3 related party → `DECLARE_CONFLICT_OF_INTEREST`, and never one-click;
    - F4 GST cancelled → `VERIFY_GST_STATUS` and `HOLD_PO`;
    - F5 any code outside the library is dropped.
  - Floor steps carry `origin="floor"` and win any conflict they're part of.
- `config/conflicts.yaml`: **new `conservative_within_class`.** SPEC §6.2 says "within a class the more
  conservative step wins" without naming it, so the two same-class pairs are now explicit: `HOLD_PO` over
  `CONDITIONAL_PO_WITH_QC`, and `ROUTE_NEXT_LEVEL_APPROVER` over `ROUTE_DELEGATE`.
- **Implemented literally, flagged for the user:** SPEC §6.1 lists the outcome class last, so in a
  `REJECT_REQUEST` vs convenience-step conflict (for example `EXPEDITE_PO`), default priority keeps the
  convenience step.
- `api/engine/composer.py`:
  - single-check lessons: steps in at least half of the supporting experience/confirmation cases; strength
    is the number of active cases whose final steps contain the lesson;
  - the union U, with source cases;
  - verified interaction precedents (verdict `yes`; several may apply);
  - the reasoning prompt, with a `Procedure` schema shared by reflect (arm C) and one LLM call (arm D);
  - **validation:** unknown codes are dropped; a step with no verified case citation is dropped and
    flagged (rule 6); removing a risk-control or compliance step from U without citing a verified
    interaction precedent restores it and flags it (rule 5); removing a routing or convenience step with no
    reason restores it;
  - then conflicts, the floor, and the diff text;
  - fallback: if reasoning fails, U plus default conflicts plus the floor, flagged "composed without memory
    reasoning" (forces step-by-step review);
  - arm E: `reasoner=None` gives U plus default conflicts plus the floor;
  - unknown cases compose only their covered checks;
  - `case_maturity` (SPEC §5.4: the lowest level among the lessons used, including interaction
    precedents) and `review_mode` (SPEC §5.5, plus F3 and the fallback forcing step-by-step).
- `api/engine/rules.py`: new `approver_for` (the approval-matrix row), shared by the approver check and the
  floor's F2 context.
- `api/engine/pipeline.py`: `run_case` runs stage 7 per arm (C = reflect, D = `composer_d` LLM call,
  E = none), builds the floor context from the rules and ledger, and saves the procedure (`procedures`)
  and the request's maturity and review mode.

**Memory**

- `api/memory/backend.py`: `reflect` added to the protocol, returning a `ReflectResult`.
- `api/memory/hindsight_backend.py`: reflect with the **inlined** schema (api-notes D7), `include_facts`
  and `tags_match="any"`. A missing `structured_output` is retried once; after that the composer takes the
  fallback.
- `config/memory.yaml`: `reflect: {budget: mid, max_tokens: 4096}` (SPEC §8.5; drop to `low` if dev p95
  is over 10 s).

**Tests:** 113 in total; new `test_precedence` (12) and `test_composer` (9, including the I3 story, the
removal rule, uncited steps, the fallback, arm E, unknown cases, maturity and review mode).

**Live check** (`make gate1` with `--compose C`, 4 cases, `eval/results/gate1-20260928T121915.json`):

- GATE-C2 (I3): `-HOLD_PO` citing PR-2026-0312. `EXPEDITE_PO`, `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT`
  kept.
- GATE-C1 (I1): `-ROUTE_DELEGATE +ROUTE_NEXT_LEVEL_APPROVER` citing PR-2026-0360.
- GATE-K1: one-click, established.
- GATE-U4: escalated. Reflect's uncited `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT` were dropped by
  validation, and the floor added `DECLARE_CONFLICT_OF_INTEREST`.
- New `--compose C|D|E` option on `scripts/gate1.py` prints each case's procedure, diff and flags.

## 2026-09-28 · Phase 1 → 2 · Gemini fallback restored; Gemini timeout

- The user restored `GEMINI_API_KEY` in `.env`. Verified: both model IDs listed, and one live fallback call
  through `llm.py` on `gemini-3.7-flash` returned valid verdicts (C1 partial, C2 no).
- **That single request took 291 s** (no retries); an earlier one took 93 s. Added
  `gemini_timeout_s: 90` (`config/models.yaml`), passed as `timeout` to `interactions.create` and as
  `http_options.timeout` to `generate_content`. A slow Gemini call now fails over, then escalates, rather
  than blocking for minutes.
- Phase 2 started. The category-source question (vendor master vs extraction) is still open; SPEC §9
  (extraction) stays in force until the user decides.

## 2026-09-28 · Phase 1 · Gate G1 run 2: PASS (reported result)

- `eval/results/gate1-20260928T111232.json`, with the `llm.py` 429 fix and `verifier-v2`:
  - **false confidence 0 of 15**;
  - **classes correct 13 of 15**;
  - **citations resolved 52 of 52**;
  - failed checks found exactly 15 of 15;
  - novel-combination flag right on 5 of 5 composed cases;
  - C1 and C2 now match their interaction precedents (I1, I3) with verdict yes;
  - 15 LLM calls (+14 cached extractions), 28,318 tokens, 178 s.
- Remaining misses: **GATE-K4 and GATE-K5 are generalized, not known.** The extractor classed both as
  `indirect_mro`, and the verifier correctly gave "partial" for the category difference.
  - The cause is a design question, not a model error: SPEC §9 takes category from extraction, while the
    vendor master also has a category.
  - It's **left for the user to decide** (take category from the vendor master, or keep extraction).
  - Labels and cases were not changed.
- **Measured token costs on real cases** (`gpt-oss-120b`): extraction ~805 tokens (n=15); verifier ~1,962
  tokens (n=27), mostly reasoning (~670) with only ~96 output tokens.
  - `scripts/estimate_budget.py` now uses the largest per-role average measured on real cases, falling back
    to the Phase 0 spike.
  - Result: Groq serves ~100 case verifications a day; **full plan 12 quota-days, reduced 8** (from 21 and 15).
  - The quota figures in CLAUDE.md and SPEC §14.5 were updated to match.
- **Open:** `GEMINI_API_KEY` is missing from `.env`, so both Gemini fallbacks currently fail. The user
  needs to restore the line.

## 2026-09-28 · Phase 1 · Gate G1 run 1 and fixes

- **Run 1** (`eval/results/gate1-20260928T110640.json`): **PASS**.
  - False confidence 0 of 15; classes correct 12 of 15; citations resolved 47 of 47; failed checks found
    exactly 14 of 15; 34,519 tokens.
  - Misses:
    - **GATE-C2** escalated: Groq returned a TPM 429 ("try again in 3.07 s"), the limiter sent the call to
      the Gemini fallback, and that failed because **`GEMINI_API_KEY` is not set in `.env`** (the app only
      finds the Groq and Hindsight keys).
    - **GATE-K4 and GATE-K5** came out generalized: the extractor classed "coolant + pump kit" and "air
      gauging units" as `indirect_mro`, while the labels assumed direct material. The extractor prompt lists
      gauges under indirect MRO, so the case design was inconsistent with it. **Labels and case text were not
      changed after seeing results.**
- **Fix, `llm.py`** (verified behaviour):
  - A 429 asking for a wait of 60 s or less (`SHORT_429_S`, a per-minute limit such as Groq's TPM) now waits
    and **retries the same model**. Only a longer (daily) 429 moves to the next model.
  - The TPM bucket is lowered to Groq's `x-ratelimit-remaining-tokens` after every response. Groq counted
    2,898 requested tokens where the bucket had estimated less.
  - Tests: two for 429s and one for the header sync (92 in total).
  - CLAUDE.md's fallback-order and rate-limiter lines were updated to match.
- **Fix, verifier prompt `verifier-v2`:** in run 1 it gave "partial" with the difference "required
  procedural steps not confirmed" (K4, and C1's budget and interaction candidates). It was treating a
  precedent's resolution steps as conditions. The system text now says a precedent's steps are how that
  case was resolved, not conditions the new request must show. This is a general wording fix, not specific
  to any case.

## 2026-09-28 · Phase 1 · detector built (SPEC §4, §5, §8, §9)

**Engine** (`api/engine/`)

- `types.py`: shared dataclasses (request facts, master-data snapshot, violations, coverage, classification),
  plus `amount_band`, `fiscal_year` and `tag_for`.
- `rules.py`: the six checks plus the related-party signal.
  - Boundaries are inclusive: ±5% for duplicates, 30 days for bank changes, a certificate expired only if
    its expiry is before the request date, three quotes above ₹2,00,000.
  - A vendor failure reports its most severe cause (`blacklisted` > `gst_cancelled` > `cert_expired`) and
    lists every problem in the detail.
  - **Decision (verified need):** both a ledger bank change and a change claimed only in the text use one
    cause, `bank_details_changed`, told apart by `source`. That keeps them the same cause for precedent
    matching (SPEC §4 maps the claim to a `bank` violation).
- `normalise.py`: rupee amounts ("4.8L", "₹4,80,000", "1.2 cr", "60k") and vendor-name matching, in code.
- `extractor.py`: one cached LLM call per request (prompt `extractor-v1`) proposes category, urgency and
  signals. **Code drops any signal whose span isn't verbatim in the source it names** (SPEC §4 adversarial
  rule). The amount comes from the form, falling back to the text; parsing is in code.
- `detector.py`:
  - Per-violation recalls run in parallel, plus an interaction recall by combo tag.
  - Candidates are built through citations, deduplicated by case, top 5. Policy memos are kept apart as
    context, not candidates.
  - **One verifier call per case** (prompt `verifier-v1`, cached per request and content).
  - **Code guards that only ever lower a verdict:** a missing verdict becomes `no`; a different cause for
    the same check in the ledger forces `no`; a `yes` with no cited case in the same amount band and
    category becomes `partial`.
  - Aggregation per SPEC §5.2: best verdict, then precedent strength, then recency.
  - A lesson dated before a policy change on the same tag is flagged (SPEC §8.8 backstop).
- `classify.py`: SPEC §5.3, pure.
- `pipeline.py`: SPEC §9 stages 1–6. Every stage writes to the ledger. If memory or the LLM fails, every
  check is set uncovered and the case escalates with "Memory unavailable, escalating to a human" (rule 11).

**Memory** (`api/memory/`)

- `backend.py`: the `MemoryBackend` protocol, with `MemoryItem`, `Hit`, `RecallResult` and
  `MemoryUnavailable`.
- `hindsight_backend.py`: bank setup (missions, disposition, directives, idempotent), retain via
  `aretain_batch` with `per_tag` scopes, and recall with source facts (`max_source_facts_tokens=-1`).
  Every call gets one retry, then `MemoryUnavailable`. It also has consolidation polling, and
  `bank_exists` via `list_banks` (a missing bank's config GET returns 404 and does not auto-create).
- `citations.py`: fact → `document_id` or `metadata.case_id`; observation → `source_fact_ids` → the
  response's `source_facts`. It strips `-override-n`, never guesses a missing source fact, and drops IDs
  the ledger doesn't know.
- **Verified change (api-notes D15):** interaction recall uses `combo:<checks>` tags for every subset (two
  or more) of the failed checks, not `tags=["interaction"]`. With `per_tag` scopes, the `interaction`
  observation carries only that tag and would merge every combination.

**Ledger** (`api/ledger.py`)

- All SPEC §11 tables. **Deviations:**
  - a new `approval_limits` table (the approval matrix the approver check needs);
  - `requests` gains `vendor_name_raw`, `amount_raw` and `quotes_count`, and uses `case_class` because
    `class` is reserved;
  - `vendors` gains `cert_name`;
  - `lessons` gains `checks`, `causes` (per check), `amount`, `category`, `urgency` and `vendor_id`, the
    exact record the verifier prompt and code guards use;
  - `coverage` gains `candidate_id`, `memory_type`, `guard` and `combo`.
- There's no `step_library` table: the library stays in `config/step_library.yaml`.
- The LLM log, quota counters and cache always live in the main database, because Groq's rolling window is
  counted from it. Gate and benchmark runs may keep their case ledger in their own database.

**Config**

- `config/memory.yaml`: the SPEC §8.2 missions, disposition and directives, plus recall and consolidation
  settings.
- `config/verdict_guide.md`: the SPEC §5.1 text, shared with `LABELLING_GUIDE.md`. An early draft added
  example conditions ("production line down", "overrun up to 10%") that matched a gate case. They were
  **removed** so the guide isn't tuned to the gate.

**Scripts and data**

- `scripts/import_history.py` (minimal): history records → ledger `lessons` / `policy_changes` /
  `experiences`, plus retains in the SPEC §8.3 template. Tags follow §8.3, so interactions carry only
  `interaction` and `combo:`. The CSV import is Phase 2.
- `scripts/gate1.py` and `make gate1`:
  - rebuilds `data/gate1/gate1.db` every run;
  - reuses the bank `kaveri-gate1-<hash of history.json>` unless `--reseed`;
  - scores against `data/gate1/expected.json`, which **only this script reads**;
  - writes `eval/results/gate1-<time>.json`.
- `data/gate1/`, all synthetic:
  - `master.json`: 15 vendors, 14 employees, the approval matrix, 2 delegations, FY 2026-27 budgets and
    1 prior request;
  - `history.json`: 16 records (two per family E1–E6, the post-July capex E3, I1, I3 and the policy memo;
    no U1, U2 or I2);
  - `cases.json`: 15 borderline cases;
  - `expected.json`: the labels.
- The gate labels were written by the engine builder (this session), not a separate data owner. They are
  development-gate labels, kept apart from `data/ground_truth/`.

**Timezones:** request and resolution times are IST (`settings.IST`); logs are UTC. SQLModel 0.0.47 refuses
naive datetimes.

**Tests:** 90 in total, adding `test_rules` (34), `test_classify` (6), `test_citations` (8, on the Phase 0
fixtures), `test_extractor` (5) and `test_detector` (14).

## 2026-09-28 · Phase 0 → 1 · SPEC.md updated for the Groq + Gemini models (decided by user)

- 23 edits across §3 (repo layout comments), §5.2, §8, §10 M11, §11 `quota_usage`, §14.1, §14.5, §15.1 demo
  controls, §17 (Phase 0 row and prompt), §19 adoption, §20 risks, and Appendix A.
- Every call from our code now names `openai/gpt-oss-120b` on Groq's free tier, with `gemini-3.8-flash`
  then `gemini-3.7-flash` as fallbacks. Quota text now says Groq's tokens per day are the binding limit.
  Adoption text now says production runs Groq with Zero Data Retention or the customer's own provider.
- Why: the user moved the primary model to Groq and asked for SPEC to match.

## 2026-09-28 · Phase 0 · CLAUDE.md LLM section rewritten (decided by user)

- **Only three models, only free tiers:** `openai/gpt-oss-120b` (Groq, primary for every role), then
  `gemini-3.8-flash`, then `gemini-3.7-flash`. Adding another model or provider, using a paid tier, or
  suggesting either is ruled out.
- Also rewritten: calling details, fallback order, effort levels, quota rules (Groq TPD binds, rolling
  24 h; Gemini resets at midnight Pacific), the order of token-saving levers, and the data rule for both
  providers.
- Hindsight note: arm C composes with Hindsight Cloud's undisclosed model and arm D with `gpt-oss-120b`.
- Added a "How to work" rule: record every change in this file.

## 2026-09-28 · Phase 0 · Groq added as the primary LLM (decided by user)

- Why: Gemini's free tier is 20 RPD per model (user's AI Studio screenshot), and `make budget` put the
  reduced benchmark at 98 quota-days on Gemini alone.
- `api/llm.py` rewritten to be provider-aware:
  - Groq over `httpx` (no new dependency) with strict `json_schema`, `reasoning_effort`,
    `include_reasoning: false` and `max_completion_tokens` 8,192.
  - Fallback chain: 2 retries on the primary, then one attempt on each fallback. A 429 or other 4xx goes
    straight to the next model.
  - `strict_schema()` adds `additionalProperties: false`, which Groq's strict mode requires.
  - Groq usage is counted over a rolling 24 h (verified: `x-ratelimit-reset-requests` of 86.4 s per
    request). TPD is enforced from `llm_calls`. The request count is synced from Groq's headers for
    Pacific-day models only.
- `config/models.yaml`:
  - `providers` map; `fallbacks` list.
  - Per-role `effort` replaces `thinking_level`.
  - `gemini_call_style: interactions`.
  - `groq:` block.
  - `est_output_tokens: 1500`, used to reserve TPM and TPD before a call and trued up after.
- `config/limits.yaml`: Groq `openai/gpt-oss-120b` at RPM 30, RPD 1,000, TPM 8,000, TPD 200,000 with
  `daily_window: rolling_24h` (user's Groq console screenshot).
- `scripts/estimate_budget.py`: the chain is the primary plus fallbacks. Capacity per model is
  min(RPD, TPD ÷ tokens per request), discounted by measured attempts per success. Tokens per request are
  the largest measured per-case-size call (4,027 tokens, verifier at `medium`). Result: full plan 21
  quota-days, reduced 15.
- `scripts/phase0_spike.py`: new `--part groq`.
- `docs/api-notes.md`: new rows D13 and D14 and a Groq section. `.env.example`: `GROQ_API_KEY`.
- Tests grew from 15 to 21: strict schema, call-style routing, 4xx handling, the TPD quota, header sync and
  the rolling window.

## 2026-09-28 · Phase 0 · Gemini limits recorded (supplied by user)

- `config/limits.yaml`: `gemini-3.8-flash` and `gemini-3.7-flash` each at RPM 5, TPM 250,000, RPD 20.
  `fallback_has_own_quota: true`, because AI Studio shows a separate counter per model.
  `reserve_requests_per_day` went from 10 to 0, since development is already an allowance line in the plan.
- `api/llm.py`: 429 responses now count toward the daily request counter. AI Studio showed 19 used where
  the ledger had counted 17, so today's counter rows were raised to AI Studio's figures (19 and 10).
- `make budget` no longer recommends "REDUCED" when the reduced plan also misses the 4-day threshold.

## 2026-09-28 · Phase 0 · setup and verification

**Environment**

- Python 3.12 virtualenv in `.venv`, with `hindsight-client` 0.10.1, `google-genai` 2.25.0, fastapi,
  uvicorn, pydantic 2, sqlmodel, httpx, pyyaml, pytest and ruff (`requirements.txt`).
- `sentence-transformers` is listed but not installed yet; arm D needs it from Phase 3.
- GNU make 4.4.1 installed with winget (`ezwinports.make`). It needs a new shell to be on PATH.
- The US Pacific DST rule is written out in `api/settings.py` because Windows has no tz database and
  `tzdata` isn't a listed dependency.

**Repo**

- Moved `SPEC.md` to `docs/SPEC.md`, where CLAUDE.md and SPEC §3 expect it.
- Scaffolded per SPEC §3: `api/` (`settings.py`, `ledger.py` with the Phase 0 tables `llm_calls`,
  `quota_usage` and `llm_cache`, `llm.py`, `memory/hindsight_backend.py` with only a client factory),
  `config/` (models, limits, assumptions, step_library, conflicts), `scripts/` (`phase0_spike.py`,
  `estimate_budget.py`), `tests/`, `Makefile`, `.gitignore`, `.env.example`, `pyproject.toml`.
- `.env` variables renamed to `GEMINI_API_KEY` and `HINDSIGHT_API_KEY` (values untouched), and
  `HINDSIGHT_BASE_URL` added.
- ruff ignores E501; the formatter owns line length, and long seed-narrative literals stay intact.

**Verified API behaviour** (details in `api-notes.md`, rows D1–D12)

- Hindsight:
  - Extraction mode is a bank setting. **`concise` chosen**: both modes kept all step codes (5 of 5 seeds),
    but `verbose` collapsed 2 of 5 seeds into one fact each.
  - `observation_scopes` is set through `retain_batch` only; `"per_tag"` is used.
  - Recall must include `world`, because Hindsight types most case facts as `world`.
  - Reflect's `response_schema` must be inlined. With `$ref`, it silently flattened objects to strings.
  - The client does spell it `include_facts`.
  - Observations are revised in place, with history available through `get_observation_history`.
  - Cloud's LLM can't be chosen or seen.
  - Consolidation took 4.1 s from a retain returning to the observation including the new case.
- Gemini:
  - The Interactions API was chosen after `generate_content` got 21 "high demand" 503s in 25 attempts.
  - `medium` thinking on 3.8-flash took 43 s.
  - The 429 body reported a limit of 5 (the per-minute limit).
- Fixtures: 20 Hindsight, 5 Gemini and 7 Groq, in `tests/fixtures/`. Measurements are in
  `docs/phase0_results.json`. Both scratch banks were deleted.

**Gate G0:**

- Passed: every call is verified, fixtures are recorded, the consolidation delay is measured, the fallback
  is confirmed, and the Hindsight LLM question is answered.
- `make budget` shows neither plan fits in 4 quota-days (full 21, reduced 15). The user chose to proceed
  on free tiers and decide the scope cuts at G1, using measured numbers.
