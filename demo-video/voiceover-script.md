# EdgeMemory demo video: voiceover script

**Video:** `edgememory-demo.mp4`, 4:50, 1920×1080, 30 fps, no audio. It was recorded from the running app
(web on :3000, API on :8000) against a freshly reset and seeded demo bank. Every case, Groq call and Hindsight
retain and recall in it ran live. Long API waits are cut, and each cut is labelled on screen ("⏩ N s of live
API time trimmed").

**How to use it:** each timecode is where a shot starts, and each block is written to fit its shot at a relaxed
pace. Lines in *[brackets]* are cues, not narration. The chapter chip at the bottom left of the video matches
the section headings here.

---

## 1 · Intro (0:00 – 0:25)

**0:00 · title card**
> Hi, I'm *[your name]*. This is EdgeMemory, built for HackwithHyderabad on Hindsight by Vectorize.

**0:05 · home page, headline stats**
> It's a copilot for procurement exceptions. Normal automation encodes the happy path. EdgeMemory learns
> where that path breaks, and how your people fixed it.

**0:18 · "How it works" row**
> Rules detect what broke. Hindsight recalls how each problem was solved before. Lessons are composed into one
> procedure, a human decides, and Hindsight remembers the decision.

## 2 · The problem (0:25 – 0:57)

**0:25 · section card**
> Here's the problem.

**0:27 · the ₹4.8 lakh request, "Failed checks (3)" highlighted**
> A ₹4.8 lakh request. Line 3 is down, the budget is overrun, the approver is on leave, and the vendor changed
> its bank details twelve days ago. The rule engine says what broke, and nothing about what to do.

**0:39 · benchmark, column A highlighted**
> Ask a model that has the policy but no memory (that's column A) and it guesses. It was confident on 3 of 5
> cases that had no precedent, and it missed required safety steps in 7 of 9.

## 3 · Live demo (0:57 – 4:19)

**0:57 · section card, then Demo controls**
> Let's watch it learn. Everything from here runs live.

**1:02 · Run: ₹60,000 order, expired certificate** *[LIVE callout]*
> A ₹60,000 order whose vendor certificate expired six days ago. Code runs the checks, and Hindsight is
> recalled once for each failed check.

**1:04 · PR-DEMO-E1-01 reveal: "No verified precedent"**
> Nothing in memory covers it, and EdgeMemory says so. It marks the case unknown and hands it to a human.

**1:20 · resolution form**
> The analyst resolves it: hold the PO, request the renewed certificate, and keep the vendor active.

**1:25 · Save as edge experience** *[RETAIN callout]*
> Saving retains that decision into Hindsight, tagged with the check it fixed. That's retain, live.

**1:33 · one week later, a different vendor with the same problem** *[LIVE callout]*
> A week later, a different vendor has the same expired certificate.

**1:37 · PR-DEMO-E1-02: known · tentative · step by step**
> Now recall finds last week's decision, and the verifier confirms it applies. A lesson backed by one case is
> only tentative, so the analyst confirms it step by step.

**1:51 · "Why this step?" drawer** *[RECALL callout]*
> Every step shows what Hindsight recalled, the case behind it, and the verifier's verdict.

**2:01 · ticking steps, Confirm** *[RETAIN callout]*
> The confirmation is retained too.

**2:08 · Replay 3 weeks** *[RETAIN callout]*
> Fast-forward three weeks: two more cases are retained and consolidated.

**2:18 · Lessons page: step:vendor with the before/after diff**
> This is the lesson panel. The Hindsight observation is now consolidated from four cases, and the diff shows
> how it changed. A tentative lesson has become established, built only from human decisions.

**2:31 · Queue → the ₹4.8 lakh case, Replay reveal**
> Back to the ₹4.8 lakh case, where three checks fail at once.

**2:40 · stage 3: how each problem was resolved before**
> Each failed check gets its own recall, and each one has established precedents. Hindsight also recalls
> combinations. Bank plus budget applies. The verifier rejected approver plus budget.

**2:47 · stage 4: the plain combination, "Hold PO" struck through**
> Just adding up the single-check lessons says "hold the PO", and that keeps line 3 down.

**2:52 · stage 5: what changes when these problems occur together**
> But three past cases handled this exact combination: release the PO so the line restarts, and hold the
> payment instead. Only a verified interaction precedent can remove a step.

**2:59 · stage 6 · safety floor, stage 7 · procedure**
> The safety floor is applied last, and no lesson can go below it. With a bank change, the bank callback and
> the payment hold have to stay. The flags show code checking the model's work.

**3:07 · "Why this step?" on Expedite PO** *[RECALL callout]*
> This step comes from a Hindsight observation built from those three cases. No rule author wrote it.

**3:15 · Run: split shipment, vendor with a past duplicate-invoice incident** *[LIVE callout]*
> Now an override. A split shipment looks like a duplicate invoice, and the usual lesson links it to the
> master PO.

**3:22 · PR-DEMO-E4-01: no verified precedent, escalated**
> But this vendor has a history of duplicate invoices, so the verifier won't apply that lesson, and the case
> is escalated.

**3:34 · Reject form: reason pre-filled** *[RETAIN callout on submit]*
> The reviewer rejects it and sends it to audit, with a reason. That override is retained.

**3:51 · Lessons page: step:duplicate**
> Memory now holds the general lesson and a new one for vendors with that history.

**4:00 · PR-DEMO-U1-01: the brother-in-law email**
> Here's an honest limit. The vendor's owner is the requester's brother-in-law. There's no precedent, so
> EdgeMemory says so and escalates, and the safety floor adds a conflict-of-interest declaration.

## 4 · Wrap up (4:19 – 4:50)

**4:19 · section card → benchmark, column C highlighted**
> On 24 blind-labelled test cases, EdgeMemory was falsely confident on 0 of 5 and missed 0 of 9 safety steps.
> It got 3 of 8 interaction cases exactly right, against 0 of 8 without interaction learning.

**4:35 · learning curve summary**
> With Hindsight, 8 of 22 reviews became one-click, against 4 of 22 with a plain vector store.

**4:38 · what surprised us** *(keep talking over the end of the benchmark and into the card)*
> What surprised us: under one broad tag, Hindsight merged every combination into a single lesson, so now we
> tag each combination separately. And plain RAG still beats us after overrides, 3 of 3 to 0 of 3. That's
> what we fix next.

**4:41 · closing card, until 4:50**
> EdgeMemory recommends. Your people decide. Hindsight remembers what they decided.

---

### Notes for the edit

- **Length:** about 640 words over 4:50, roughly 130 a minute, which leaves pauses while the reveals play. If you
  run long, drop the flags sentence at 2:59 first, then the RAG sentence in the surprise.
- **The split-shipment beat** didn't play exactly as `docs/demo-runbook.md` describes. The verifier refused the
  usual "link to the master PO" lesson for this vendor, so the case escalated instead of recommending the link
  for the reviewer to reject. The script describes what's on screen.
- **Synthetic data:** the footer on the cards and the app header both say the data is synthetic. Keep them
  visible, since the rules require that label in the video.
- **Numbers:** every number here is on screen (the app computes it) or in `docs/benchmark.md`.
- **60-second cut:** 0:27–0:39 (hook), 2:37–3:07 (composed), 3:22–3:51 (override).
