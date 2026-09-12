# TERRAINBANK — empty-structure weed “action bank” falsifier

Status: **FALSIFIED_AS_ACTION_BANK** for the pinned official engine. Evidence only;
no gameplay/default/archive/Kaggle activation.

## Claim tested

The proposed mechanism was: during otherwise-idle time, BUILD_COOP or
BUILD_PASTURE across future production tiles; because `_spawn_weeds` only rolls
on `None`, those structures prevent weeds; later DIG the structure and PLANT.
The claimed advantage was that this “banks” future weed-clearing work into idle
time and reduces work on a busy planting day.

That action accounting is backwards on the pinned official engine.

## Source-bound facts

Official engine: `reference/engine/kaggriculture.py` Git blob
`3c202c7ee921da239356789e266b694635103fc4`.

* `_spawn_weeds` rolls only when `farm["tiles"][y][x] is None`; an empty
  COOP/PASTURE therefore does prevent a weed on that tile while it remains.
* BUILD_COOP and BUILD_PASTURE require the current tile to be `None`, place an
  empty structure, and have no cash mutation in their exact branches.
* DIG removes a weed **or an empty COOP/PASTURE** by setting the tile back to
  `None`; it refuses to remove a placed animal.
* Default `weedSpawnChance` is `0.005`.
* `_end_of_day` passes one `rng` through player farms sequentially, so shielding
  also changes which deterministic RNG draws are consumed elsewhere. A paired
  same-seed board is therefore not a monotone “same weeds minus covered tiles”
  counterfactual.

## Exact lower-bound action proof

Consider one future-use tile kept empty for `d` end-of-day weed rolls.

Baseline: if a weed first appears it persists, because the tile is no longer
`None`; therefore the tile needs one future DIG with probability

`q(d) = 1 - (1 - p)^d`, where `p = 0.005`.

Empty-structure shield: keeping the COOP/PASTURE in place through the same
horizon makes the future DIG probability **1**, because the structure itself must
be removed before the tile can be used. It also consumed one earlier BUILD
action. This ignores movement and routing cost, so it is the most favorable
possible accounting for the shield.

| EOD rolls before use | baseline future DIG EV | shield future DIG EV | added busy-day DIG EV | added total tile-local actions incl. BUILD |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.005000 | 1.000000 | 0.995000 | 1.995000 |
| 5 | 0.024751 | 1.000000 | 0.975249 | 1.975249 |
| 10 | 0.048890 | 1.000000 | 0.951110 | 1.951110 |
| 20 | 0.095390 | 1.000000 | 0.904610 | 1.904610 |
| 30 | 0.139616 | 1.000000 | 0.860384 | 1.860384 |

So the pure shield does not bank the future DIG. It makes that DIG certain while
adding an earlier BUILD. Clearing the structure before the last EOD only restores
weed exposure for the subsequent empty interval; it does not create a saved
action.

## Boundary

This kills only the **empty-structure weed-shield as an action-saving policy**.
It does not say COOP/PASTURE are bad when they provide animal capacity or other
productive value. A dual-use structure must be evaluated on that productive
economics, not credited with a nonexistent weed-clearing action bank.

Do not create a V4 overlay that blankets idle tiles solely for weed avoidance on
this engine blob. Re-open only if official BUILD/DIG/spawn semantics change, or
if a different dual-use mechanism supplies independently measured productive
value.

## Reproduction

From this directory inside the repository:

```bash
python -m unittest -v test_terrain_bank
python -O -m unittest -v test_terrain_bank
python verify_terrain_bank.py
```

`verify_terrain_bank.py` fail-closes on official-engine Git-blob drift and on the
required BUILD/DIG/weed/default-chance/caller anchors.
