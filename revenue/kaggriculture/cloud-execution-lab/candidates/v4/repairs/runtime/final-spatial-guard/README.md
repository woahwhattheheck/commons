# #12019 current-ABI final SpatialTempo guard

Operation: `TITAN-V4-12019-FINAL-SPATIAL-GUARD-CURRENT-ABI-20260919-01`

This is the current-source redrive of the historical final-pressure idle-fertilizer ledger rebind. It is a repair carrier inside the existing V4 repair tree, not a sibling V4 root and not independent promotion authority.

## Live defect

The canonical wrapper already lets `SpatialTempo.guard_returned()` validate an idle-FERT `DROP` plus unique `SELL FERTILIZER 1` before the wrapper's late market finalizers. The wrapper then permits final pressure, town procurement, and overflow preservation to alter the returned market bytes. `SpatialTempo.finish()` commits afterward using `_sale_proposal['slot']`. A valid late reorder can therefore leave the proposal bound to a stale slot and lose the ledger receipt even though the engine-facing sale executes.

The current shared guard already owns the safe semantics needed for the redrive: it accepts only the current proposal, requires the paired DROP when a worker is bound, requires exactly one exact `SELL FERTILIZER 1`, rebinds the proposal to that final slot, and fails the paired action closed when the lot is missing or ambiguous.

## Current-ABI repair

After every existing late market transform, and only on a completed producer result, call the same `spatial.guard_returned(obs, returned)` once more immediately before `_early_capital_selected()` returns. Checkpoint those fully guarded bytes as `spatial_final_guard`.

This placement is deliberately after pressure/procurement/overflow and before the outer runtime can call `SpatialTempo.finish()`. Deadline fallback does not start this additional guard.

## Source custody

The carrier is bound to exact Git blobs:

- `main.py`: `727c36ee3727db159f5879d4ac9a842a28ca570c`
- `spatial_tempo.py`: `a2f13cd9871e6da24b2ccf3297c4c96ac324100e`
- serial base used for this recovery: `7c3b010b77f1fe16fdeffb5a4601504a284c616a`

Any source drift fails closed before materialization. The carrier refuses in-place canonical mutation.

## Contracts

`test_current_abi.py` proves:

- the exact current source identities;
- the literal current predecessor loses the ledger slot after a late FERT/CARROT reorder;
- the candidate rebinds to the final returned slot and checkpoints those bytes;
- a duplicate final fertilizer sale fails closed together with the paired DROP;
- no proposal is identity-equivalent; and
- deadline fallback does not start the new final guard.

Run from this directory:

```bash
python -m unittest -v test_current_abi.py
python -O -m unittest -v test_current_abi.py
python apply_repair.py --tree ../../../../../../../.. --output /tmp/main.final-spatial-guard.py --receipt /tmp/final-spatial-guard.json
python -m py_compile /tmp/main.final-spatial-guard.py
```

Composition into canonical `main.py` requires the one-tree queue; this carrier itself changes no runtime/config/CURRENT/CANONICAL/COMPOSITION/INTEGRATION/archive/release/Kaggle/ref state.
