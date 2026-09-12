# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed observation/private/market custody fails closed for MELON while
non-MELON proposals pass through.

## Executable proposal custody

Canonical `fourth_quadrant.proposals()` stores the executable plan in
`proposal['variants'][route]['patches']`, and `FourthQuadrant.install()` applies
those patch rows directly. Outer `tiles`, `size`, and `seed_units` are metadata;
they are not a safe authority for partial reconstruction.

`filter_proposals()` therefore treats every MELON proposal as atomic:

- count actual `PLANT MELON` actions in every route variant's executable patches;
- require every route variant to have the same positive cardinality;
- require `tiles`, optional `size`, and `seed_units` to agree with that executable
  cardinality;
- admit the **original proposal object unchanged** only when the whole executable
  commitment fits the remaining cap;
- reject malformed or oversized MELON proposals rather than trimming metadata or
  synthesizing patches.

FourthQuadrant alternatives are mutually exclusive: its admission callback must
return exactly one supplied proposal or `None`. Safe candidate alternatives
therefore do **not** consume one another's budget merely by appearing earlier in
the proposal list. This preserves valuation choice while the selected plan remains
bounded by the same real-world committed-production reserve.

`MELON_LIFETIME_UNIT_CAP = 28` is deliberately conservative and is not claimed
to equal the exact number of full-season town-center consumption ticks.

## Reproduce focused validation

The committed unit suite is dependency-free:

```sh
python -m unittest -v test_melon_cap.py
python -O -m unittest -v test_melon_cap.py
python -m py_compile melon_cap.py test_melon_cap.py check_fourth_quadrant_contract.py
```

The producer/consumer harness additionally requires an extracted canonical
package containing `fourth_quadrant.py` with Git blob
`57ffe172a5a5ebf5b57132319731aa367b9dc7f5`:

```sh
python check_fourth_quadrant_contract.py --package /path/to/package
python -O check_fourth_quadrant_contract.py --package /path/to/package
```

That harness uses the real producer to obtain five- and four-plant MELON
alternatives, proves the five-plant proposal is rejected without mutation, proves
the original four-plant proposal survives by object identity, and passes that
filtered choice through real `FourthQuadrant.install()`.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
proposal seam. OFF identity, current-native engagement, economics, and whole-v4
graph composition remain separate gates before activation.
