# E7 — guaranteed center-tick sale-advance veto

## Source fact

The pinned Kaggriculture interpreter processes farm work, then `_process_market`, then `_town_consume`. `_town_consume` subtracts one unit of every non-fertilizer town-center product on `step % townCenterSellInterval == 0` (default 24) and refreshes prices afterward. Market SELLs therefore execute **before** that deterministic inventory subtraction.

Current V3.1 R04/E184 starts its multi-turn `reserve_sales` window at step 288. Its inherited `step % 4 == 0` no-advance guard applies only before step 144, so it does not protect the live E184 window from pulling a future sale onto a later town-consumption tick.

## Why this is an experiment, not a theorem

A naive claim that “waiting through a town tick is always better” is false as a public-state theorem. The rival market queue for the current step is hidden. Rival supply can hit the shared market before the town subtraction, and rival supply on the later sale step can also change per-unit lockstep quotes. Deterministic town demand therefore creates a price-reset opportunity, not a guaranteed domination result.

E7 deliberately avoids pretending otherwise. It changes one factor only: on guaranteed 24-step town-center ticks at/after E184 `ADVANCE_START`, the experiment prevents E184 from **advancing non-fertilizer future SELLs** into the pre-consumption market. It does not delete or rewrite authored/current SELL rows. The future authored sale remains available unless another parent rule changes it. FERTILIZER keeps the exact parent E184 behavior because the town center never consumes fertilizer.

The wrapper runs the original reservation function on deep-copied action/state for telemetry before applying the veto. `REPORT` records counterfactual activation count, skipped rows/units and a bounded trace, without mutating the live action/state through that diagnostic path.

## Exact evaluator tuple

`candidate.py` binds the ready-submission V3.1 R04 tuple:

- `r04_sale_horizon = 8`
- `r04_open_roundtrip = 0`
- row order ON
- evening flush ON
- sale fertilizer ON
- cattle early ON
- E7 center-tick veto ON

The experiment lives entirely under `candidates/v3/experiments/**` and is outside deterministic `build_v3.source_shas()` / submission package inputs.

## Decision gate

No score, promotion or default claim is made here. The next useful test is exact paired execution against exact V3.1 on identical opponents/seeds/seats, reporting competitive ΔM, every negative cell, E7 `counterfactual_activations`, `skipped_units`, and per-step/item trace. Because the source theorem is intentionally non-dominating, an inactive panel is a lane kill and a positive mean with concentrated negative cells is not sufficient on its own.

This branch must not change canonical archives, generated config/defaults, evaluator/opponent semantics, provider state, Kaggle state or submission state.
