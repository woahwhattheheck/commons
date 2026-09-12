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

## Downstream-pressure novelty admission

`novel_rank_guard.py` is an additive admission layer for the current V4 stack. Canonical V4 applies market pressure after the row-shed seam, so an intermediate row-shed rank that differs from the incumbent is not sufficient evidence of a distinct final action: the later stable pressure sort can erase that difference completely.

The stronger guard therefore receives the exact downstream pressure transform from its caller and evaluates that same transform twice with identical public observation, configuration, and quote evidence: once on the incumbent action and once on the row-shed candidate. Row-shed is admitted only when those validated final pressure outputs differ. If downstream pressure collapses both paths to the same action, the guard returns exact parent identity. Equal-pressure tie classes remain useful: because canonical pressure is stable, a row-shed tie-break that survives through the final pressure output remains admissible.

The guard first proves that row-shed is only an exact permutation of the inherited leading contiguous SELL block, with duplicate multiplicity, quantities, every suffix/barrier index, and all non-market surfaces preserved. It then requires each pressure output to preserve the complete market-row multiset, cardinality, quantities, duplicates, and non-market surfaces; canonical pressure's permitted row reordering and eligible empty-slot compaction remain representable. Missing/throwing pressure authority, missing quote evidence, malformed outputs, quantity drift, row drift, or non-market mutation all fail closed to parent identity.

This remains an admission primitive, not a new controller and not a second pressure implementation. It deliberately does not import, recreate, or approximate LARK pressure policy; composition must inject and authenticate the canonical pressure transform it already owns.

## Composition

Intended seam:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. downstream-pressure novelty admission using the exact canonical pressure transform under the same public evidence;
4. the existing FrozenSelected / selected-SELL economics and later canonical market-pressure stage;
5. existing composer/materializer and sole V4 runtime.

LOOM PR #12777 registered this package as `row-shed-sell-order` in the canonical composition graph. PR #12998 subsequently added the sole authenticated graph-postimage field carrier: it materializes the exact graph predecessor, overlays only the existing row-shed source bytes, and measures natural both-seat official-engine engagement with action-transparent diagnostics. That carrier is evidence-only and does not activate row-shed in production.

The #12998 field workflow has separate evidence-custody ownership for proving that an internal row-shed diagnostic survives into the final action returned to the engine. This source package does not fork or modify that workflow. Do not fork the scheduler, producer, market engine, evaluator, canonical pressure family, or canonical V4 tree to consume this repair.

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

`test_novel_rank_guard.py` adds 13 focused contracts, passing under normal Python and `python -O` in the authoring runtime. They cover the critical stronger theorem directly: an intermediate row-rank difference that downstream pressure collapses must return identity, while a row-shed tie-break inside an equal-pressure score class that survives the stable downstream sort must be retained. The suite also covers downstream identity, missing/throwing pressure authority, pressure quantity/non-market mutation rejection, row-shed multiset rejection before callback execution, duplicate-row multiplicity, falsey barriers, legal empty-slot compaction, malformed parent rows, and action/observation/configuration immutability.

A current official-engine/full-game both-seat economic gate remains required before any production/default activation. Downstream-pressure novelty admission likewise requires exact-current composition and field evidence before it can become an active edge.
