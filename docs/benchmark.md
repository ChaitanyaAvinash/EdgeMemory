# Benchmark

> **Status: not run yet.** The 60 case specs are written (`data/cases/specs.json`); their narratives and the
> blind ground truth are not (SPEC §13). This page states the protocol and expectations in advance. Results
> will be added per case, as counts, once the runs happen.

## Dataset (SPEC §13)

- 60 synthetic case specs: 20 dev and 40 test, stratified by the SPEC §13 class mix.
- All 8 interaction cases (2 I1, 2 I3, 4 held-out I2), the 3 post-July capex approver-away cases (M6) and
  the 3 cases after an override (M7) are in the test split, so those metrics are scored on data never used
  for tuning.
- Each spec states the checks its scenario is built to fail. `make specs` confirms, in code and without an
  LLM, that the six ledger checks against `data/master/master.json` fire exactly those. That tests how the
  data was built, not what the system answers.

## Arms (SPEC §14.1)

| Arm | What it is | Isolates |
|---|---|---|
| A | No memory: the policy document, a ledger extract and the request, one LLM call | — |
| B | Plain RAG: A plus top-k vector search over the seed narratives (2,048-token budget) | What a generic RAG agent gets |
| C | **EdgeMemory**: the full pipeline with Hindsight | — |
| D | The same pipeline with a plain vector store: cosine top-k, one LLM call composes, and no consolidation or temporal reasoning | **What Hindsight adds** (C vs D) |
| E | C without interaction recall or reflect: the plain union, then default conflict resolution, then the floor. It reuses C's coverage from the same run | **What interaction composition adds** (C vs E) |

**Models:**

- Every call from our code uses `openai/gpt-oss-120b` on Groq's free tier. Any case that fell back to
  `gemini-3.8-flash` or `gemini-3.7-flash` is listed with the results (metric M11).
- **Arm C composes with Hindsight Cloud's own model, which Cloud neither discloses nor lets us choose.
  Arm D composes with `gpt-oss-120b`.** So C vs D also differs in the composing model. This is a known
  confound, stated here in advance.

## Protocol (SPEC §14.2)

1. The ground truth is written blind by someone who doesn't build the engine, and frozen before any run.
   The format is in [ground_truth_format.md](ground_truth_format.md).
2. Tuning happens only on dev. The test split runs **once per arm**.
3. Every run gets a fresh memory bank, seeded identically.
4. Arms B, C and D get the same retrieved-context budget.
5. Results are reported as counts ("x of n"), with per-case rows in `eval/results/`.

## Metrics (SPEC §10)

All metrics are computed in `api/metrics.py` from the run files and the ground truth.

| ID | Metric |
|---|---|
| M1 | False confidence (target 0) |
| M2 | Risk-floor violations |
| M3 | Classification confusion matrix |
| M4 | Procedure F1 |
| M5 | Interaction accuracy, and the novel-combination flag rate |
| M6 | Outdated-lesson use |
| M7 | Post-override correctness |
| M8 | Review effort per 10 cases |
| M9 | Estimated analyst minutes, using the ASSUMPTIONS in `config/assumptions.yaml` |
| M10 | Unnecessary escalations |
| M11 | Cost and latency |

**M11 tokens** count only the calls our code makes (`llm.py`). A call served from the output cache is charged
the tokens of the original call it replays, so every arm is priced as an uncached run. Arm E needs the same
extraction and verification as C, so it's charged the same. Hindsight Cloud's own LLM usage (retain,
consolidation, reflect) runs on Cloud's credit and **isn't included** in C's or E's figure.

## Test set used: reduced (SPEC §14.6)

`make budget` put the plan over §14.6's 4-quota-day threshold, so the test runs use 24 of the 40 test cases,
listed in `data/cases/test_reduced.json`. The 24 were chosen by spec family before any test ground truth
existed. They keep all 8 interaction cases, the 3 post-July capex cases (M6), the 3 override cases (M7) and all
4 unknowns. Every arm runs on the same 24.

