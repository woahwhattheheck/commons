# V4 row-shed SELL ordering

This repair recovers the strongest unported V3.1 sale-order theorem into the sole canonical V4 workspace without importing the V3 router or creating a new controller.

## Provenance

- V3.1 evidence commit: `7cbe552087626d09dbd8a84be8fa89efc7320ad0`
- historical router blob: `21210f396335431e81d300e118487dd859d54468`
- historical focused regression: `checks/test_v31_row_shed.py`
- historical S34 field gate: 1,280 games per arm, 1273 W / 7 L and +540.0 margin/game against V3.0
- historical top-40 recorded replay bench: 96 W / 64 L

Those scores are historical provenance, not a V4 strength claim.

## Current-ABI contract

`RowShedSellOrder.transform(...)` consumes the current stack's already-owned `post_unit_shed` projection. It constructs no producer, invokes no parent controller, and never mutates the selected action.

Only the leading contiguous SELL block can move. Each row is ranked by the market-price drop caused by the units it can actually fill: `min(requested_quantity, post_unit_shed[item])`. The first falsey row or non-SELL row is a hard barrier, so raw market cardinality and every suffix index remain unchanged.

The transform fails closed to the caller action on missing/incomplete/type-poisoned stock evidence, malformed rows, malformed market/configuration input, unknown price inputs, or a pricing failure. This is intentionally stricter than V3.1's incumbent requested-quantity fallback because V4 has no reason to activate a second legacy ROW_ORDER policy when projection evidence is ambiguous.

## Composition

Intended seam:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. current `SelectedActionSell` / `OrderedSelectedSell` economics;
4. existing composer/materializer.

Do not fork the scheduler, producer, market engine, evaluator, or canonical V4 tree to consume this repair.

## Focused validation

`test_row_shed_sell_order.py` freezes the current official price-shape example plus the donor's important boundary invariants: falsey barriers, tail-index preservation, no row mutation, incomplete projection, bool/float/string/negative poison, malformed truthy rows, stable ties, explicit caller fallback, and missing-projection identity.

Local authoring check: 10/10 normal, 10/10 with `python -O`, and `py_compile` pass. A current official-engine/full-game gate is still required before any production/default activation.
