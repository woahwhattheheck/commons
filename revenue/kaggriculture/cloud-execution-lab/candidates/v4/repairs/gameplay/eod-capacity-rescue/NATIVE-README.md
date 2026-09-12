# Native EOD capacity proof and shadow gate

Status: **component verified; zero natural engagement on the declared panel;
NOT wired into production; default OFF.** This extends the existing
`r04_eod_capacity_rescue.py` donor in this same package. The exact donor,
historical apply, original tests and custody manifest are unchanged.

## What is new

`native_eod_capacity_rescue.py` reuses current `scheduler.post_units` rather
than legacy H3c/router imports or a potentially stale selected-action snapshot.
It preserves the single-product theorem: with post-unit shed total S <= 100,
carried product quantity T, overflow O = S + T - 100 > 0 and at least O of
that product already in the shed, append SELL O after the original shed-neutral
market prefix. EOD backfills the sold product. Own post-EOD private shed and
cargo state match the unmodified path; only otherwise-discarded units are sold.

This permits actual HARVEST and COLLECT_FERTILIZER output, subtracts actual
FEED/FERTILIZE consumption, accounts for partial PLACE, and refuses to rescue
cargo already discarded by DROP. It projects the complete raw unit list:
omitted actors still carry inventory, and nonexistent extra actors still count
in the official interpreter's atomic PLANT-demand check. Inventories bind to
actual public actors, not the number of emitted commands.

No new config key, controller, archive, production caller, or legacy
materializer was introduced. An eventual gated caller would belong after final
capital/pressure selection but **before finalizer/history receipts**, not in a
post-return wrapper. That caller is deliberately absent: the natural gate did
not justify activation.

## Executed gates

Exact current b567 archive (429,604 bytes), entrypoint 4a8cf7, runtime b952,
scheduler a483, mechanics 044a, official engine 3c202. All detailed identities
are in `NATIVE-RECEIPT.json` and the executable tests.

* 19/19 tests normal and 19/19 optimized; 411 candidate checks and 256 full
  official-interpreter differential pairs per mode. Nine products, both seats,
  shed/cargo boundaries, same-tile actor order, stock-neutral purchase prefixes,
  omitted/extra actors, terminal boundary, floor quotes, and rival order streams.
* Seven deliberately broken local variants rejected in both modes. The mixed-
  cargo fixture funds both possible products so random set order cannot hide a
  missing single-product guard. No original donor was modified for this check.
* Unmodified literal `main.py::agent` versus the official deterministic starter,
  seeds 9120701 and 9120702, both seats: 4/4 full games, 2,876 callbacks per mode,
  116 usable EOD callbacks, **zero activations**, all parent callbacks completed.
  Normal/optimized action+diagnostic hashes match for all four games. EOD skips:
  55 not-single-product, 49 existing stock-changing/unknown market prefix, 12
  no-overflow. The remaining 2,760 callbacks are not usable EOD boundaries.

A direct mature-WHEAT fixture recovers 5 or 6 units depending on WATER/HARVEST
order; fertilizer collection recovers 1. These are synthetic local witnesses,
not observed field profit. Private-state equality is NOT a public-market or
whole-game competitive-EV theorem: extra supply can affect rival quotes. The
starter panel is not opponent-diverse field validation. Zero here parks this
candidate for that panel, not for every possible opponent or state.

## Reproduce without network or legacy materialization

Set `TITAN_RUNTIME_ROOT` to the exact unpacked b567 canonical archive. From
this existing repair directory run each command with `python` and `python -O`:

```sh
python test_native_eod_capacity_rescue.py
python check_native_mutants.py
python census_native_eod.py --seeds 9120701 9120702 --seats 0 1 --output CENSUS.json
```

The gate verifies dependency Git blobs before import and the existing offline
loader verifies all official engine files. The census calls the literal
entrypoint and evaluates the candidate only in shadow; it never feeds changed
actions into the trajectory. It writes the declared plan before running and
full EOD action/state rows to the selected output. This is reproducible local
execution, not proof of an externally preregistered or hosted run. Detailed
raw output hashes and compact per-game rows are retained in the receipt.
