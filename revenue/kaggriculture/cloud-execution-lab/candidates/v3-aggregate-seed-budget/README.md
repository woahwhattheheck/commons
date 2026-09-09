# TITAN v3 aggregate seed-budget candidate

Operation: `titan-v3-aggregate-seed-budget-20260909-01`

## Hypothesis

The landed `SeedBudget.apply()` bounds each executable `BUY_SEED` row against the same post-unit seed stock. When the live market prefix contains two rows for the same crop, both rows can independently fit the remaining-route bound while their **aggregate realized fills** exceed every branch-compatible future `PLANT` request. The excess is fixed-price cash converted into seed stock that the frozen route cannot use.

This candidate does **not** aggregate arbitrary purchase queues. It edits only the final non-empty active row when all of the following are proven from current public state and immutable route data:

1. the target is the second-or-later `BUY_SEED` for one crop;
2. every non-empty active row through the target is a strict fixed-price `BUY_SEED`;
3. exact own-cash simulation proves how many units every preceding row and the target row fill;
4. the aggregate fill exceeds observed post-unit stock plus the exact branch-compatible remaining demand;
5. all surplus is local to the final row, so preceding execution is byte-for-byte unchanged;
6. there is no later active order whose execution could change when cash is saved.

On decline, the original action object is returned by identity. On admission, one copied market slot is reduced (or replaced by `[]` when its realized fill is wholly surplus). Farmer, hands, all preceding rows, inactive tail rows, route state, seller ledger, and canonical bytes are untouched.

## Evidence boundary

`audit_routes.py` decodes the exact current four-route Arlene bank and inventories duplicate same-crop seed rows inside the official first-N market prefix. A route shape is only an opportunity witness; it is not a gameplay or score claim. Promotion would additionally require realized activation telemetry and complete identical-cell, both-seat official-engine games against unchanged current canonical TITAN.

## Local acceptance

```bash
python -m py_compile aggregate_seed_budget.py audit_routes.py test_aggregate_seed_budget.py
python -m unittest -v test_aggregate_seed_budget.py
python audit_routes.py --output route-audit.json
```

The focused suite covers funded over-retention, partial-funding preservation, surplus that spills into an earlier row, SELL/variable-prefix ambiguity, active-prefix truncation, branch-compatible demand, zero-tail idempotence, mixed fixed-price seed rows, invalid numeric input, and route-audit classification.

## Non-claims

This additive packet does not change `seed_budget.py`, `titan_runtime.py`, `main.py`, `TITAN-CONFIG.json`, the canonical archive or pointers, provider state, or any Kaggle submission. It makes no playing-strength, leaderboard, or first-place claim without complete official evidence.
