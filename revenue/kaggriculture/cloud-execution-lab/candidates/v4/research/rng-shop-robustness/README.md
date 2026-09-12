# V5 RNG shop robustness research

This component turns the current pinned engine's shop-unlock RNG coupling into an exact, auditable research primitive. It does **not** activate a gameplay policy and it does not modify the frozen V4 package, runtime, defaults, config, archive, or Kaggle artifact.

## Source contract

Pinned engine Git blob: `3c202c7ee921da239356789e266b694635103fc4` (`reference/engine/kaggriculture.py`). At end of day it constructs:

`random.Random((seed * 1_000_003) ^ day)`

Then, for every farm, `_spawn_weeds` performs exactly one `rng.random()` for every tile whose value is `None`. Plant and animal daily refreshes contain no RNG calls. After all farms are scanned, an eligible shop unlock uses `rng.choice(sorted(SHOPS))`. Therefore the shop cursor depends on the **total number of None tiles across all farms**, not on which seat contributed each draw.

The default unlock interval is 3 days, unlocks are with replacement, and the total shop-instance cap is 8.

## What the solver certifies

`rng_shop_robustness.py` provides:

- `shop_unlock_due`: the exact unlock cadence/cap predicate;
- `shop_draw`: exact pinned-source shop prediction from seed/day and per-player empty counts;
- `stable_shop_intervals`: maximal total-empty-count windows that map to the same exact shop;
- `robust_options`: evaluates each caller-supplied reachable own count against **every** caller-supplied rival count. It reports an exact shop only if every rival count agrees, and target-set robustness only if every outcome lies in the target set.

No probability is inferred from an uncertainty set.

`cursor_reachability.py` closes the previously external one-turn mechanics boundary for a represented final-tick state:

- unit actions run before market and EOD;
- every distinct worker standing on an owned `None` tile can leave it empty or fill it with `BUILD_COOP`/`BUILD_PASTURE` without cash or seed dependency;
- every distinct worker standing on an owned non-animal nonempty tile can leave it occupied or clear it with `DIG`;
- therefore the complete unit-only reachable own-`None` counts form one contiguous integer interval; duplicate workers on the same tile contribute only once;
- `BUY_LAND` runs after unit actions but before EOD and converts every still-`LOCKED` tile in the next quadrant to `None`;
- a current-shed `SELL` is worth at least the engine's `$1` price floor, so the helper can certify a later `BUY_LAND` even under arbitrary opponent market behavior when current cash plus enough pre-land shed sales covers its cost;
- market-slot limits mirror the engine exactly as `max(1, int(maxMarketOrdersPerTurn))`.

The result is a fail-closed `CursorReachability` certificate plus `robust_shop_options_from_state`, which feeds only mechanically certified own counts into the shop solver. If same-tick carried-inventory `DROP -> SELL` could change whether land is fundable, the helper refuses to return an incomplete certificate rather than guessing. The guaranteed-sale calculation also respects the engine's 99,999 committed-unit loop ceiling per order.

## Fresh-loss-seed result

The two exact public-loss rematch seeds recorded on V5 main reveal nontrivial stable cursor windows:

- Sian loss seed `2051966578`, end-of-day `5` (unlocking day 6): total `None` count `42..47` yields `BRUNCH_SPOT` for all six cursor positions.
- Sian loss seed `2051966578`, end-of-day `11` (unlocking day 12): total `None` count `33..37` yields `BAKERY` for all five positions.
- Gracie loss seed `1378040481`, end-of-day `14` (unlocking day 15): total `None` count `42..46` yields `BAKERY` for all five positions.

The original constructed witness remains useful: own count `22` plus rival uncertainty `20..25` produces totals `42..47`, hence exact `BRUNCH_SPOT` on Sian's day-6 unlock. The new reachability layer does **not** relabel that witness as a historical replay state; an exact replay state can now be passed to `robust_shop_options_from_state` to decide the one-turn question without hand-waving.

## Run

From this directory:

```text
python -B test_rng_shop_robustness.py
python -O -B test_rng_shop_robustness.py
python -B test_cursor_reachability.py
python -O -B test_cursor_reachability.py
```

Both suites pin the same engine Git blob. The reachability suite also source-checks interpreter ordering (`unit -> market -> EOD`) and the exact `DIG`/`BUILD_*`/`BUY_LAND` mutation contracts.
