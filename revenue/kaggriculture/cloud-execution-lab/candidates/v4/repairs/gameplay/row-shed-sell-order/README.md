# V4 row-shed SELL ordering

This repair recovers the strongest unported V3.1 sale-order theorem into the sole canonical V4 workspace without importing the V3 router or creating a new controller. `repairs/gameplay/row-shed-sell-order` is the authoritative source package; the race-created `row-shed-ordering` carrier from PR #12768 is superseded and removed during consolidation rather than becoming a second implementation.

## Provenance

- V3.1 evidence commit: `7cbe552087626d09dbd8a84be8fa89efc7320ad0`
- historical router blob: `21210f396335431e81d300e118487dd859d54468`
- historical focused regression: `candidates/v3/overlay/checks/test_v31_row_shed.py`
- historical source SHA-256: `569b515c89f56a8f060ce94de218a341ae0e5b3c8e0e2c6428a8a0f08a462b05`
- historical focused-test SHA-256: `b8f81248e37078d15e767f2883c59589a670353c248c5d5eab126b58f41cabee`
- historical S34 field gate: 1,280 games per arm, 1273 W / 7 L and +540.0 margin/game against V3.0
- historical top-40 recorded replay bench: 96 W / 64 L

Those scores are historical provenance, not a V4 strength claim.

## Current-ABI contract

`RowShedSellOrder.transform(...)` consumes the current stack's already-owned `post_unit_shed` projection. It constructs no producer, invokes no parent controller, and never mutates the selected action.

Only the leading contiguous SELL block can move. Each row is ranked by the market-price drop caused by the units it can actually fill: `min(requested_quantity, post_unit_shed[item])`. The first falsey row or non-SELL row is a hard barrier, so raw market cardinality and every suffix index remain unchanged.

The transform fails closed to the caller action on missing/incomplete/type-poisoned stock evidence, malformed rows, malformed market/configuration input, invalid inventory/quote evidence, or a pricing failure. This is intentionally stricter than V3.1's incumbent requested-quantity fallback: V4 does not activate a second legacy ROW_ORDER policy when the post-unit projection is ambiguous. The expanded regression suite contains an explicit divergence witness so that this safety decision cannot be accidentally “fixed” back into the V3 behavior.

Current ABI market parameters are passed through to the current quote function. The historical donor-parity fuzz gate is restricted to the complete-projection/default-market domain where V3.1 and the current component are intended to be semantically identical.

## Composition

Intended seam:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. current `SelectedActionSell` / `OrderedSelectedSell` economics;
4. existing composer/materializer.

LOOM PR #12777 registers this package as `row-shed-sell-order` in the canonical composition graph but keeps it **blocked** until an authenticated materialized runtime postimage exists. Do not fork the scheduler, producer, market engine, evaluator, or canonical V4 tree to consume this repair.

## Validation

`test_row_shed_sell_order.py` now covers the original current-ABI boundary contract plus a literal independent V3.1 reference implementation:

- 14/14 focused tests under normal Python;
- 14/14 focused tests under `python -O`;
- 800 deterministic complete-projection/default-market donor-parity cases per mode, 1,600 total;
- falsey barriers and suffix-index preservation;
- no selected-action mutation and no row/quantity edits;
- stable score ties;
- incomplete/type-poisoned projection fail-closed behavior;
- malformed inventory and pricing failure fail-closed behavior;
- explicit V3.1-vs-V4 incomplete-projection divergence witness;
- current-ABI market-parameter passthrough.

The component source itself is unchanged by this consolidation. A current official-engine/full-game both-seat economic gate is still required before any production/default activation, and the composition graph still requires an authenticated materialized runtime postimage before this becomes an active edge.
