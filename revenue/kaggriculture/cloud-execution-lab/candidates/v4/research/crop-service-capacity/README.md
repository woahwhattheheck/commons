# CROPSCALE — source-derived crop service capacity

This package is a **V4 research/admission primitive**, not another crop policy, router, scheduler, or controller.

## Why this exists

Historical merged PR **#9806 (FLORA)** replaced a fixed crop cap with a worker/service-load bound and reported a +$5,315.75 mean improvement against its shipped checkpoint on two paired development seeds. That donor used policy allowances (`0.52`, `3.2`, `1.45`) rather than engine constants, so CROPSCALE does **not** transplant its formula.

The current official engine blob `3c202c7ee921da239356789e266b694635103fc4` provides a harder theorem:

1. `PLANT` calls `_new_plant(...)`.
2. `_new_plant` initializes `consecutive_unwatered = 1` and `watered_today = False`.
3. At end of day, an unwatered plant increments `consecutive_unwatered`.
4. At `>= 2`, the plant becomes a weed.

So a new crop site that still exists after the same EOD needs at least **two unit actions before EOD: PLANT + WATER**. Movement, seed collateral, fertilizer, harvest, animal service, shed work, and every other action only consume additional capacity.

## Land-bound correction

The first CROPSCALE revision capped both impossibility ceilings by **currently empty owned tiles**. That is not one-sided safe. In the same official engine, `_process_market` executes `BUY_LAND` atomically after the callback's unit actions, and `_do_buy_land` immediately converts the next locked quadrant's `LOCKED` cells to `None`. Those cells are therefore available to later same-day callbacks. `DIG` and some `HARVEST` actions can also reclaim occupied cells.

`empty_owned_tiles` remains useful telemetry, but it is **not a hard future physical cap** unless a caller separately proves no land acquisition or tile reclamation. CROPSCALE now caps its impossibility envelopes by the total rectangular board cell count observed in `farm["tiles"]`. That is deliberately generous: it may credit locked or occupied cells whose cash/action path is actually impossible. Over-credit is correct for an impossibility bound; under-credit is not.

## API

`capacity_envelope(observation, configuration=None)` returns two ceilings:

- `current_labor_ceiling`: conditional only on taking **no future HIRE credit**. It uses farmer + currently present hands across callbacks remaining, and caps by total observed board cells. It does not assume the current empty-owned set is frozen.
- `absolute_action_ceiling`: a deliberately loose hard upper bound. It grants the full `maxMarketOrdersPerTurn` as successful HIRE rows after every remaining callback, gives every new hand every later unit-action slot, ignores cash and all competing market/LAND work, and caps only by total observed board cells.

The envelope also reports both `empty_owned_tiles` and `board_tiles` so downstream planners can apply stronger separately-proved land/reclamation constraints without weakening CROPSCALE's one-sided theorem.

`assess_proposed_expansion(...)` returns only:
- `IMPOSSIBLE_ACTION_BUDGET`, or
- `NOT_CERTIFIED`.

It never returns SAFE. Passing the action-count bound does not prove movement, seed availability, target assignment, land acquisition, tile reclamation, watering route, market execution, or economic value.

## Ownership boundaries

CROPSCALE does not:
- choose crop species or quantities from prices/demand;
- alter MELON/STRAWBERRY/WHEAT economics;
- claim animal acquisition/collection throughput;
- allocate workers or movement routes;
- credit same-callback BUY_SEED or HIRE before unit execution;
- prove BUY_LAND/DIG/HARVEST feasibility merely because the envelope over-credits their possible cells;
- modify returned actions, config defaults, runtime, archive, or Kaggle state.

It is intended as an input to the existing single V4 planner/composition path.

## Reproduce

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/crop-service-capacity
python -B test_crop_service_capacity.py
python -O -B test_crop_service_capacity.py
python -m py_compile crop_service_capacity.py test_crop_service_capacity.py
```

Expected: **20 tests pass** in each mode.

## Evidence limits

The historical +$5,315.75 result belongs to PR #9806's old policy and is donor evidence only. This package makes **no current-native EV claim** and activates nothing. Its contribution is replacing a stale heuristic crop-cap concept with a conservative source-derived action-budget theorem while refusing false impossibility from a merely current empty-tile snapshot.
