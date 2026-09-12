# V4 row-shed SELL ordering

This repair recovers the strongest unported V3.1 sale-order theorem into the sole canonical V4 workspace without importing the V3 router or creating a new controller. `repairs/gameplay/row-shed-sell-order` is the authoritative source package.

## Provenance

- V3.1 evidence commit: `7cbe552087626d09dbd8a84be8fa89efc7320ad0`
- historical router blob: `21210f396335431e81d300e118487dd859d54468`
- historical S34 field gate: 1,280 games per arm, 1273 W / 7 L and +540.0 margin/game against V3.0
- historical top-40 recorded replay bench: 96 W / 64 L

Those scores are historical provenance, not a V4 strength claim.

## Current-ABI donor

`RowShedSellOrder.transform(...)` consumes the current stack's caller-owned post-unit shed projection. It constructs no producer or controller and never mutates its input action. The intended theorem is narrowly about reordering engine-executable leading SELL rows by the price drop caused by units that can actually be filled.

The current donor/source-composition line has its own active prefix-custody repair: official market execution is limited to `max(1, int(maxMarketOrdersPerTurn))`, engine-dead SELL quantity zero must not be treated as sortable, and no inert suffix row may be promoted into the executable prefix. That source/composer authority is separate from this file's novelty helper. Do not use the novelty helper to bypass or substitute for the donor's prefix/positive-quantity gate.

## Complete-pipeline final-action novelty admission

`novel_rank_guard.py` is an evidence/admission primitive, not a runtime controller. Earlier variants compared an intermediate pressure rank, then directly replayed LARK pressure from the STRATUM seam. Both are insufficient.

STRATUM is injected inside `FrozenSelected.transform`, immediately after its post-unit projection. Existing seller economics still run afterward and may resize, blank, append or move market rows before TITAN later invokes canonical market pressure. A direct pressure replay from the STRATUM seam therefore skips real stateful policy and can claim novelty that disappears before pressure is ever reached.

The corrected guard does **not** replay seller or pressure code. Its caller must supply two already-produced final returned actions from an authenticated, isolated dual-arm execution of the complete remaining canonical suffix: incumbent and STRATUM. The guard then admits STRATUM only when both conditions hold:

1. the pre-seller STRATUM candidate is an exact permutation of the same leading positive-quantity SELL rows entirely inside the source-safe executable market prefix, with duplicate multiplicity preserved and every barrier/inert suffix/non-market surface byte-identical; and
2. after the complete remaining seller + pressure pipeline, the two returned actions still differ inside the engine-executable market prefix.

A final difference only in rows at or beyond the market cap is identity. A zero-quantity SELL is a hard barrier. Plain integer cap 0/negative normalizes to one executable row; bool/float/string cap poison fails closed. If final arms differ on non-market action surfaces, evidence is non-comparable and fails closed rather than attributing the difference to STRATUM.

This deliberately leaves closure/authentication of the complete dual-arm suffix to the sole final-return evidence carrier. It neither imports nor recreates `FrozenSelected`, selected-SELL economics, LARK pressure, the evaluator, or the engine.

## Composition and custody

Intended source order remains:

1. caller-owned current selected-action unit projection;
2. `RowShedSellOrder` using that packet's `post_unit_shed`;
3. existing remaining `FrozenSelected` SELL economics;
4. canonical market pressure;
5. final returned action / engine boundary.

LOOM registered this package in the canonical composition graph. The dedicated returned-action workflow owns proof that an internal row-shed change survives the whole remaining route. `FinalActionNoveltyGuard` may consume those final arm outputs; it does not replace that workflow and it is not activation authority by itself.

Do not fork the scheduler, producer, seller, market engine, evaluator, pressure family, runtime, archive, or V4 tree to consume this repair.

## Validation

The historical/current donor suite remains separate from this novelty helper and must be rebound after the executable-prefix/positive-quantity source repair.

`test_novel_rank_guard.py` now contains 14 focused contracts for the complete-pipeline theorem: intervening seller/pressure collapse; surviving final executable-prefix difference; final suffix-only difference; pre-seller suffix-only mutation; stale suffix promotion into the prefix; min-one cap semantics; zero-quantity barrier; duplicate multiplicity; quantity mutation rejection; final non-market divergence rejection; legitimate seller resize/blank behavior; type-poisoned cap fail-closed behavior; malformed final action; and input immutability.

No production/default activation or full-game strength claim follows from these source contracts. Promotion still requires the repaired donor, exact current composition, final-return custody, natural engagement, and paired own/rival/margin economics on the one canonical V4.
