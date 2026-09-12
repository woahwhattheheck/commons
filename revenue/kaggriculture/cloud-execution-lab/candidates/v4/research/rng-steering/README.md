# EOD RNG steering oracle

Research-only mechanism package for the **one** canonical TITAN V4. It does not
add a controller, feature key, runtime path, default, archive, workflow, or
Kaggle submission change.

## Finding

The pinned official engine uses one end-of-day `random.Random` object, seeded as
`(episode_seed * 1_000_003) ^ day`. It passes that same object through farm 0's
weed scan, then farm 1's weed scan, and only afterwards uses it for a public town
shop unlock.

`_spawn_weeds` calls `rng.random()` once for **every tile that is currently
`None`**. The call is on the left side of the comparison with `weed_chance`, so
this draw still occurs when `weedSpawnChance == 0`. Therefore the RNG state seen
by the next shop draw is a deterministic function of the episode seed, day, and
the total count of currently-empty tiles scanned before the unlock. Occupying or
clearing one controllable tile can shift that shared stream.

This extends, rather than duplicates, the landed seat-symmetry oracle. The prior
oracle proves that the EOD weed stream is seat-indexed; this package asks a
different causal question: can player-visible farm occupancy change the RNG state
that later determines the shared public shop? The answer at the source/state
level is yes.

## Clean one-tile witness

With official seed `5`, EOD day `2`, and 25 empty NW tiles on each farm:

- baseline public unlock: `PIZZA_SHOP`;
- counterfactual: occupy only seat 1's **final scan-order empty tile** before EOD,
  leaving 25/24 empty tiles;
- counterfactual public unlock: `BRUNCH_SPOT`.

Using the final eligible tile makes the causal witness unusually clean: all farm
0 weed draws and all earlier seat 1 weed draws are identical; only the removed
last draw and later RNG consumers can differ. The shop flip still occurs with
`weedSpawnChance=0`, proving that a weed-off panel is not by itself an RNG-state
ablation for public shop selection.

## Fixed mechanism census

`panel_report()` evaluates seeds 1..256 over the eight default unlock EODs
(days 2, 5, 8, 11, 14, 17, 20, 23), with a 25/25 empty-tile baseline and a
seat-1 final-tile fill counterfactual. That is 2,048 constructed cells:

- 1,336 public shop flips;
- 712 unchanged shops;
- 65.234375% shop-flip rate in this constructed panel.

This rate is **not field EV** and is not an activation statistic. It quantifies
how often a one-draw state shift changes the public shop under one transparent
empty-count model. Exact shop identities also inherit the Python stdlib
`random.Random` behavior used by the official engine runtime.

## Seat causality

For public shop choice, only the total number of RNG draws before `choice` matters,
so a one-tile reduction on either seat reaches the same RNG state when total
empty counts match. The side effects differ:

- a seat-1 final-tile fill can preserve every earlier weed outcome and change
  only the downstream public shop draw;
- a seat-0 final-tile fill preserves seat 0's earlier weed outcomes but shifts
  the RNG stream consumed by seat 1 before the public shop.

That makes active occupancy steering a distinct mechanism from passive seed
inference (`WEEDPRINT`) and from the expected-action economics of blanket
structure occupancy (`HOMESTEAD`).

## Authority boundary

The oracle source-binds the exact official engine bytes:

- Git blob: `3c202c7ee921da239356789e266b694635103fc4`
- SHA-256: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`

It proves a **state-level causal mechanism only**. It does not prove that a
production policy can reach a desired final-scan tile at acceptable action cost,
that an alternate shop is economically preferable, or that manipulating the RNG
improves rating. A policy successor would need a current-native both-seat gate
that prices the tile action, crop/structure opportunity cost, changed weeds,
future demand vector, and terminal own/rival margin. No such promotion is made
here.

## Reproduce

From this directory:

```bash
python -B test_rng_steering.py
python -O -B test_rng_steering.py
python -B rng_steering.py --output /tmp/rng-steering.json
```

The first two commands are self-contained. The CLI additionally authenticates
the exact repository engine before emitting a report.
