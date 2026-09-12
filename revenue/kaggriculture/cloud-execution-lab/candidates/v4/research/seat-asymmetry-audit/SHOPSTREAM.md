# SHOPSTREAM — farm-tile RNG cursor can change public shop unlocks

Status: **source mechanism confirmed; exact-checkout execution pending; policy reachability/economics not assessed**.

Canonical home: `main:revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/seat-asymmetry-audit`.
This is an additive extension of the existing shared-RNG/seat-asymmetry source authority, not another
controller, feature key, runtime transform, composition edge, V4 root, archive, or Kaggle submission.

## Mechanism

The authenticated official engine (Git blob `3c202c7ee921da239356789e266b694635103fc4`,
SHA-256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`) creates
one end-of-day RNG from `(episode_seed * 1_000_003) ^ day`. It then processes farm 0 and farm 1
in order. `_spawn_weeds` consumes one `rng.random()` call for every tile that is `None` when scanned.
After both farms have consumed that shared stream, the same RNG object is used for
`rng.choice(sorted(SHOPS))` when a town-shop unlock is due.

Consequently, **tile occupancy changes the RNG cursor seen by the public shop draw**. The important
quantity for the shop cursor is the number of empty tiles scanned before the draw, not whether a
weed actually spawns. Setting `weedSpawnChance=0` prevents weed creation but does not prevent
`rng.random()` from being evaluated on each empty tile, so it does not remove this coupling.

This is distinct from the existing seat-asymmetry oracle's proven fact that farms receive different
segments of the shared weed RNG stream. SHOPSTREAM binds the downstream *public town state* consequence:
a source-real change to empty-tile count can change which shop is appended.

## Exact-engine witness and pending execution gate

`town_shop_rng_oracle.py` authenticates the exact official engine bytes and is built to execute its real
`_end_of_day` function on a complete checkout. A static `COOP` is used as the one-tile occupancy toggle so plant/animal refresh
cannot confound the witness. `weedSpawnChance=0` is deliberate.

At day argument 2 (unlock of next day 3), with only the default NW quadrant unlocked:

- baseline: both farms have 25 empty NW tiles, so 50 weed-scan RNG draws precede the shop draw;
- variant: one NW tile on farm 0 is a static `COOP`, so 49 draws precede the shop draw;
- seed 5: baseline unlocks `PIZZA_SHOP`; the one-tile variant unlocks `BRUNCH_SPOT`.

The source-equivalent RNG model predicts the following 512-seed result (seeds 1..512); the committed
exact-engine suite asserts these same counts and must be run from a complete checkout before this is
recorded as an execution receipt:

| Result | Cells |
| --- | ---: |
| shop changed after one static-tile toggle | **337** |
| shop unchanged | 175 |
| pure cursor-model mismatches vs exact engine | **0** |
| mismatch when the same one filled tile is moved from farm 0 to farm 1 | **0** |

The last control matters: for public shop choice, `(24 empty, 25 empty)` and `(25, 24)` consume the
same total of 49 `random()` calls before `choice`, even though the farms themselves receive different
segments of that stream.

## Strategic boundary

This is a mechanism receipt, not a policy recommendation. It does **not** establish that:

- the episode seed (or enough RNG state) is observable/predictable by the live agent;
- current TITAN naturally reaches a safe, output-changing occupancy decision immediately before an unlock;
- keeping, adding, digging, harvesting, or planting a tile for RNG position is free;
- a preferred shop can be selected reliably against opponent occupancy;
- any such choice improves score, margin, or hosted win rate.

The next useful gate is therefore **reachability before strategy**: replay-capable owners should look
only at callbacks immediately preceding shop-unlock EODs, record the exact post-refresh empty-tile count
for both farms and whether TITAN had a source-legal, otherwise-neutral occupancy choice. If such a
witness exists, town/route owners can evaluate economics. Do not add a standalone SHOPSTREAM controller.

## Reproduce

From this directory in a complete Commons checkout:

```bash
python -B test_town_shop_rng_oracle.py
python -O -B test_town_shop_rng_oracle.py
python -B town_shop_rng_oracle.py --output /tmp/shopstream.json
python -B -m py_compile town_shop_rng_oracle.py test_town_shop_rng_oracle.py
```

The oracle fails closed on official-engine byte drift or on reordering/removal of the source anchors
that bind RNG creation, weed scans, and shop choice. Local pre-publication preflight covered `py_compile`
and the source-equivalent 512-seed cursor model (337 changed / 175 unchanged); that is not a substitute
for the repo-mounted exact-engine test.
