# B11 — public mirror-adaptive sale horizon

## Why this lane exists

Unconditional `r04_sale_horizon: 8 -> 10` is rejected as a production default even though its self-play signal is huge. The exact H13 evidence carrier records:

- frozen V3.1 self-play: 16/16 positive, mean head-to-head margin +1764.75;
- adversarial self-play seeds 101..110: 20/20 positive, mean +1666.6;
- exact Arlene gate: 0+/8-/0=, mean paired ΔM -662, range -1037..-377;
- every Arlene cell lowered TITAN's own score and raised Arlene's.

That is the signature of an opponent-conditioned shared-market effect, not a robust global parameter improvement.

## Public-state contract

The official engine exposes the shared `farms` collection in every player's observation while `observation.private` remains player-specific. B11 never reads rival private shed, carried inventories or market orders. It also deliberately excludes public `money`: horizon choice itself changes sale timing and cash, so including money would make the classifier self-invalidating after the first candidate-only market effect.

The repaired classifier validates the public structural schema before equality. A signature requires:

- a nonempty square `tiles` list-of-lists;
- tile cells restricted to `None`, literal `LOCKED`, known crops (`PLANT` + WHEAT/CARROT/TOMATO/STRAWBERRY/MELON), `WEED`, `COOP` with absent/GOOSE animal, or `PASTURE` with absent/COW/SHEEP animal;
- main `farmer` and every hand as in-bounds two-element lists of literal non-bool ints;
- `unlocked_quadrants` as a duplicate-free list drawn from `NW/NE/SW/SE`;
- literal nonnegative-int `hires_today`.

Tiles are normalized to production/layout identity only. Dynamic water/yield/feed/care fields are intentionally **not** classifier evidence; B11 asks whether route/production structure identifies the self-like shared-market regime.

A mirror certificate then requires exactly two validated farms, literal integer `step`/`player`, exact type+value equality of the normalized public structural signatures, and **8 consecutive callbacks** with no gap/rewind. The eighth consecutive mirror callback may use horizon10. Any mismatch, malformed/missing structure, type confusion or callback discontinuity fails closed to horizon8 immediately. Recoverable malformed input clears that player's existing streak so identical malformed farms cannot accumulate mirror evidence.

## Policy isolation

`candidate.py` binds the ready-submission V3.1 R04 tuple exactly:

- baseline horizon8;
- mirror horizon10;
- opening round-trip0;
- row order ON;
- evening flush ON;
- sale-fertilizer ON;
- cattle-early ON.

No L3 suppression or H4 logic is added. B11 changes only the value observed by E184's existing `SALE_HORIZON` seam during a single parent callback. The shared module-global horizon is snapshotted and restored in `finally`, so another arm/control in the same interpreter cannot inherit H10, including after parent exceptions. If the conditioner is disabled, `install()` returns the exact horizon8 parent callable without classification or action rewriting.

The experiment changes no canonical archive, overlay source, generated default/config, package builder/input, evaluator/opponent, provider, Kaggle or submission state.

## Exact-head source custody

The dedicated workflow checks out the event's exact PR head with full history, requires frozen V3.1 base `508b342f...` as the exact ancestor, constrains the full base→head diff to the four experiment files plus that workflow, and pins frozen producer blobs before import:

- R04 `21c4f1db0298f8955b1f5ad366bd780a89cad206`
- r01 tapes `a43289b9cc5e34a2481fddf652762a7d92f427ef`

It runs the focused predecessor module, `py_compile`, then requires a clean worktree. Hosted green is a separate fact and must be bound to the current exact head.

## What must be measured

This source shape is not a promotion claim. The minimum economics screen is deliberately two-regime:

1. exact V3.1 mirror/self-play cells where fixed H10 was strongly positive;
2. exact Arlene cells where fixed H10 was decisively negative.

For every paired cell report Δown, Δrival, ΔM, horizon callback counts, maximum mirror streak, every transition into/out of H10, and every negative cell. Crucially, bind classifier/horizon state at the first E184-relevant decisions (`step >= 288`), not only final/max streak. The first gate question is whether the certificate captures material mirror benefit **while remaining horizon8-identical against Arlene**. Repeated Arlene H10 activation with the old negative signature is an economics rejection.

Only after that screen should B11 be tested on Shop-Router-like field opponents. Structural similarity is a public regime heuristic, not hidden opponent identity or private-policy inference.

## Focused predecessors

The focused suite now covers money exclusion; strict structural mismatch; gap and rewind reset; step/player type confusion; missing fields; equal malformed farms across eight callbacks; immediate streak clearing on malformed state; accepted/rejected tile structural domains; type-strict equality; 8-callback H10 warmup; callback-scoped horizon restoration; shared-module control isolation; parent-exception restoration; immediate mismatch fallback; disabled exact-parent mode; literal baseline horizon; and signature de-aliasing.

No local or hosted PASS is claimed by this documentation update. Exact-head CI/review truth must be bound separately.
