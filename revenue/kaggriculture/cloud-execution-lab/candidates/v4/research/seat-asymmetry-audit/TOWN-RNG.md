# TOWNRNG — EOD weed-stream / public-shop coupling

Status: **source-confirmed causal-integrity oracle; not a gameplay policy**.

This extends the existing V4 `seat-asymmetry-audit` authority. It does not add a
controller, feature key, runtime patch, alternate V4, archive, default, workflow,
or Kaggle mutation.

## Exact source mechanism

Pinned official engine Git blob:

`3c202c7ee921da239356789e266b694635103fc4`

At end of day, the official interpreter creates one RNG:

`random.Random((seed * 1_000_003) ^ day)`

It then calls `_spawn_weeds` for farm 0, then farm 1, using that same RNG. The
weed scan calls `rng.random()` **only when the current tile is `None`**. After
both farm scans, the same RNG is used for `rng.choice(sorted(SHOPS))` when a
town-shop unlock is due.

Consequences:

- the shop RNG cursor advances by the **sum of both farms' pre-scan empty-tile
  counts**;
- redistributing the same total number of empty tiles between seats does not
  change the shop draw;
- changing total empty-tile count can change the next public shop at the same
  episode seed/day;
- `weedSpawnChance=0` removes weed placement, **not the RNG draws**. Every empty
  tile still evaluates `rng.random() < weed_chance`, so the coupling survives;
- because the shop is public and later consumes market inventory, a baseline and
  candidate can enter different public environment paths before later economic
  divergence is measured.

This is a paired-experiment confound, not a live exploit. No claim is made that a
policy can infer or target the hidden episode seed.

## Deterministic witness

On default shop cadence, `day=2` is an unlock EOD (`next_day=3`). With episode
seed 1:

- baseline pre-weed empties `[20, 20]` consume 40 RNG draws and select
  `SMOOTHIE_SHOP`;
- candidate empties `[20, 21]` consume 41 draws and select `BAKERY`;
- seat-swapping a fixed total `[13, 27] -> [27, 13]` leaves the shop unchanged;
- a counterfactual independent shop RNG leaves the shop unchanged across the
  40/41-empty pair, isolating shared-stream coupling.

`town_rng_coupling.py` reproduces this directly from Python's `random.Random`
using the exact source seed transform, draw count, sorted shop names, unlock
cadence, and shop cap.

## Gate rule for V4 economics

For any paired baseline/candidate run that can change empty-tile occupancy
(BUILD, DIG, PLANT, BUY_LAND, weed handling, land expansion, etc.), record
`town.unlocked_shops` at every EOD.

If the first shop list diverges, mark that cell
`ENVIRONMENT_PATH_DIVERGED` before attributing later market/margin changes to
the policy. Either:

1. report the downstream score separately as coupled-environment evidence, or
2. rerun the causal comparison with an explicitly controlled shop schedule /
   split-RNG experimental harness.

A changed empty count without an actual shop-choice divergence is exposure, not
proof of confounding on that cell. The RNG is re-seeded each EOD, so the gate is
day-local and should be checked at each unlock.

## Reproduce

From this directory:

```bash
python -B test_town_rng_coupling.py
python -O -B test_town_rng_coupling.py
python -m py_compile town_rng_coupling.py test_town_rng_coupling.py
python -B town_rng_coupling.py \
  --engine ../../../../reference/engine/kaggriculture.py \
  --output /tmp/TOWN-RNG.json
```

The CLI refuses engine-source drift before emitting a source claim.

## Boundaries

- `seat_symmetry_oracle.py` keeps its market-lockstep falsifier and direct
  weed-seat-stream witness.
- `TOWNRNG` adds only the downstream shared-RNG -> public-shop causal boundary.
- seed-identifiability / hidden-seed inference is a separate question.
- occupancy/weed/expansion policy economics remain with their existing owners.

`promotion_decision = NOT_ASSESSED`.
