# V4 row-shed SELL ordering

This repair recovers the strongest unported V3.1 sale-order theorem into the sole canonical V4 workspace without importing the V3 router or creating a new controller. `repairs/gameplay/row-shed-sell-order` is the authoritative source package; the race-created `row-shed-ordering` carrier from PR #12768 is superseded rather than becoming a second implementation.

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

The transform fails closed to the caller action on missing/incomplete/type-poisoned stock evidence, malformed rows, malformed market/configuration input, invalid inventory/quote evidence, or a pricing failure. This is intentionally stricter than V3.1's incumbent requested-quantity fallback: V4 does not activate a second legacy ROW_ORDER policy when the post-unit projection is ambiguous.

Current ABI market parameters are passed through to the current quote function. The historical donor-parity fuzz gate is restricted to the complete-projection/default-market domain where V3.1 and the current component are intended to be semantically identical.

## Final-pressure novelty admission

`novel_rank_guard.py` is an additive admission layer for the current V4 stack. It does not construct STRATUM ranking and it does not copy or approximate LARK market pressure. Canonical pressure remains the sole final-pressure authority.

The landed `choose(parent, row_shed, pressure_action)` API is retained for source compatibility and can still validate already-produced intermediate rank evidence. It is **not** the strongest activation theorem because current V4 runs LARK pressure at the returned-action boundary: two different intermediate ranks can collapse to the same final action.

`choose_after_pressure(...)` is the stronger admission path. The caller injects the exact canonical pressure `transform` callback plus its exact quote function. The guard:

1. proves the row-shed candidate is an exact permutation of the inherited leading SELL block, preserving duplicate multiplicity, quantities, every suffix/barrier index, and every non-market surface;
2. invokes the same supplied pressure callback on isolated deep copies of the incumbent and row-shed candidate under the same public observation/configuration/quote evidence;
3. validates each pressure result as a full-market row permutation only: cardinality, quantities, duplicates, and non-market surfaces must remain exact, while legitimate SELL reordering and eligible empty-slot compaction are allowed;
4. returns exact parent identity if the two final pressure outputs are equal (`collapsed_after_final_pressure`);
5. admits the row-shed candidate only when the distinction survives final pressure (`survives_final_pressure`).

Missing/throwing pressure authority, missing quote evidence, malformed output, market-row mutation, top-level/non-market mutation, or malformed row-shed evidence all fail closed to parent identity. Observation/configuration/action inputs are copied before the callback, so an evidence callback cannot mutate caller-owned state.

The return remains the parent or row-shed candidate rather than a pressure-transformed action. This preserves one owner: the canonical runtime still performs the actual final pressure transform at its existing boundary.

## Composition

Intended seam:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. final-pressure survival admission using the exact canonical LARK pressure callback;
4. current `SelectedActionSell` / `OrderedSelectedSell` economics and later guards;
5. the existing canonical final LARK pressure boundary;
6. existing composer/materializer.

LOOM PR #12777 registered this package as `row-shed-sell-order` in the canonical composition graph. PR #12998 added the authenticated graph-postimage field carrier. That carrier is evidence-only and does not activate row-shed in production. The earlier intermediate-rank mirror is not sufficient activation evidence for the stronger final-output theorem; exact-current field/economic evidence must exercise this stronger admission path.

Do not fork the scheduler, producer, market engine, evaluator, canonical pressure family, or canonical V4 tree to consume this repair.

## Validation

`test_row_shed_sell_order.py` covers the original current-ABI boundary contract plus a literal independent V3.1 reference implementation:

- 14 focused tests in the existing suite under normal and optimized Python;
- 800 deterministic complete-projection/default-market donor-parity cases per mode, 1,600 total;
- falsey barriers and suffix-index preservation;
- no selected-action mutation and no row/quantity edits;
- stable score ties;
- incomplete/type-poisoned projection fail-closed behavior;
- malformed inventory and pricing failure fail-closed behavior;
- explicit V3.1-vs-V4 incomplete-projection divergence witness;
- current-ABI market-parameter passthrough.

`test_novel_rank_guard.py` preserves the 11 landed intermediate-rank compatibility contracts.

`test_final_pressure_guard.py` adds 12 stronger final-output contracts: downstream rank collapse, stable-tie survival, legal empty-slot compaction, quantity/non-market/top-level mutation rejection, missing/throwing pressure and quote fail-closed behavior, malformed output rejection, callback input isolation, invalid row-shed precheck, and an API-compatibility execution against the attributed current LARK `pressure_priority.py` source.

A current official-engine/full-game both-seat economic gate remains required before any production/default activation. Source admission is not production authority.
