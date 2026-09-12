# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed observation/private/market custody fails closed for MELON while
non-MELON proposals pass through.

## Executable proposal custody

Canonical `fourth_quadrant.proposals()` stores proposal-owned executable custody
in both `proposal['variants'][route]['patches']` and the companion `bundle`.
`bundle.lots[*]` records the exact selected tile, plant step and 1-based worker;
`bundle.land.{step,slot}` records the insertion point immediately after inherited
market rows. The producer appends `BUY_LAND`, `BUY_SEED <crop> <qty>`, then HIREs
at that point. `FourthQuadrant.install()` applies the patch rows directly.

Outer `tiles`, optional `size`, and `seed_units` are therefore cross-checks, not
a safe authority for partial reconstruction. `filter_proposals()` treats every
MELON proposal as atomic and requires every route variant to prove all of:

- unique outer coordinate tiles and exact `seed_units` cardinality;
- exactly one bundle lot per selected tile;
- every lot's `plant_step` + positive 1-based `worker` points to literal
  `PLANT MELON` in that route's executable patch;
- no two lots reuse the same `(plant_step, worker)` executable slot;
- the lot tile set exactly equals the outer tile set;
- `bundle.land.step/slot` points to literal `BUY_LAND` followed immediately by
  literal positive-int `BUY_SEED MELON N`, where `N` equals the same commitment;
- optional `size`, when present, also equals the commitment.

Using `bundle.land.slot` is deliberate: blindly summing every BUY_SEED in copied
patch rows could count inherited route economics as proposal spending. The bundle
position identifies the producer-owned order.

An admitted MELON proposal remains the **original object unchanged**. Malformed
or oversized proposals are dropped, never shallow-shrunk or rewritten.
FourthQuadrant alternatives are mutually exclusive: its admission callback must
return exactly one supplied proposal or `None`, so safe candidate alternatives do
**not** consume one another's budget merely by appearing earlier in the list.

`MELON_LIFETIME_UNIT_CAP = 28` is deliberately conservative and is not claimed
to equal the exact number of full-season town-center consumption ticks.

## Reproduce focused validation

```sh
python -B -m unittest -q test_melon_cap.py
python -O -B -m unittest -q test_melon_cap.py
python -m py_compile melon_cap.py test_melon_cap.py check_fourth_quadrant_contract.py
```

The producer/consumer harness additionally requires an extracted canonical
package containing `fourth_quadrant.py` with Git blob
`57ffe172a5a5ebf5b57132319731aa367b9dc7f5`:

```sh
python check_fourth_quadrant_contract.py --package /path/to/package
python -O check_fourth_quadrant_contract.py --package /path/to/package
```

The harness uses the real producer to obtain five- and four-plant MELON
alternatives, authenticates exact lot→patch PLANT custody and producer-owned
BUY_SEED quantity, mutates BUY_SEED 4→5 as a fail-closed predecessor, proves the
five-plant proposal is rejected without mutation, proves the original four-plant
proposal survives by object identity, and passes that choice through real
`FourthQuadrant.install()`.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
proposal seam. OFF identity, current-native engagement, economics, and whole-v4
graph composition remain separate gates before activation.
