# TITAN V2 disabled-SpatialTempo identity regression

This packet isolates a structural V2 regression that survives after the three optional V2 market features are disabled. It contains a one-hunk patch, a source-level invariant test, and a compact receipt for the two already-spent Apex witness cells selected by the upstream V1-versus-V2 factorial.

## Finding

`TitanAgent._initialize()` constructs `SpatialTempo` and invokes `install()` whenever the frozen consumer is active and the terminal route is not selected. That call still occurs when both `spatial_pathing` and `spatial_tempo` are false.

Before this patch, `SpatialTempo.install()` always replaced `controller.act`. Every call through that wrapper ran `_begin()` before `transform()` reached its disabled-feature return. `_begin()` rebuilt `controller.R` from the route table captured at installation, so a nominally disabled feature erased producer route mutations. Disabled configuration therefore was not behavioral identity.

The safe module-level invariant is:

```python
if not (self.pathing or self.tempo):
    return
```

Place it at the start of `SpatialTempo.install()`, before capturing `controller.R` or replacing `controller.act`. Keeping the invariant in the module protects every caller rather than only the current runtime branch.

## Causal chain

Both spent failure cells have the same first action divergence at step 30: the affected candidate hand emits `BUILD_PASTURE` in the unpatched V2 core where V1 emits `PASS`. At step 88, that earlier state changes the candidate market row from selling two fertilizer to selling three. The extra sale crosses the cow-purchase threshold and changes post-step candidate money from `$335` to `$31`; the same `$304` deficit remains at the step-95 day end (`$431` versus `$127`).

The guard restores all 97 pre-state, joint-action, and post-state hashes through step 96. Full fresh-process replays then restore V1 exactly:

| Apex witness | V1 terminal scores | Unpatched V2 core | Guarded V2 core | Guarded trace result |
|---|---:|---:|---:|---|
| seed `2609097303`, candidate seat `1` | `[102918, 101269]` | `[44068, 50435]` | `[102918, 101269]` | exact V1 SHA-256 |
| seed `2609097306`, candidate seat `0` | `[105279, 106062]` | `[83173, 81151]` | `[105279, 106062]` | exact V1 SHA-256 |

The full trace digests, source hashes, environment hashes, and action/cash witnesses are in [`receipt.json`](receipt.json). The source bundle and raw benchmark traces are intentionally not committed.

## Verification

Run the source invariant against an unpatched and patched module:

```bash
python test_disabled_spatial_identity.py /path/to/unpatched/spatial_tempo.py  # expected exit 1
python test_disabled_spatial_identity.py /path/to/patched/spatial_tempo.py    # expected exit 0
python verify_receipt.py                                                       # expected PASS
```

The negative control matters: it proves the test detects the exact failure mode rather than merely importing successfully.

## Integration gate

1. Port or apply [`disabled-spatial-identity.patch`](disabled-spatial-identity.patch) to the V3 candidate source.
2. Require the identity test whenever both spatial switches are false.
3. Re-run the two spent Apex cells and require exact V1 terminal scores and trace SHA-256 values from the receipt.
4. Re-run the owner’s broader acceptance panel before any archive or submission pointer changes.

## Scope

This is a causal regression proof on two preselected, already-spent cells. It uses zero fresh seed cells and makes no standalone leaderboard-strength claim. Its value is removing a masked structural loss from the V3 baseline so subsequent experiments measure their own behavior rather than an unintended disabled-wrapper side effect.
