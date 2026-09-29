# Adoption

## Where it plugs in

Requests arrive in one of two ways:

- by email, to a monitored approvals inbox;
- as a CSV or webhook export from whatever system holds the approval queue.

EdgeMemory returns each recommendation as an approval-note attachment (the procedure, a citation for every
step, and what is not covered). `GET /audit/export.csv` provides a full audit trail: every recommendation,
citation, verdict, safety-floor addition and human decision, with timestamps.

## Cold start

Export the last 12 months of exception tickets or approval emails into the CSV format of
`data/seed/history.csv`. Each row records one resolved case:

- the checks that failed, and why;
- the steps approved;
- the outcome, and the lesson.

`scripts/import_history.py` loads that into the ledger and into memory; the demo is seeded the same way.
Lessons with a single supporting case start as *tentative* and need step-by-step review. They become
one-click only after repeated agreement.

## Buyer and price (a hypothesis)

The likely buyer is the Head of Procurement or the Finance Controller at an Indian manufacturer with 500–5,000
employees. The price hypothesis is about ₹4,000 per analyst seat per month. This is a hypothesis, not tested
with customers.

## Data and model

- **Hackathon build:** Groq and Gemini free tiers, with synthetic data only. Free tiers may retain or use
  prompts: Google uses free-tier Gemini data to improve its products, and Groq keeps data for up to 30 days
  for abuse monitoring unless Zero Data Retention is on.
- **Production:** Groq with Zero Data Retention enabled, or the customer's own model provider. `api/llm.py`
  is the only file that changes.
- **Memory:** Hindsight Cloud, or a self-hosted Hindsight on the customer's infrastructure.

## Rollout

1. **Shadow mode:** EdgeMemory recommends, and analysts compare its recommendations with what they did.
2. **Step-by-step review, after about two weeks:** analysts tick each recommended step.
3. **One-click review** unlocks lesson by lesson, as established lessons build up.

Escalation of unknowns never switches off.

## Where else this works

The same mechanism, per-check coverage plus interaction-aware composition learned from human decisions,
applies to:

- accounts payable exceptions;
- IT change approvals;
- insurance claims.

## How it relates to procurement suites

Procurement suites automate the standard path, and some include AI assistants. EdgeMemory is complementary:
it learns *this team's own* exception decisions and cites them. Named products' features are not compared
here.
