# TITAN V4 — Gemini WEEDBANK as a reversible occupancy lease

This packet consumes the Gemini/Antigravity **WEEDBANK / zero-cost coop carpet** proposal inside the existing V4 RNG-steering research authority. It is research-only: no runtime key, controller, default, archive, evaluator, provider, Kaggle or submission path is added.

## Source verdict

Pinned official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

The useful mechanical core is real:

- `BUILD_COOP` converts an owned `None` tile into an empty `COOP` without cash cost.
- `DIG` removes plants, weeds and **empty** COOP/PASTURE tiles back to `None`; a placed animal is not removable this way.
- `_spawn_weeds` calls `rng.random()` only for `None` tiles.
- therefore an empty structure can temporarily suppress both weed risk and that tile's weed RNG draw, then be removed later.

The original framing is still too strong. "Zero cost" means zero **money**, not zero opportunity cost: BUILD consumes a unit action, restoring the tile consumes another DIG action, and the tile cannot be used for another purpose while leased.

## New labor theorem

For one otherwise-empty tile held empty for `N` EODs with weed chance `p`, baseline needs at most one weed-cleanup DIG because after a weed appears the tile is no longer `None` and receives no more weed rolls until cleared.

So expected baseline weed-cleanup actions are:

`P(weed by N) = 1 - (1-p)^N <= 1`.

A non-restored carpet costs one BUILD action; a reversible occupancy lease costs BUILD + DIG = two actions. Therefore blanket structure carpeting has **no direct weed-labor advantage**, even before charging temporary productive-tile value, travel, or scheduler conflicts.

At the standard `p=0.005` across 30 EODs:

- `P(weed)` = `0.13961580808530394`;
- expected direct cleanup saved = `0.13961580808530394` action/tile;
- non-restored BUILD-only direct action delta = `-0.8603841919146961`;
- restored BUILD+DIG direct action delta = `-1.860384191914696`.

That kills the blanket "bank actions by carpeting" interpretation.

## What still survives: RNG steering

The RNG effect is separate from weed cleanup. An empty tile consumes a draw every EOD until its first weed; a structure consumes none while present. Expected baseline draws over `N` EODs are the truncated geometric sum, `(1-(1-p)^N)/p` for `p>0`.

At the standard 30-EOD horizon this is `27.92316161706079` expected suppressed draws. With `weedSpawnChance=0`, there are still 30 suppressed RNG draws even though direct weed benefit is exactly zero. That makes the separation explicit: WEEDBANK is primarily an **occupancy/RNG-path intervention**, not a weed-labor optimization.

Existing TOWNRNG/RNGSTEER evidence already shows that changing the weed-draw cursor can change later public shop RNG. This packet deliberately gives that effect **no positive decision value**. Without an observable predictor and paired economic gate, a shop-path change is `ENVIRONMENT_PATH_DIVERGED`, not a policy win. SEEDIDENT's no-turn-1-omniscience boundary remains binding.

## Best-form V4 handoff

Do not ship a blanket carpet controller. A future field arm may test an occupancy lease only when all of these are separately proven by existing V4 authorities:

1. the structure has independent productive value **or** the experiment is explicitly testing RNG steering;
2. the tile is empty and remains animal-free;
3. BUILD reachability and any future restore-DIG reachability are executable;
4. temporary tile opportunity cost and BUILD/DIG action cost are charged;
5. every EOD records `town.unlocked_shops`, with first divergence tagged `ENVIRONMENT_PATH_DIVERGED`;
6. same-total-empty occupancy is retained as a negative control for mere geometry changes;
7. no hidden-seed reconstruction or clairvoyant shop targeting is claimed.

EXPANDTAX should consume this accounting too: BUY_LAND adds `None` tiles, which simultaneously changes weed exposure and the shared RNG cursor feeding later shop unlocks. Those effects must be reported separately from deterministic productive land value.

## Carrier

- `weedbank_occupancy_lease.py` — source-pin helper plus exact labor/RNG accounting; emits no runtime authority.
- `test_weedbank_occupancy_lease.py` — engine-blob/anchor check, standard theorem values, zero/one probability edges, type poison and authority killers.

Authoring container: source/test `py_compile` PASS; pure standard receipt probe PASS. The authoring container did not contain the repository checkout, so the committed exact-engine-path test is intentionally not claimed executed here. Run it from this directory on the reviewed checkout under normal Python and `python -O` before merge.
