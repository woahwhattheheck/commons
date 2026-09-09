# TITAN v3 aggregate seed-budget candidate

Operation: `titan-v3-aggregate-seed-budget-20260909-01`

Evidence base: current main `78b1c3647d58407da1a315fb5e13b93bff635650`, inherited by non-force merge commit `fe879ef9ccf591237f61ebf1b21fca8e488bb015`.

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

## Runtime adapter

`candidate_runtime.py` consumes only an already completed frozen-TITAN action. It binds the exact route, normalized step, post-unit seed stock, and every branch-compatible remaining request (including spatial additions). `main.py` calls canonical TITAN exactly once, edits no controller or ledger state, and attempts the bounded transform only inside the parent's remaining reserved time. Any missing binding, unsupported mode, malformed state, timeout, or exception returns canonical bytes.

`test_official_engine.py` runs the preserved competition interpreter and proves that trimming the final MELON row from four units to one leaves every prior and rival effect unchanged while preserving exactly three seed costs in cash. It separately proves the partial-funding abort semantics used by the pure simulator.

## Evidence boundary

`audit_routes.py` decodes the exact current four-route Arlene bank and inventories duplicate same-crop seed rows inside the official first-N market prefix. A route shape is only an opportunity witness; it is not a gameplay or score claim. Promotion would additionally require realized activation telemetry and complete identical-cell, both-seat official-engine games against unchanged current canonical TITAN.

## Local acceptance

```bash
python -m py_compile aggregate_seed_budget.py audit_routes.py candidate_runtime.py main.py \
  test_aggregate_seed_budget.py test_candidate_runtime.py test_official_engine.py
python -m unittest -v test_aggregate_seed_budget.py test_candidate_runtime.py
python audit_routes.py --output route-audit.json
# Hosted CI installs kaggle-environments==1.32.7 and also runs test_official_engine.py.
```

The 18 network-independent contracts cover funded over-retention, partial-funding preservation, surplus that spills into an earlier row, SELL/variable-prefix ambiguity, active-prefix truncation, branch-compatible demand, zero-tail idempotence, mixed fixed-price seed rows, invalid numeric input, route-audit classification, completed-action binding, spatial demand, day/hour normalization, player validation, and exact projection fallback. Hosted CI adds two preserved-engine contracts.

## Non-claims

This additive packet does not change `seed_budget.py`, `titan_runtime.py`, `main.py`, `TITAN-CONFIG.json`, the canonical archive or pointers, provider state, or any Kaggle submission. It makes no playing-strength, leaderboard, or first-place claim without complete official evidence.
