# V3.1 row-shed -> current V4 selected-action ABI

This directory recovers the reviewed **row-shed SELL-order pricing** semantics from
TITAN V3.1 commit `7cbe552087626d09dbd8a84be8fa89efc7320ad0` into the one canonical V4
workspace. It is deliberately an additive component, not a second V4 root and not a
legacy-router resurrection.

## What the donor fixed

The inherited row-order policy ranks a leading contiguous block of `SELL` rows by the
market-price drop each row causes. Tape rows can request far more stock than the shed
actually contains (`1000` is effectively “sell all”). Pricing a 1000-unit request when
only one unit exists can incorrectly move that row in front of another row that clears
real stock.

Row-shed ranks each leading row using:

`quantity_for_priority = min(requested_quantity, exact_post_unit_shed[item])`

It changes **only row order**. It does not edit quantities, compact slots, move tail
rows, add orders, or mutate the selected action.

Historical custody is exact: source SHA-256
`569b515c89f56a8f060ce94de218a341ae0e5b3c8e0e2c6428a8a0f08a462b05`, reviewed test
SHA-256 `b8f81248e37078d15e767f2883c59589a670353c248c5d5eab126b58f41cabee`.
The shipping V3.1 receipt records a 1,280-game-per-arm official-reference gate at
1273W/7L and +540 margin/game versus V3.0, plus a 96W/64L top-40 bench. Those are
**historical donor receipts**, not a claim about current V4 economics.

## Current ABI seam

`current_row_shed.transform_selected()` consumes exactly what the current selected SELL
stack already exposes:

- the already-selected action/market queue,
- the public market inventory from the current observation,
- the exact post-unit shed produced by the selected-action projection,
- the pinned default-market quote function and product set.

The intended composition point is after the caller has selected/projected unit actions
and has `post_unit_shed`; no parent controller is called and no production state is
advanced. A composer should bind `price_at(item, level)` to the current pinned default
`mechanics.market_price(item, level, None)` and `priced_items` to `mechanics.PRODUCTS`.

The component rejects truthy custom market parameters. Raw falsey slots are barriers,
tail indices survive exactly, malformed row quantities preserve the parent order, and
incomplete/type-poisoned shed evidence falls back coherently for the entire leading
block to the donor's requested-quantity priority. Other malformed current-ABI envelopes
fail closed to the exact parent action object.

## Validation

`test_current_row_shed.py` passes under normal Python and `PYTHONOPTIMIZE=1`:

- 15 focused checks per mode;
- 800 deterministic randomized valid-domain parity cases per mode against a literal
  reference implementation of the reviewed `7cbe552` donor (`1,600` parity cases total);
- success-path row identity / quantity / tail-slot invariants;
- falsey-barrier preservation;
- whole-block incomplete/poisoned-projection fallback;
- malformed configuration/envelope and quote/inventory fail-closed checks.

Run from this directory:

```bash
python -B -m unittest -v test_current_row_shed.py
python -O -B -m unittest -v test_current_row_shed.py
```

## Promotion boundary

This landing is **component-tested, not runtime-promoted**. It does not create a new
feature key or alter `main.py`, `frozen_selected.py`, `ordered_selected_sell.py`, the
canonical archive, or defaults. Current-V4 promotion should first run the official
reference evaluator against the canonical real/published opponent panel in both seats,
with the transform inserted at the selected-action post-unit seam. That gate must also
verify that inherited funding-prefix rows and raw slots remain unchanged except for the
reviewed leading-SELL permutation.
