# Ground-truth format (for the data owner)

The data owner writes the ground truth **blind**, from the case specs, using `LABELLING_GUIDE.md`. That guide
copies `config/verdict_guide.md` word for word and adds the family rules (SPEC §13). It is frozen at Gate G2.
The engine never reads it (CLAUDE.md rule 10); only `eval/report.py` does.

**What to label from.** The 60 specs are in `data/cases/specs.json`, and each case's generated text is in
`data/cases/<split>/<case_id>.json`. Two spec fields exist to help you, and neither is an answer:

- `ledger`: the master-data facts on the request date (vendor status, certificate, bank change, budget,
  approver and delegation, earlier requests, quotes), which the request text needn't mention.
- `scenario_checks`: the checks the scenario was built to fail. `make specs` confirms them in code.

The class, the uncovered checks and the steps are yours to decide, using the verdict guide, the family rules
and the seed history in `data/seed/history.csv`. SPEC §13 gives the human answer for U1, U2 and I2. For any
other uncovered check, decide the human answer from the policy in `data/seed/policy.md` before any run.

One file per split: `data/ground_truth/dev.json` and `data/ground_truth/test.json`.

```json
{
  "labeller": "name or role",
  "second_labeller": "name or role (dev only)",
  "frozen_at": "2026-10-01",
  "cases": {
    "DEV-001": {
      "class": "composed",
      "failed_checks": ["bank", "budget"],
      "causes": {"bank": "bank_details_changed", "budget": "overrun"},
      "uncovered_checks": [],
      "steps": ["EXPEDITE_PO", "VERIFY_BANK_CALLBACK", "HOLD_PAYMENT", "ALLOW_BUDGET_OVERRUN",
                "ATTACH_LINE_DOWN_EVIDENCE", "ADD_CONTROLLER_SIGNOFF"],
      "family": "I3",
      "interaction": true,
      "novel_combination": false,
      "post_july_capex_approver": false,
      "after_override": false,
      "adversarial": false
    }
  }
}
```

| Field | Meaning | Used by |
|---|---|---|
| `class` | `normal`, `known`, `generalized`, `composed` or `unknown` (SPEC §5.3) | M1, M3, M4, M10 |
| `failed_checks` | Checks that really fail: `budget`, `vendor`, `approver`, `duplicate`, `bank`, `quotes`, `related_party` | M2 |
| `causes` | Cause per failed check, in the rule engine's vocabulary (`cert_expired`, `gst_cancelled`, `blacklisted`, `overrun`, `approver_on_leave`, `possible_duplicate`, `bank_details_changed`, `insufficient_quotes`, `related_party`) | M2 (F4) |
| `uncovered_checks` | Failed checks with no valid precedent. Non-empty if and only if `class` is `unknown` | M1 |
| `steps` | The correct final step set, as step-library codes | M4, M5, M7, M8, M9 |
| `family` | Edge family (E1–E6, I1–I3, U1, U2, `normal`, `adversarial`) | reporting |
| `interaction` | An interaction case (I1, I2, I3) | M5 |
| `novel_combination` | The combination has no precedent (I2), so the system should flag it | M5 |
| `post_july_capex_approver` | A capex approver-away case after 1 Jul 2026 | M6 |
| `after_override` | A case after an override, which should follow the revised lesson | M7 |
| `adversarial` | Looks like an edge case but isn't, or hides a risk | reporting |

The risk-floor requirements for M2 are derived in code from `failed_checks` and `causes`:

- F1: `bank` → `VERIFY_BANK_CALLBACK` and `HOLD_PAYMENT`.
- F3: `related_party` → `DECLARE_CONFLICT_OF_INTEREST`.
- F4: vendor cause `gst_cancelled` → `VERIFY_GST_STATUS` and `HOLD_PO`.