## Test results (24 cases, run once per arm)

Report `eval/results/report-test-20260928T222947.json`; runs `run-bench-test-<arm>-test1.json`. The ground truth
was frozen before any test prediction was scored (`data/labelling/FROZEN.json`). Every call in every arm ran on
`openai/gpt-oss-120b`: no Gemini fallback, and no `llm_unavailable` case.

| Measure | A | B | **C** | D | E |
|---|---|---|---|---|---|
| False confidence (M1) | 3 of 5 | 1 of 5 | **0 of 5** | 0 of 5 | 0 of 5 |
| Floor violations (M2) | 7 of 9 | 4 of 9 | **0 of 9** | 0 of 9 | 0 of 9 |
| Classes correct (M3) | 11 of 24 | 15 of 24 | **21 of 24** | 21 of 24 | 21 of 24 |
| Procedure F1, macro (M4) | 0.472 | 0.843 | **0.798** | 0.797 | 0.758 |
| Interaction exact match (M5) | 0 of 8 | 0 of 8 | **3 of 8** | 3 of 8 | 0 of 8 |
| Interaction mean F1 (M5) | 0.174 | 0.794 | **0.739** | 0.843 | 0.672 |
| New combination flagged (M5) | 0 of 4 | 0 of 4 | **4 of 4** | 4 of 4 | 4 of 4 |
| Outdated-lesson use (M6) | 0 of 3 | 0 of 3 | **0 of 3** | 2 of 3 | 3 of 3 |
| Post-override correct (M7) | 1 of 3 | 3 of 3 | **0 of 3** | 0 of 3 | 0 of 3 |
| Review effort per 10 cases (M8) | 25.4 | 37.5 | **28.3** | 39.6 | 35.8 |
| Est. minutes per 10 exception cases (M9) | 270.0 | 206.4 | **189.5** | 166.4 | 204.5 |
| Unnecessary escalations (M10) | 10 of 17 | 3 of 17 | **3 of 17** | 1 of 17 | 3 of 17 |
| Tokens per case (M11) | 2,300 | 4,374 | **3,699** | 6,931 | 3,699 |
| p50 latency (M11) | 17.0 s | 32.7 s | **27.0 s** | 48.4 s | 27.0 s |

Per case:

- **False confidence:**
  - A: TEST-016, TEST-022, TEST-037.
  - B: TEST-036.
- **Floor violations:**
  - A: TEST-005, 007, 019, 022, 024, 025, 037.
  - B: TEST-005, 007, 019, 025.
- **Misclassified:**
  - C: TEST-001, 013, 027.
  - D: TEST-002, 013, 027.
  - E: TEST-001, 013, 027.
- **Outdated-lesson use:**
  - D: two of TEST-002, 004, 039.
  - E: all three.
- **Post-override:**
  - C: TEST-013 and TEST-027 were escalated to a human.
  - TEST-020 was classed `known` with an **empty step list, no flag and no escalation**. That's a defect: it
    breaks "fail visibly". It's recorded here as a result, not re-run.

**Against the expectations written before the runs:**

- **"C should beat E on interaction cases":** held, 3 of 8 exact against 0 of 8. E also used the outdated
  pre-July lesson 3 of 3 times, against C's 0.
- **"C should beat D on post-override correctness, outdated-lesson use and learning speed":**
  - **Outdated-lesson use:** held, 0 of 3 against 2 of 3.
  - **Learning speed:** held in the replay below, 8 of 22 one-click against 4 of 22.
  - **Post-override correctness:** didn't hold. Both scored 0 of 3.
- **Where C and D tie:** M1, M2, M3 and M5 exact. The shared pipeline (per-check coverage, the verifier, the
  floor) is what produces those.
- **Where D is ahead:** interaction mean F1 (0.843 against 0.739), unnecessary escalations (1 against 3) and
  estimated minutes.
