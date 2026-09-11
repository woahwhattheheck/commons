# B11 — public mirror-adaptive sale horizon

## Why this lane exists

Unconditional `r04_sale_horizon: 8 -> 10` is rejected as a production default even though its self-play signal is huge. The exact H13 evidence carrier records:

- frozen V3.1 self-play: 16/16 positive, mean head-to-head margin +1764.75;
- adversarial self-play seeds 101..110: 20/20 positive, mean +1666.6;
- exact Arlene gate: 0+/8-/0=, mean paired ΔM -662, range -1037..-377;
- every Arlene cell lowered TITAN's own score and raised Arlene's.

That is precisely the signature of an opponent-conditioned shared-market effect, not a robust global parameter improvement.

## Public-state contract

The official engine exposes the shared `farms` collection in every player's observation while `observation.private` remains player-specific. B11 reads only public farm structure:

- `tiles`
- main `farmer` position
- `hands` positions
- `unlocked_quadrants`
- `hires_today`

It never reads rival private shed, carried inventories or market orders. It also deliberately excludes public `money`: horizon choice itself changes sale timing and cash, so including money would make the classifier self-invalidating after the first candidate-only market effect.

A mirror certificate requires exactly two farms, literal integer `step`/`player`, recursive JSON type+value equality of those five public structural fields, and **8 consecutive callbacks** with no gap/rewind. The eighth consecutive mirror callback may use horizon 10. Any mismatch, malformed state, missing field or callback discontinuity fails closed to horizon 8 immediately.

The strict comparator intentionally rejects Python aliases such as `True == 1`.

## Policy factor

`candidate.py` binds the ready-submission V3.1 R04 tuple exactly:

- baseline horizon 8;
- mirror horizon 10;
- opening round-trip 0;
- row order ON;
- evening flush ON;
- sale-fertilizer ON;
- cattle-early ON.

No L3 suppression or H4 logic is added. B11 changes only the value observed by E184's existing `SALE_HORIZON` seam before each parent callback. If the conditioner is disabled, `install()` returns the exact horizon-8 parent callable without classification or action rewriting.

This experiment lives entirely under `candidates/v3/experiments/**` and changes no canonical archive, overlay source, generated default/config, package builder, evaluator/opponent, provider, Kaggle or submission state.

## What must be measured

This source shape is not a promotion claim. The minimum economics screen is deliberately two-regime:

1. exact V3.1 mirror / self-play seeds where fixed H10 was strongly positive;
2. exact Arlene cells where fixed H10 was decisively negative.

For every paired cell report Δown, Δrival, ΔM, selected-horizon callback counts, maximum mirror streak, every transition into/out of H10, and every negative cell. The first gate question is not “does B11 reproduce all H10 upside?” but whether the public structural certificate captures a material portion of the mirror gain **while remaining horizon-8-identical against Arlene**. Any H10 activation in malformed/gapped state is a source failure; repeated H10 activation in Arlene with the same negative signature is an economics failure.

Only after that screen should B11 be tested on Shop-Router-like field opponents. Exact public structural similarity may be a useful regime certificate, but it must not be relabeled as hidden opponent identity or private-policy inference.

## Focused predecessors

`test_b11_mirror_horizon.py` freezes the important boundaries: money exclusion; strict structural mismatch; gap reset; bool/string type confusion; missing fields; recursive JSON type equality; 8-callback warmup; immediate H8 fallback; disabled exact-parent mode; literal baseline horizon; and signature de-aliasing.

No local or hosted PASS is claimed by this commit. Exact-head CI/review truth must be bound separately.
