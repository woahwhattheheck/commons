# TITAN V3 T02 — land-unlock JIT

Operation: `TITAN-V3-T02-LAND-UNLOCK-JIT-20260910-01`

This additive candidate consumes only the open `land_unlock_timing` lane. It
does not change the canonical TITAN source, config, archive, pointers, provider,
or Kaggle submission.

## Causal boundary

The pinned official mechanics allow movement onto `LOCKED` tiles. Tile-changing
operations such as `PLANT`, `WATER`, `HARVEST`, `BUILD_*`, `FEED`, and `CARE`
remain no-ops until the quadrant is owned. Therefore a represented route does
not need `BUY_LAND` before its first movement into the target quadrant; it needs
the purchase to execute in a market stage strictly before the first
land-dependent tile action.

`land_unlock_jit.py` decodes that boundary from the exact authored route bank:

1. replay represented worker positions and same-day HIRE spawns;
2. map each executable `BUY_LAND` to `NE`, `SW`, then `SE`;
3. locate the first represented land-dependent tile effect;
4. reject checkpoint crossings and same-day horizons without a safe target;
5. nominate only a literal **trailing empty** market slot inside the official
   `max(1, maxMarketOrdersPerTurn)` prefix; and
6. move exactly one existing `BUY_LAND` atomically, leaving all other rows and
   nonempty market entries byte-equivalent.

Movement is evidence, not the deadline. `PLACE` is land-dependent only for an
animal; shed `PLACE` remains legal from locked shed-access tiles.

## Two-stage gate

`audit_current_routes.py` is the first gate. It is pinned to the exact current
Git blobs for `frozen_selected.py`, `scheduler.py`, `mechanics.py`, and the
retained Arlene controller. It writes a deterministic census of every purchase,
first effect, checkpoint crossing, intervening market order, and source-level
relocation.

A source-level relocation is **not** yet a runtime or strength claim. A later
adapter may consume one only after proving from the live observed cash and exact
fixed-cost prefix that:

- the original purchase would execute;
- the delayed purchase still executes before the first target-quadrant effect;
- every baseline-completed intervening fixed purchase remains completed;
- current route, unlocked-quadrant count, selected source slot, and reserved
  target slot match the certificate; and
- both no-op controls return the original selected object unchanged.

If the exact current bank has no relocation, T02 is rejected before games. If it
does, candidate-action activation and a complete mirrored
opponent × seed × seat panel are still required before any promotion claim.

## Verification

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v3-t02-land-unlock-jit-sol-terrace
python -m unittest -v test_land_unlock_jit.py
python audit_current_routes.py --output CURRENT-CENSUS.json
```

The pure suite covers locked-tile movement, unit-before-market timing, HIRE spawn
positions, animal-versus-shed `PLACE`, active-prefix semantics, checkpoint and
day boundaries, trailing-slot preservation, exact two-slot mutation, source
drift rejection, multiple land purchases, deterministic serialization, and
malformed-input fail closure.