- **"B may match C on plain known cases":** B did better than that.
  - B scores 3 of 3 after overrides, against C's 0 of 3, and 0.971 procedure F1 on known cases, against C's
    0.571. Its macro F1 is also higher (0.843 against 0.798).
  - The override cases are C's clear weakness. From C's run ledger (`data/runs/bench-test-C-test1.db`):
    - **TEST-013 and TEST-027:** the verifier correctly rejected the original lesson, because the override's
      condition applies. The override's own resolution wasn't recalled as a separate candidate, so the check
      was left uncovered and escalated. That's safe, but it's a miss.
    - **TEST-020:** the verifier matched the override precedent (PR-2026-0735, "yes"). But the composer builds
      a single-check lesson only from experience and confirmation cases (`composer.single_lesson`), so an
      override-only match gave an empty lesson and an empty procedure, with nothing flagged.
  - B has neither step; it reads the override narrative directly.
  - **Fixed after the test run (29 Sep), without re-running the test split:**
    - overrides merged into a lesson's memory are now judged as their own candidates;
    - a verified override supplies the lesson;
    - an empty procedure is escalated.
  - The published test numbers above are from the code as it was. The fix was checked on the four dev cases
    it can affect (no change) and on the demo's override beats.
- **Where B falls down:** B is also unsafe where C isn't. It gave 1 of 5 unknowns a confident answer, and 4 of 9
  cases missed a required safety step. EdgeMemory's claim is zero false confidence with the floor held, and
  on that C, D and E are the only arms at 0.

## Learning curves (SPEC §14.4, test split)

Files: `eval/results/replay-hindsight-test-test1.json` and `replay-vector-test-test1.json`.

**Method:**
- Each backend starts from an empty memory and walks the 45 seeds and the 24 labelled test cases in date order.
- After each case, a simulated reviewer retains the frozen ground-truth resolution through the same decision
  path as the UI.
- False confidence is judged against what memory holds at that point. A check the ground truth calls uncovered
  stops counting as uncovered once an earlier replayed case with the same check and cause has been resolved.

| Measure (22 exception cases) | Hindsight (C) | Vector (D) |
|---|---|---|
| False confidence | 0 of 22 | 0 of 22 |
| One-click reviews | 8 of 22 | 4 of 22 |
| Mean reviewer effort per case (M8 units) | 2.82 | 3.77 |
| Escalations | 5 | 6 |
| Classes correct (all 24) | 20 of 24 | 19 of 24 |

Rolling one-click share (last 10 exception cases, at each position):

- Hindsight: 0, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 4, 3, 2, 1, 2, 3, 3, 3, 3, 3, 3
- Vector: 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 2, 2, 2, 2, 2, 3

**Maturity (C3), Hindsight replay:**
- The held-out I2 combination (certificate expired plus sole source) first appeared at TEST-011. It was
  composed from the two single-check lessons for step-by-step review.
- Its lesson was *tentative* at TEST-015, after one resolution, and *established* at TEST-030.
- The related-party and GST cases (TEST-036, TEST-037) came after one resolved case each. They got tentative
  step-by-step procedures instead of an escalation.

**Read with care:**
- **The curve isn't monotonic.** Hindsight's one-click share dips in the middle, around the override and unknown
  cases, and then recovers.
- **One infrastructure escalation per backend.** TEST-032 (Hindsight) and TEST-019 (vector) were escalated
  because the batched verifier prompt went over Groq's 8,000-token single-request cap (HTTP 413; see
  `docs/api-notes.md`), and both Gemini fallbacks were out of quota. That's safe, but it isn't a judgement.
- **Small and simulated.** The sample is 22 exception cases, and the reviewer is the ground truth, not a person.

## Dev results (tuning split, 20 cases)

Report `eval/results/report-dev-20260928T173805.json`. Runs: A `dev1`, B `dev1`, C and E `dev3`, D `dev1`.

