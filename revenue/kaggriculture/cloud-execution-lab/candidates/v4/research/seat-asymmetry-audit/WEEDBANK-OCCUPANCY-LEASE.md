# TITAN V4 — WEEDBANK as a TOWN-RNG occupancy lease

This packet strengthens the merged Gemini/Antigravity convergence disposition for **WEEDBANK / zero-cash structure carpet** inside the canonical `seat-asymmetry-audit/TOWN-RNG` authority. It is research-only: no runtime key, controller, default, config, COMPOSITION edge, archive, evaluator, provider, Kaggle or submission path is changed.

## Source-correct mechanism

Pinned official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

Three facts hold together:

1. `BUILD_COOP` converts an owned `None` tile into an empty structure without a cash debit.
2. `DIG` later removes an **empty** COOP/PASTURE back to `None`; a placed animal is not removable by this path.
3. `_spawn_weeds` consumes `rng.random()` only for `None` tiles, before later town-shop RNG consumes the same daily stream.

Therefore an empty structure is a reversible **occupancy lease**. It can suppress weed risk and the tile's weed RNG draws while present. That does not make it free: BUILD costs a unit action, restoration costs another DIG action, and the tile is unavailable for productive use while occupied.

## Direct-labor theorem: blanket carpet loses

For one otherwise-empty tile held empty over `N` end-of-day rolls with weed chance `p`, baseline can require at most one weed-cleanup DIG before a spawned weed makes the tile non-`None`.

Expected baseline cleanup is therefore

`P(weed by N) = 1 - (1-p)^N <= 1`.

A non-restored carpet costs one BUILD action. A reversible lease costs BUILD + DIG = two unit actions. So blanket prebuilding has **no direct weed-labor advantage**, even before charging tile value, travel, scheduler interference or animal/plant opportunity cost.

At standard `p=0.005`, `N=30`:

- `P(weed)` / expected direct cleanup saved = `0.13961580808530394` action per tile;
- BUILD-only direct action delta = `-0.8603841919146961`;
- BUILD + restore-DIG direct action delta = `-1.860384191914696`.

This is the source-bound reason the merged convergence lock is right to reject a blanket carpet policy.

## Surviving mechanism: shared RNG-path intervention

The RNG effect is distinct from cleanup. An empty tile consumes one daily weed RNG draw until its first weed; a structure consumes none while occupying the tile. Expected baseline draws over `N` rolls are the truncated geometric sum:

`(1-(1-p)^N)/p` for `p>0`.

At the standard 30-EOD horizon that is `27.92316161706079` expected suppressed draws per continuously occupied tile. When `weedSpawnChance=0`, direct weed benefit is exactly zero but an always-empty tile still consumes 30 RNG draws, all of which an occupied tile suppresses. That cleanly separates **RNG steering** from **weed avoidance**.

TOWN-RNG already proves that occupancy-induced weed-draw changes can alter later public shop unlock RNG. This packet gives that effect **no positive decision authority**. SEED-IDENTIFIABILITY remains binding: opening weed observations do not uniquely recover the hidden seed, and this packet authorizes no clairvoyant shop targeting.

## Best-form V4 admission boundary

Do not ship a carpet controller. A future current-native experiment may use an occupancy lease only when an existing productive/route owner independently justifies the structure, or when the arm is explicitly a bounded RNG-steering experiment. In either case it must separately charge:

- BUILD and any required restore-DIG action;
- temporary productive-tile value;
- reachability and scheduler conflicts;
- downstream public environment divergence, recording the first changed `town.unlocked_shops` path as environment-path divergence rather than pretending it is policy-identical;
- whole-game both-seat economics across a seed distribution, not a clairvoyant selected seed.

`EXPANDTAX` should use the same separation: BUY_LAND creates additional `None` tiles, increasing both weed exposure and shared RNG consumption before later shop unlocks. Those are separate externalities from deterministic productive land value.

## Carrier

- `weedbank_occupancy_lease.py` — exact source pin, direct-action theorem and RNG-draw accounting; all decision/hidden-seed/runtime authority flags are false.
- `test_weedbank_occupancy_lease.py` — exact engine blob/anchor binding, standard values, probability edges, poison rejection and authority killers.

The earlier pre-convergence prototype branch placed equivalent accounting under the obsolete standalone `research/rng-steering` home. This branch intentionally relocates the mechanism into the merged canonical TOWN-RNG sink rather than maintaining two RNG authorities.
