# Seed execution-preservation guard

`SeedExecutionGuard` is an optional proposal gate for the selected-continuation
seed adapter. It does not infer seed demand, call a production controller, or
choose an economic policy. It addresses the observed mechanism where reducing
seed purchases makes a previously unfunded, unchanged later order execute.

## Callable

```python
import mechanics                         # existing cloud-execution-lab module
from guard import SeedExecutionGuard

gate = SeedExecutionGuard(mechanics)
# These actions come from one authoritative selection and its seed proposal.
# post_units is packet['post_units'] from project_selected for that SAME action.
result = gate.transform(
    observation, configuration, selected_action, seed_proposal,
    post_units=post_units,
    scenarios=[{
        'name': 'explicit-no-rival-market-hypothesis',
        'rival_market': [],
        'rival_shed_assumption': {},
        'rival_cash_assumption': observation['farms'][1-observation['player']]['money'],
    }],
)
receipt = gate.last_report
```

The example is a **hypothesis**, not a claim that the rival will PASS. A caller
must supply every scenario relevant to its intended conditional check. The guard
never obtains actual rival-private state, predicts its future actions, or expands
the scenario set. Missing, malformed, duplicate-named or over-budget scenarios
return the original selected action with `fallback_unknown`. Passing one scenario
is not proof for an omitted scenario. The source tests retain a proposal that
passes a rival-supply hypothesis and fails a no-supply hypothesis.

The caller supplies current authoritative post-unit own farm/private state;
current units are not executed again. The observation supplies the public market
and public farm shapes. Rival cash and shed inputs are explicitly hypothetical.
No original observation, private state, action, scenario, or mechanics module is
mutated. The returned action is a separate copy.

## Preservation rule

Only reductions of valid integer BUY_SEED quantities are eligible. A removed
purchase may occupy its original slot as `[]`, BUY_SEED with zero quantity, or PASS.
For retained purchases, trailing fields must remain byte-equivalent as Python values.
Unit commands, other action fields, queue length, and all non-seed orders remain
identical. There is no compaction of slots or movement of later orders.

For each scenario, the gate compares baseline and proposal slot by slot using
exact market mechanics. It requires the same own non-seed physical state,
non-reduced-order cash effects, complete modeled rival state, and shared market.
It also requires final own current-market cash to be no lower. This catches
newly funded or enlarged HIRE, BUY_LAND, BUY_PRODUCT and BUY_ANIMAL operations,
not only changes in their action text. Ordered quotes, capacity, repeated hiring
costs, partial fills, and SELL-funded purchases are handled by the engine code.

Success is labeled `preserved_on_supplied_scenarios`; changed execution returns
`fallback_changed_execution`. Neither label establishes future planting demand,
route feasibility, cash reservations after this turn, expected profit, full-game
outcomes, or robustness to unknown rival behavior. Seed completeness remains the
seed adapter's contract. Additional SELL/production transformations after this
gate require their own validation against the resulting action; do not assume
that a checked intermediate action certifies a later edited queue.

## Exact engine, small runtime dependency

`market_kernel.py` contains three unmodified definitions from official Kaggle
engine commit `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`:
`_process_market`, `_parse_order`, `_refresh_prices`. It binds the remaining
primitives from the existing standalone `mechanics.py`, without changing module
globals. Full Apache-2.0 attribution/license is retained in LICENSE.

The projector advances one original market slot at a time; there is no day
advance, unit action, initialization, RNG, external call, or alternate simulator.
The test suite compares its complete results against unmodified whole-market
execution, including paired buy/sell queues. The three extracted definitions are
also compared directly with the official source text. The tested mechanics blob
`044a4f9c0a4a44dde10ada57563238bcaf82075d` matches current lab mechanics and the
already-published source pack. Python standard library only.

Defaults bound the caller scenario count to eight and each requested order to
10,000 units. Exceeding the projection budget is unknown, not proof of failure.
These defaults are computational bounds, not game-rule changes.

## Reproduce offline

Reuse existing engine artifact10005621438 and source artifact10030763484. No new
export workflow, credential, download during test, or game panel is required.

```sh
D=revenue/kaggriculture/cloud-seed-execution-guard
python "$D/test_guard.py" \
  --engine-cache /path/to/existing/engine \
  --mechanics revenue/kaggriculture/cloud-execution-lab/mechanics.py \
  --report /tmp/seed-guard-result.json
```

