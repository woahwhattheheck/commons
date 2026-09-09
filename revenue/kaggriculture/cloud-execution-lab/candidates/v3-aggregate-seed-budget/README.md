# TITAN v3 aggregate seed-budget candidate — NO SIGNAL

Operation: `titan-v3-aggregate-seed-budget-20260909-01`

Evidence base: main `bdb428d05487b16dbad83bbbb6286a5d1a77836d`, inherited by non-force merge commit `ca73e17d55b020d493d81d75abc87329b5506f35`.

## Disposition

**REJECT BEFORE GAMES on the current public feature set.** Independent exact-route review decoded the same four-route Arlene bank and found zero duplicate same-crop rows in the official active market prefix and zero strict trailing opportunities. The hosted workflow now invokes `audit_routes.py --require-tail-safe` and exits nonzero with `NO_SIGNAL / REJECT BEFORE GAMES` when that count is zero. Passing source contracts cannot override missing applicability.

The mechanism remains a bounded reference implementation for a future route or final-action callsite that actually emits multiple funded same-crop seed rows. It is not a current TITAN v3 gameplay candidate, should not consume paired panel cells, and must not be merged or promoted without a realized final-action activation witness on an exact executable closure.

## Hypothesis and safety boundary

The landed `SeedBudget.apply()` bounds each executable `BUY_SEED` row against the same post-unit seed stock. If a live market prefix ever contains two rows for the same crop, both rows can independently fit the remaining-route bound while their **aggregate realized fills** exceed every branch-compatible future `PLANT` request. The excess is fixed-price cash converted into seed stock that the frozen route cannot use.

This implementation does **not** aggregate arbitrary purchase queues. It edits only the final non-empty active row when all of the following are proven from current public state and immutable route data:

1. the target is the second-or-later `BUY_SEED` for one crop;
2. every non-empty active row through the target is a strict fixed-price `BUY_SEED`;
3. exact own-cash simulation proves how many units every preceding row and the target row fill;
4. the aggregate fill exceeds observed post-unit stock plus the exact branch-compatible remaining demand;
5. all surplus is local to the final row, so preceding execution is byte-for-byte unchanged;
6. there is no later active order whose execution could change when cash is saved.

On decline, the original action object is returned by identity. On admission, one copied market slot is reduced (or replaced by `[]` when its realized fill is wholly surplus). Farmer, hands, all preceding rows, inactive tail rows, route state, seller ledger, and canonical bytes are untouched.

## Runtime adapter

`candidate_runtime.py` consumes only an already completed frozen-TITAN action. It binds the exact route, normalized step, post-unit seed stock, exact positive-integer active-prefix capacity, and every branch-compatible remaining request (including spatial additions). `main.py` calls canonical TITAN exactly once, edits no controller or ledger state, and attempts the bounded transform only inside the parent's remaining reserved time. Candidate-local modules are loaded by exact resolved paths under unique names. A candidate-local import failure is retained as a diagnostic only after canonical parent bytes are obtained. Every missing binding, unsupported mode, malformed state/configuration, timeout, import failure, or exception returns canonical bytes.

`test_entrypoint_load.py` copies only the candidate entrypoint and siblings into a temporary evaluator-shaped tree, loads the entrypoint from outside that directory, proves path-bound sibling resolution and exactly one parent call, then corrupts the candidate runtime and proves the parent action still returns. `test_official_engine.py` runs the preserved competition interpreter and proves the fixed-price cash/fill invariant used by the pure simulator.

## Local acceptance

```bash
python -m py_compile aggregate_seed_budget.py audit_routes.py candidate_runtime.py main.py \
  test_aggregate_seed_budget.py test_candidate_runtime.py test_entrypoint_load.py \
  test_official_engine.py
python -m unittest -v \
  test_aggregate_seed_budget.py test_candidate_runtime.py test_entrypoint_load.py
python audit_routes.py --output route-audit.json --require-tail-safe
```

The 21 network-independent contracts pass. Hosted CI adds two preserved-engine contracts for 23 total, then deliberately fails on the exact current route bank unless at least one strict trailing opportunity exists. A green semantic suite plus a red applicability gate is the expected and correct current result.

## Non-claims

This additive packet changes no canonical runtime, `SeedBudget`, config, archive, pointer, provider state, or Kaggle submission. It makes no playing-strength, leaderboard, first-place, regression-repair, activation, or promotion claim.
