# C4 quiet-slot WHEAT sale experiment

## Scope

Default-OFF / experiment-only. This directory is outside deterministic V3 package inputs and does not change `overlay/**`, `TITAN-CONFIG.json`, canonical artifacts, evaluator/opponent sources, provider state, or Kaggle state.

Live V3.1 already runs E184's horizon-8 sale reservation for every product except WHEAT. A structural census of the exact 13 R04 tapes found that ordinary non-WHEAT future sales are already pulled predominantly into low-row-count current slots by E184, so a generic “schedule jamming” layer would duplicate shipped behavior. WHEAT is the only residual source seam.

C4 exposes only future authored WHEAT SELL rows to the exact existing E184 reservation machinery when:

1. the current action has strictly fewer own market rows than the future due tape action; and
2. moving the sale earlier crosses no deterministic public WHEAT town-demand tick.

It does not read hidden rival state. E184 continues to own projected-stock bounds, current/future PICKUP and BUY_PRODUCT blockers, 72-step route boundaries, debt accounting, item-price floor, animal-PLACE conservatism, and the 10-row cap. Non-WHEAT reservation behavior is delegated to the exact base function.

## Why the public-demand guard exists

An intentionally broad development probe removed WHEAT from E184's exclusion without the C4 guards. Against exact vendored Arlene on frozen seeds `2611151001..2611151008`, both candidate seats, under the pinned official Kaggriculture interpreter (`kaggle-environments 1.32.7`, upstream `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`), it produced 12 positive / 4 negative paired margin cells, mean `+12.0625`, while **own score fell by 9.125/game** and rival score fell by 21.1875/game. That is an externality signal, not clean monetization.

The guarded C4 predicate on the same frozen Arlene panel produced:

- 16/16 positive paired margin cells;
- mean paired `ΔM +17.3125`, median `+20.5`, min `+2`, max `+29`;
- mean own-score delta `+8.25`;
- mean rival-score delta `-9.0625`;
- zero evaluator failures/timeouts.

Per-seed paired `ΔM` (seat0 / seat1):

- 1001: `+19 / +19`
- 1002: `+7 / +7`
- 1003: `+23 / +23`
- 1004: `+2 / +2`
- 1005: `+22 / +22`
- 1006: `+12 / +12`
- 1007: `+29 / +29`
- 1008: `+24 / +25`

The exact experiment module reproduced the earlier direct source-patch terminal scores on seeds 1001 and 1002 in both seats before publication.

## Truth boundary

This is **development evidence**, not an official promotion receipt or leaderboard claim. The result is small and currently single-opponent. Before any production wiring, a successor gate should materialize the exact current candidate on the official frozen package path and run at least one materially different strong opponent plus the fleet D3 externality receipt (`Δown`, `Δrival`, `Δmargin`). Any regression in own score on a representative mixture is a hold/reject signal.
