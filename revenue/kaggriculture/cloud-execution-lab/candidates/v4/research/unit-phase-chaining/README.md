# TITAN V4 — Unit-phase chaining (TILEPIPE)

Research-only, source-bound evidence for a previously unregistered Kaggriculture engine seam. This package does **not** change the controller, runtime, config, feature defaults, archive, submission, or composition graph.

## Exact mechanism

Canonical engine authority: `reference/engine/kaggriculture.py` Git blob `3c202c7ee921da239356789e266b694635103fc4`.

For each player callback, the interpreter first computes one atomic same-crop `PLANT` collateral check across the farmer and every hand. It then executes the farmer (`actor 0`) and hands (`actor 1..N`) **sequentially in list order**, mutating the shared farm after every unit action. The market phase starts only after the player unit loops finish.

That makes a narrow class of same-callback, same-tile pipelines mechanically real when the later actor already owns every non-tile prerequisite:

| Earlier actor | Later actor | Source consequence |
| --- | --- | --- |
| `DIG` weed/empty structure | `PLANT crop` | later actor sees `None` and can plant immediately, subject to the callback-wide seed preflight |
| `HARVEST` mature non-ongoing crop | `PLANT crop` | harvest clears the tile to `None`; later actor can replant immediately |
| `FERTILIZE` | `WATER` | later water sees the just-written `fertilized_until_day` and receives the fertilizer watering bonus in the eligible window |
| `BUILD_COOP` / `BUILD_PASTURE` | `PLACE animal` | later actor can place onto the just-built matching structure **only if that actor already carries the animal** |

The executable oracle proves each positive witness against its reversed actor order and includes a distinct-tile negative control. It also pins the existing atomic seed rule: two WHEAT `PLANT` requests with one WHEAT seed are both converted to `PASS`; TILEPIPE cannot use actor ordering to escape seed collateral.

## What this does not authorize

- No same-callback market credit. Unit actions happen before `BUY_SEED`, `BUY_PRODUCT`, `BUY_ANIMAL`, `HIRE`, and other market commits, so a unit pipeline may use only inventory/seeds/workers already physically present before the callback.
- No cross-actor inventory transfer. A later `PLACE`/`FERTILIZE`/`FEED` must be collateralized by that later actor's own carried inventory unless an existing engine operation moved it earlier.
- No blanket instruction to co-locate workers. Movement, hire cost, lost parallelism, route displacement, and terminal economics are outside this source theorem.
- No new scheduler/controller. This is an invariant + oracle for existing LABORFLOW/route/composition owners to consume.

## Validation

From this directory on a complete Commons checkout:

```bash
python -B test_unit_phase_chaining.py
python -O -B test_unit_phase_chaining.py
python -B unit_phase_chaining.py --out /tmp/tilepipe.json
```

The checker fails closed if the canonical engine blob moves, if farmer/hand execution order changes, if hand iteration is no longer literal `enumerate(hands_actions)`, if market moves ahead of the unit phase, or if the atomic PLANT preflight changes.

## Next gate

Census the **current canonical native returned unit-action surface** for callbacks with two or more actors already co-located on a tile where an earlier authored action enables a later authored action. Measure actual action compression, movement opportunity cost, seed/inventory collateral, fallback/deadline behavior, and both-seat economics. Zero natural opportunities means `COLD_CURRENT_NATIVE`, not that the engine theorem is false.

Disposition: `SOURCE_MECHANISM_CONFIRMED_CURRENT_NATIVE_ECONOMICS_UNASSESSED`.
