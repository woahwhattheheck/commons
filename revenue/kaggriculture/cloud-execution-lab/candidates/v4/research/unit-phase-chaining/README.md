# TITAN V4 — Unit-phase chaining (TILEPIPE + UNITPIPE admission)

Research-only, source-bound evidence for a Kaggriculture engine seam plus one conservative, default-OFF returned-action admission experiment. This package does **not** change the controller, runtime, config, feature defaults, archive, submission, or composition graph.

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

The executable oracle proves each positive witness against its reversed actor order and includes a distinct-tile negative control. It also pins the existing atomic seed rule: two WHEAT `PLANT` requests with one WHEAT seed are both converted to `PASS`; actor ordering cannot escape seed collateral.

## Converged UNITPIPE admission experiment

`unit_pipeline_admission.py` is the unique implementation delta recovered from superseded PR #12866 after this package became the canonical source-mechanism authority. #12866 is closed unmerged so V4 does not carry a second unit-order package.

The helper is deliberately much narrower than the source theorem. With `enabled=False` it returns exact action identity. With `enabled=True` it may only reorder **already-authored**, already-co-located, actor-local-inventory-neutral rows:

- empty tile: existing `PLANT -> WATER`;
- observed `WEED`, empty `COOP`, or empty `PASTURE`: existing `DIG -> PLANT [-> WATER]`.

It never invents a row, actor, movement, crop, quantity, or market order. It preserves the raw `PLANT` multiset and refuses engagement when whole-vector same-crop PLANT demand exceeds observed seeds, so the official atomic collateral rule cannot be bypassed. It also refuses inventory/service-dependent rows such as `PLACE`, `FERTILIZE`, `FEED`, `CARE`, `HARVEST`, `PICKUP`, and `DROP`; TILEPIPE's source witnesses for those operations remain evidence-only until actor-local inventory/lifecycle admission is separately proven.

This helper is **not runtime-wired** and has no activation authority. Its first legitimate consumer is the current-native returned-action census: locate natural authored vectors that are already co-located and merely ordered causally backward, then measure changed actions, movement/opportunity cost, fallback/deadline behavior, and both-seat terminal economics. Zero natural engagements means `COLD_CURRENT_NATIVE`, not theorem falsification.

## What this does not authorize

- No same-callback market credit. Unit actions happen before `BUY_SEED`, `BUY_PRODUCT`, `BUY_ANIMAL`, `HIRE`, and other market commits, so a unit pipeline may use only inventory/seeds/workers already physically present before the callback.
- No cross-actor inventory transfer. A later `PLACE`/`FERTILIZE`/`FEED` must be collateralized by that later actor's own carried inventory unless an existing engine operation moved it earlier.
- No immediate annual-crop harvest. `HARVEST` rejects a plant whose age is below that crop's `first_yield_day`; a legal `HARVEST -> PLANT` chain begins from an already-mature non-ongoing crop with positive yield.
- No blanket instruction to co-locate workers. Movement, hire cost, lost parallelism, route displacement, and terminal economics are outside this source theorem.
- No new scheduler/controller. This package is one invariant/oracle/admission authority for existing LABORFLOW/route/composition owners to consume.

## Validation

From this directory on a complete Commons checkout:

```bash
python -B test_unit_phase_chaining.py
python -O -B test_unit_phase_chaining.py
python -B test_unit_pipeline_admission.py
python -O -B test_unit_pipeline_admission.py
python -B unit_phase_chaining.py --out /tmp/tilepipe.json
python -B -m py_compile unit_phase_chaining.py unit_pipeline_admission.py test_unit_phase_chaining.py test_unit_pipeline_admission.py
```

The source checker fails closed if the canonical engine blob moves, if farmer/hand execution order changes, if hand iteration is no longer literal `enumerate(hands_actions)`, if market moves ahead of the unit phase, or if the atomic PLANT preflight changes. The admission tests additionally pin OFF identity, same-site-only eligibility, market/unrelated-row preservation, global seed collateral, destructive-state refusal, and refusal of inventory/service-dependent groups.

## Next gate

Census the **current canonical native returned unit-action surface** for callbacks with two or more actors already co-located on a tile where an earlier authored action enables a later authored action. Separate source-theorem opportunities from the narrower admission helper's natural engagements. Measure actual action recovery, movement opportunity cost, seed/inventory collateral, fallback/deadline behavior, and both-seat economics.

Disposition: `SOURCE_MECHANISM_CONFIRMED_ADMISSION_DEFAULT_OFF_CURRENT_NATIVE_ECONOMICS_UNASSESSED`.