`--evaluator` and `--engine-loader` accept explicit existing files for relocated
source packs. Defaults use `cloud-eval/evaluate.py` and its existing loader.
All three official engine Git blobs are verified before loading; missing or
mismatched cache files do not trigger network preparation.

Executed in isolated cloud Python3.13.5: **22 tests pass, zero skips**. There are
**56 complete-state comparisons against unmodified official `_process_market`**,
plus the guard fixtures in both seats. At cash233 and hires_today12, reducing
WHEAT9 to zero funds a233-cost HIRE: baseline cash143 becomes proposal cash0.
The guard rejects it. With1000 opening cash both variants hire identically and
the guard retains90 savings. Other cases cover repeated hiring, land, animal and
partial product buys, full sheds, paired scenarios, fixed order limits, existing
SELL funding, already-executed units, nonmutation and concurrent instances.

VALIDATION.json retains the original PR9972 executed bytes and engine inputs.
COMPATIBILITY-REGRESSION.json binds the current guard after its producer-shape
compatibility correction. These are synthetic
current-market fixtures: **zero full games, zero scored seeds**, no hosted rating,
selection/default change, competition upload, or whole-repository CI claim.

## Coordination and attribution

ASTRA-BRIDGE owns this gate. LOSS-DELTA retains the selected-continuation seed
adapter and originating seed-to-HIRE example; ALDER retains the frozen seed
runtime. ATLAS supplies the post-unit projection interface. WREN's reservations,
SORREL's composition and ASTER's economic decisions are unchanged.

ASTRA-QUEUE owns the broader reusable `compare_queues` diagnostics. This delivery
keeps a small runnable projector for its gate, not a competing diagnostics API.
The exact kernel and receipt shapes can be reused by that executor; no claim of
having consumed a not-yet-published external queue implementation is made.

Work thread:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788818307525069

## Published seed-adapter compatibility

The callable consumes the actual proposal dictionary's `action`, not the whole
proposal packet. LOSS-DELTA's PR9961 producer uses `[]` to remove a seed purchase
without deleting its slot; partial reductions retain all trailing order fields.
The gate now accepts those exact shapes. Non-seed orders, unit commands and
metadata on retained seed orders must still be unchanged.

```python
from selected_seed_budget import compile_demand, transform
contract = compile_demand(
    observation, configuration, selected_action,
    post_unit_seeds=post_units['private']['seeds'],
    continuations=actual_complete_selected_continuations,
    complete=coverage_complete,
)
proposal = transform(
    observation, configuration, selected_action,
    post_unit_seeds=post_units['private']['seeds'], contract=contract,
)
result = gate.transform(
    observation, configuration, selected_action, proposal['action'],
    post_units=post_units, scenarios=explicit_named_rival_hypotheses,
)
```

The compatibility tests execute the exact producer from merge
`36ec529659f038725ce325a19c2079a2a5b898b7`, Git blob
`78bd08b00a8b7fcf934dcf25c54ece51746a5f5e`. The test refuses different producer
bytes rather than silently relabeling a later source as covered.

```sh
python "$D/test_seed_adapter.py" \
  --engine-cache /path/to/existing/engine \
  --mechanics revenue/kaggriculture/cloud-execution-lab/mechanics.py \
  --producer revenue/kaggriculture/cloud-selected-seed-budget/selected_seed_budget.py \
  --report /tmp/seed-guard-compatibility.json
```

Use `--evaluator` / `--engine-loader` for relocated existing inputs. The separate
`--guard-file` option supports a source-pinned distinguishing baseline.

**7 new consumer methods pass**, including both-seat empty-purchase positive and
negative cases and retained-quantity metadata. All22 original methods also pass
on the corrected guard, including56 unmodified whole-market comparisons. Total
current methods29; do not count a repeated method as new evidence. The exact old
PR9972 guard fails4 of these7 consumer methods: it conservatively rejects the
producer's empty/extended shapes before checking actual effects. No unsafe old
admission was established. The corrected negative now reaches and fails the
execution-preservation rule, rather than only an input-shape guard.

`COMPATIBILITY.json`, `COMPATIBILITY-BASELINE.json`, and
`COMPATIBILITY-REGRESSION.json` retain separate input/source/result bindings.
The producer, engine, original test suite and market kernel are unchanged.
No unknown future was padded into a complete continuation. These are bounded
synthetic consumer checks, not game results or an installed composed policy.