| Arm | False confidence | Floor violations | Classes correct | Procedure F1 (macro) | Review effort / 10 | Est. minutes / 10 exception cases | Unnecessary escalations | Tokens / case | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| A | 3 of 4 | 6 of 8 | 8 of 20 | 0.642 | 31.0 | 183.8 | 3 of 12 | 2,225 | 16.6 s |
| B | 3 of 4 | 4 of 8 | 10 of 20 | 0.854 | 28.5 | 138.8 | 2 of 12 | 4,189 | 31.2 s |
| C | 0 of 4 | 0 of 8 | 20 of 20 | 0.923 | 21.0 | 132.5 | 0 of 12 | 3,078 | 12.0 s |
| D | 0 of 4 | 0 of 8 | 19 of 20 | 0.872 | 22.0 | 136.9 | 0 of 12 | 5,345 | 44.1 s |
| E | 0 of 4 | 0 of 8 | 20 of 20 | 0.923 | 24.5 | 145.0 | 0 of 12 | 3,078 | 12.0 s |

Per case:

- **False confidence:** A and B on DEV-010, DEV-019, DEV-020.
- **Floor violations:**
  - A: DEV-001, DEV-010, DEV-013, DEV-014, DEV-017, DEV-018.
  - B: DEV-001, DEV-017, DEV-018, DEV-019.
- **Misclassified:** D on DEV-013. The full A and B lists are in the report file.

**Read these with care:**

- **Dev is the tuning split.** The verifier prompt (v2 to v4), the composer's validation rules and the
  approver-delegate rule were all changed in response to dev failures. C's 20 of 20 is tuning-set performance
  and says nothing yet about unseen cases. That's what the test split is for.
- **C and E tie here** because dev holds no interaction cases, and M5 to M7 have no cases on dev (each is
  "0 of 0"). The interaction, override and outdated-lesson cases are all in the test split.
- Minutes use the ASSUMPTIONS in `config/assumptions.yaml`; they're estimates, not measurements.
- 20 cases is a small sample.

## Quota plan (SPEC §14.5, §14.6)

- `make budget` projected the whole plan at 12 quota-days full and 9 reduced, so the **reduced benchmark
  (§14.6) was used**: 24 test cases, no arm F.
- The test runs and replays ran between 18:10 and 22:30 UTC on 28 Sep 2026. They used four Groq API keys
  supplied by the user, each on the free tier. The runner resumes across quota stops without scoring a stop as an escalation.

## Honest expectations (written before the runs)

- B may match C on plain known cases. If so, we'll say so.
- C should beat E on interaction cases.
- C should beat D on post-override correctness, outdated-lesson use and learning speed.
- If C doesn't beat D, we'll report it and explain why.

## Limits

- The data is synthetic and covers one domain.
- The sample is small: 60 cases, with a reduced test set if §14.6 applies.
- The minutes are estimates.
- **Labelling (dev):** the first labeller was the engine-building Claude Code session, which had read part of
  the case-design notes, so the labels are not blind in SPEC §13's sense. The second labeller was an
  independent Claude Code subagent with a fresh context, not a person. Agreement before adjudication: 11 of 20
  cases on every field (class, failed checks, causes and uncovered checks: 20 of 20); after the user
  adjudicated two conventions: 20 of 20. It shows consistency with the rules, not independent human judgement.
- **Labelling (test):**
  - One labeller: a separate Claude session with a fresh context, the same model family that builds the
    system.
  - It saw only the worksheet, the seed history, the policy and the guide, never system output.
  - There is no second labeller. The labeller's 7 judgement calls are listed in
    `data/labelling/test_labeller_notes.md`.
  - The file was frozen before any test prediction was scored.
- The case specs and the engine come from the same small team, which the blind ground truth and the second
  labeller only partly offset. The 60 specs were written, at the user's request, in the same Claude Code
  session that built the engine.
