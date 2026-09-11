# Riot fert-daily-sweep — repaired-P0 donor

This directory preserves Riot's `r04_fert_daily_sweep` factor as an additive donor on repaired P0 `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a` without creating another production `r04_full_router.py` writer while the sole L3 consumer owns that surface.

## Exact provenance

Original branch: `riot/v3.1-lane-b5`

Original parent: `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`

Original head: `8638d0db7068f38966424c59181875d8b128a72a`

Original factor blob: `cd6c1dd50a439f58bce9434db8d628ca8d6f978f`

Original focused-test blob: `fb51b305289a311e9e8e4a3a63c38c18c5a1fd30`

The copied `r04_fert_daily_sweep.py` in this directory is byte-identical to the original factor blob. Riot called the lane "B5", but it is **not** the shipped B5 CARROT/JIT architecture; do not alias their evidence or defaults.

## Donor theorem

The factor is default-OFF. It considers only workers whose command is exactly `PASS`:

- an idle worker on an animal tile with daily fertilizer available may become `COLLECT_FERTILIZER`;
- an idle worker beside the shed holding fertilizer may become `DROP` only when the same-day tape proves that doing so will not starve later `FERTILIZE`/`FEED` work and the worker is not carrying an animal;
- workers do not move;
- no market rows are added or reordered by this factor;
- malformed/unreadable evidence fails closed to incumbent action behavior.

The intended production seam is after `POLICY_AGENT` and before `ROW_ORDER`.

## Why this branch is additive

The repaired-P0/current convergence stack already carries B5 CARROT + JIT, H4, gated L3, sale-fertilizer, and cattle wiring, and `#12565` owns the current production-router recomposition. Replaying Riot's stale five-path wiring directly would create a competing `r04_full_router.py` lineage and could silently drop newer stack bytes.

Therefore this donor changes only files under this experiment directory. It is **not** merge/default/submission authority.

## Validation

From `revenue/kaggriculture/cloud-execution-lab/candidates/v3`:

```bash
python -B -m unittest -v experiments/riot_fert_daily_sweep_6e5/test_factor.py
```

The focused contract checks factor behavior plus the current-root preservation boundary. `DONOR.json` binds the original branch/head/blob provenance and the exact stack keys a future consumer must preserve.

## Consumption contract

Consume this factor once, only after the literal final `#12565` L3 package head exists:

1. Copy the exact `cd6c1dd50a439f58bce9434db8d628ca8d6f978f` factor bytes into the production overlay.
2. Wire it at the reviewed `POLICY_AGENT -> ROW_ORDER` seam with a new `r04_fert_daily_sweep` configuration key that remains default `false`.
3. Preserve the final package's B5 CARROT + JIT, H4, fail-closed L3, sale-fertilizer, and post-L3 cattle decision exactly; regenerate FILES/manifest through the optimizer-safe builder rather than replaying Riot's stale metadata.
4. Run the exact factor/source/package contracts on that final parent.
5. Run paired current-package economics with treatment differing only by `r04_fert_daily_sweep`; no default promotion from this donor alone.

No Actions workflow or PR is attached to this donor under the current saturated runner queue.
