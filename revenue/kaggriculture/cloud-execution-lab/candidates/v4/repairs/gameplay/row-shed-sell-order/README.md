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
2. after the complete remaining seller + pressure pipeline, the two returned actions still differ in **official engine-parsed market semantics** inside the executable prefix.

The final comparison mirrors `_parse_order()` plus the supported-item dispatch from authenticated reference engine blob `3c202c7ee921da239356789e266b694635103fc4`: parser-dead rows normalize to an inert slot, HIRE/BUY_LAND ignore extra tokens, quantity-bearing orders use the engine's `int(...)` coercion and positive-quantity rule, and unsupported items/sub-ops are inert. Interior inert slots are preserved because their lockstep index relative to the opponent is observable; only inert trailing slots are trimmed after the raw executable prefix is sliced.

Therefore suffix-only differences, zero-quantity versus empty rows, HIRE/BUY_LAND extra-token differences, coercible quantity spellings, unsupported-item rows, and absent versus inert trailing slots do not establish novelty. A zero-quantity SELL remains a hard pre-seller ordering barrier. Plain integer cap 0/negative normalizes to one executable row; bool/float/string cap poison fails closed. If final arms differ on non-market action surfaces, evidence is non-comparable and fails closed rather than attributing the difference to STRATUM.

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

`test_novel_rank_guard.py` now contains 20 focused contracts for the complete-pipeline theorem. In addition to the original collapse/survivor, prefix-custody, barrier, multiplicity, poison, malformed-evidence, and immutability cases, parser-equivalence killers cover zero-quantity versus empty, HIRE extra tokens, coercible quantities, trailing inert-slot equivalence, interior inert-slot alignment, and unsupported market items. Exact current source/test blobs pass 20/20 normal, 20/20 under `-O`, and `py_compile`.

No production/default activation or full-game strength claim follows from these source contracts. Promotion still requires the repaired donor, exact current composition, final-return custody, natural engagement, and paired own/rival/margin economics on the one canonical V4.
