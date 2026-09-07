# Selected-continuation seed budget

A standalone proposal stage for seed purchases when a controller supplies its
complete remaining continuations. It does not import, instantiate or advance a
controller. The selected default is unchanged.

This extends the request-count mechanism in ALDER's
[`seed_budget.py`](../cloud-hosted-loss-response/seed_budget.py) to explicit
caller continuations. That original component and its route-specific runtime
remain unchanged. KESTREL identified the intact-Arlene/SELL route boundary in
[T13](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788812914485609).
This implementation belongs only to `cloud-selected-seed-budget/`.

## Callable

```python
from selected_seed_budget import compile_demand, transform

contract = compile_demand(
    obs, cfg, selected_action,
    post_unit_seeds=post_unit_private["seeds"],
    continuations=possible_selected_continuations,
    complete=coverage_complete,
    reserves={"WHEAT": 0},
)
proposal = transform(
    obs, cfg, selected_action,
    post_unit_seeds=post_unit_private["seeds"],
    contract=contract,
)
candidate_action = proposal["action"]
```

`continuations` maps a branch name to dated rows
`{"step": n, "action": complete_action}`. Every branch must explicitly cover
`obs["step"] + 1` through `cfg["episodeSteps"] - 2`, including no-op rows.
An empty branch is valid only at the last executable decision. Do not supply
recorded future opponent actions, hidden seeds, or an incumbent tape after
changing its route. Supply the actual possible selected continuations.

`complete=True` asserts that the caller covered every remaining branch it may
choose. The compiler checks dates and structure, not the truth of that coverage
assertion. A planner that cannot supply the complete horizon passes `False`;
purchases then remain unchanged. The contract is bound to the selected action,
post-unit seeds, visible public state, own private state, and relevant limits.
A stale/different context returns an independent copy of the original action.

Count every PLANT request, including requests that might ultimately no-op.
Take the maximum remaining count **per crop across branches**, then add any
explicit reserve. Subtract only authoritative post-unit seed stock. Future
purchases are not guaranteed replenishment. Current-unit requests are already
resolved before the market and are not counted twice.

Only positive integer BUY_SEED quantities in executable market slots change.
A removed purchase becomes `[]`; other slots, trailing order fields, farmer and
hand actions remain in place. Each repeated buy uses observed stock, not the
requested quantity of an earlier buy that may fail for lack of cash. This may
retain redundant buys; it intentionally does not claim a minimum-cost schedule.
The implementation bounds compilation to 16 branches and 12,000 dated rows;
exceeding those bounds preserves the original action.

## Execution and evidence

Runtime needs only Python's standard library. Tests reuse the repository's
unchanged `cloud-eval/evaluate.py` and its existing source-verified engine loader:

```sh
D=revenue/kaggriculture/cloud-selected-seed-budget
KAG_ENGINE_DIR=/path/to/existing/pinned/engine \
  python "$D/test_selected_seed_budget.py"
```

The cache must already contain `kaggriculture.py`, `kaggriculture.json`, and the
framework `utils.py`. The official pin is
`Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
Existing engine artifact `10005621438` and source artifact `10030763484` were
reused. No new transport job, installation, or engine distribution is added.

22 tests pass. Seven fixture methods execute the actual interpreter in both
seats. They cover rewritten two-worker planting, post-unit stock, atomic seed
cancellation, cash-limited repeated buys with an intervening sale, independent
seed/shed storage, a shortage control, and a later-hire spending counterexample.
Other tests cover branch maxima, explicit reserves, incomplete horizons, stale
contexts, preserved slots, nonmutation and the JSON command-line interface.
`TEST-RESULT.txt` and `VALIDATION.json` retain exact run/source identities.

These are bounded manufactured component cases, not new full-game panels.
The rewritten two-worker case keeps 2 of 9 WHEAT seeds, completes the same two
plants, and preserves 70 cash. The funded-later-buy case receives 49 from selling
WHEAT2, then buys the required two seeds and retains 29 cash. Both run in both
positions; neither is a leaderboard claim.

**A seed-demand bound is not cash dominance or route feasibility.** The retained
negative case has 12 existing hands/hires and 233 cash. Removing a seed buy lets
the unchanged later HIRE execute for 233, leaving 0 rather than the baseline's
143 cash at that transition. Market slot identity does not imply unchanged
execution after liquidity changes. Feed the proposal through the consumer's
actual whole-bundle/receipt evaluation before selecting it. No policy promotion
or automatic composition is performed here.

The warm 30-sample measurement at 16 branches / 11,488 dated rows observed a
32.014 ms maximum compilation and 0.146 ms maximum transform. Imports and full
agent execution are excluded; this is not a hosted action-time guarantee.

## JSON CLI

```sh
python "$D/selected_seed_budget.py" case.json --output result.json
```

Input keys: `observation`, `configuration`, `selected_action`, `post_unit_seeds`,
`continuations`, `complete`, and optional `reserves`. Output includes the action,
reason, slot-level changes and compiled contract. Runtime source is a single
file; there are no external services, credentials or hidden controller state.
