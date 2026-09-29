# Content outlines (each team member writes their own piece)

These are outlines only, for the hackathon's content deliverables. Use real numbers from `eval/results/` and
`docs/benchmark.md`, never estimates. Always say the data is synthetic.

## Article: "Automation encodes the happy path. What about the exceptions?"

1. **The problem, told through Ananya and Ravi.** Tacit exception knowledge, and what happens when the
   senior analyst is away.
2. **Why "just use an LLM" fails.** It is confidently wrong, with nothing to cite. Show the related-party
   case that plain RAG waved through, and say it was a 3-case smoke run, not the benchmark.
3. **Per-check coverage.** How one rule gives known, composed and unknown.
4. **The "a PO is not a payment" moment:** why two lessons together aren't their union.
5. **What Hindsight adds.** Lessons that consolidate, mature (tentative → established), get revised by an
   override in context, and are dated by a policy change. Include the before/after lesson text from
   `docs/memory-design.md`.
6. **The safety rails in code.** The floor, the removal rule, citations. The LLM proposes, code verifies, a
   human decides.
7. **Results and limits.** Counts only, and link the per-case results.

## Social post (short)

- Hook: "Ravi is on leave. The ₹4.8L request has three red checks. What would he have done?"
- One screenshot of the case view: two interaction precedents change the plain combination, and the floor
  holds the payment.
- One line on memory: "one decision makes a tentative lesson; three make it one-click; one override revises
  it".
- Link to the repo and the video. The words "synthetic data" appear in the post.

## Video (3:00, with the 60-second cut first)

Follow SPEC §18 beat by beat, from **Demo controls** after `make reset seed`:

1. Hook (0:00–0:20).
2. First exception, unknown, resolved live (0:20–0:40).
3. Tentative, then established, with "replay 3 weeks" and the lesson panel diff (0:40–1:05).
4. The ₹4.8L composed case with I1 and I3 (1:05–1:40).
5. The override revises a lesson, and a similar case follows it (1:40–2:05).
6. The related-party case escalates (2:05–2:20).
7. The benchmark page, with real counts only (2:20–2:50).
8. Close (2:50–3:00).

Keep the recorded fallback ready. Warm up the demo bank with one recall first.
