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

## Pressure-novel admission

`novel_rank_guard.py` is an additive admission layer for the current V4 stack, where the already-enabled LARK market-pressure transform can independently choose a leading-SELL order. It does not construct either ranking and does not change the historical `RowShedSellOrder.transform(...)` donor semantics.

Given one shared parent action, one row-shed candidate, and one pressure candidate, the guard admits row-shed only when both candidates are exact permutations of the same leading contiguous SELL block, preserve duplicate multiplicity, preserve every suffix/barrier index and all non-market action surfaces, and produce different ranks. If the two ranks are identical, the row-shed candidate is redundant and the guard returns exact parent identity. Missing/malformed pressure evidence, cardinality drift, row/quantity changes, suffix movement, or non-market mutation also fail closed to parent identity.

This is deliberately an admission primitive rather than a new controller or a new pressure implementation. The canonical pressure transform remains the rank authority; later composition may pass its already-produced candidate into this guard without importing a second policy family.

## Composition

Intended seam:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. optional pressure-novel admission against the canonical market-pressure candidate;
4. current `SelectedActionSell` / `OrderedSelectedSell` economics;
5. existing composer/materializer.

LOOM PR #12777 registered this package as `row-shed-sell-order` in the canonical composition graph. PR #12998 subsequently added the sole authenticated graph-postimage field carrier: it materializes the exact graph predecessor, overlays only the existing row-shed source bytes, and measures natural both-seat official-engine engagement with action-transparent diagnostics. That carrier is evidence-only and does not activate row-shed in production.

Do not fork the scheduler, producer, market engine, evaluator, canonical pressure family, or canonical V4 tree to consume this repair.

## Validation

`test_row_shed_sell_order.py` covers the original current-ABI boundary contract plus a literal independent V3.1 reference implementation:

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

`test_novel_rank_guard.py` adds 11 focused contracts, passing under normal Python and `python -O` in the authoring runtime. They cover redundant-rank identity, distinct-rank admission, pressure identity as valid comparison evidence, missing pressure fail-closed behavior, suffix/non-market/multiset mutation rejection, duplicate-row multiplicity, falsey barriers, malformed parent rows, and input immutability.

A current official-engine/full-game both-seat economic gate remains required before any production/default activation. Pressure-novel admission likewise requires current-stack field evidence before it can become an active composition edge.
