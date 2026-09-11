# Riot fert-daily-sweep — repaired-P0 donor

This directory preserves Riot's `r04_fert_daily_sweep` factor as an additive donor on repaired P0 `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a` without creating another production `r04_full_router.py` writer while the sole L3 consumer owns that surface.

## Exact provenance

Original branch: `riot/v3.1-lane-b5`

Original parent: `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`

Original head: `8638d0db7068f38966424c59181875d8b128a72a`

Original factor blob: `cd6c1dd50a439f58bce9434db8d628ca8d6f978f`

Original focused-test blob: `fb51b305289a311e9e8e4a3a63c38c18c5a1fd30`

The copied `r04_fert_daily_sweep.py` in this directory remains byte-identical to the original factor blob. Riot called the lane "B5", but it is **not** the shipped B5 CARROT/JIT architecture; do not alias their evidence or defaults.

## Source-safety correction

Independent review of the frozen official engine found that the original donor's delivery theorem is too broad to consume directly. Official unit actions run **before** market processing. For `DROP`, the engine transfers only `min(worker_inventory, shed_room)` and then deletes the entire worker inventory, so a full or nearly-full shed can discard overflow. A same-step `SELL` cannot create room in time to make that DROP safe. `shedCapacity` is configurable, so a source wrapper must not assume the default value 100.

The original Riot bytes are intentionally preserved for provenance. `safe_consume.py` is the current source-safe consumption theorem:

- fertilizer collection remains available only for exact literal `PASS`, a known animal tile, and exact boolean `fertilizer_available is True`;
- synthetic DROP is disabled unless the caller supplies an exact non-negative integer `shed_capacity` from the live environment configuration;
- the worker's **entire** strict non-negative inventory must fit in the shed at unit-action time;
- multiple wrapper-authorized DROPs reserve their complete payload in farmer/hand execution order;
- any earlier unit command other than PASS/COLLECT_FERTILIZER (or a DROP already authorized by the wrapper) blocks a later synthetic DROP rather than guessing whether that command changes shed occupancy;
- later tape FERTILIZE/FEED work and animal cargo still block DROP;
- same-step market rows are never used as capacity evidence and are never changed;
- malformed capacity, shed, worker inventory, positions, commands, or callback structure fail closed to incumbent action behavior.

This correction is source custody only. It carries no economics claim; the original lane's old behavior must not authorize the safe wrapper.

## Why this branch is additive

The repaired-P0/current convergence stack already carries B5 CARROT + JIT, H4, gated L3, sale-fertilizer, and cattle wiring, and `#12565` owns the current production-router recomposition. Replaying Riot's stale five-path wiring directly would create a competing `r04_full_router.py` lineage and could silently drop newer stack bytes.

Therefore this donor changes only files under this experiment directory. It is **not** merge/default/submission authority.

## Validation

From `revenue/kaggriculture/cloud-execution-lab/candidates/v3`:

```bash
python -B -m unittest -v \
  experiments/riot_fert_daily_sweep_6e5/test_factor.py \
  experiments/riot_fert_daily_sweep_6e5/test_safe_consume.py
```

`test_factor.py` preserves the original donor provenance contract. `test_safe_consume.py` kills the official-engine overflow/order failure classes without touching production R04. `DONOR.json` binds both layers.

## Consumption contract

Consume this factor once, only after the literal final `#12565` L3 package head exists and only if the lane is still worth an economics spend:

1. Preserve the exact original `cd6c1dd50a439f58bce9434db8d628ca8d6f978f` bytes as provenance, but port the **safe_consume.py theorem**, not the original unrestricted DROP path, into production.
2. Wire it at the reviewed `POLICY_AGENT -> ROW_ORDER` seam with a new `r04_fert_daily_sweep` configuration key that remains default `false`.
3. Pass the live configuration's exact `shedCapacity` into the safe delivery seam. Missing/malformed capacity must mean collection-only, never guessed default capacity.
4. Preserve the final package's B5 CARROT + JIT, H4, fail-closed L3, strict row-shed, sale-fertilizer, and post-L3 cattle decision exactly; regenerate FILES/manifest through the optimizer-safe builder rather than replaying Riot's stale metadata.
5. Run both source contracts on that final parent, then paired current-package economics with treatment differing only by `r04_fert_daily_sweep`; no default promotion from this donor alone.

No Actions workflow or PR is attached to this donor under the current saturated runner queue.
