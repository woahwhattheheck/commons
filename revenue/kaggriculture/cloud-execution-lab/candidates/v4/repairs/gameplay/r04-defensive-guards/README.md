# TITAN V4 lane: R04_DEFENSIVE_GUARDS — defensive last-mile guards

**Status:** landed source evidence, NOT runtime-promoted (composition state:
`blocked`). Ships default-OFF behind one master key; nothing in the production
package changes until the promotion wiring below is composed and gated.

## Verdict

- **PASS (neutral, as expected for defensive guards)**
- Tests: `checks/test_v3_r04_defensive_guards.py` — **30/30 pass in normal and
  `python -O` modes** (run in the wired payload carrier; landed files are
  byte-identical to the gated copies)
- Parent commit: `465f4263da1c98acf78889d67cdd21b61dbba145`
  (titan/v4-20260911 tip; docs-only delta over tree-v4base)
- Donor: `guard-donor-7a64dc3d.patch` (final, published; CARE guard excluded)

## Mechanism

Standalone, stdlib-only module (`r04_defensive_guards.py`) for the
`R04_DEFENSIVE_GUARDS` key. Three fail-closed guards applied after all lane
wrappers via `_apply_defensive_guards` (identity when nothing needs fixing):

1. `_sanitize_numeric_args` — clamps non-finite/out-of-range numeric args
   (engine `int()` on inf/nan kills the whole interpreter step).
2. `_guard_plant_overdemand` — caps per-crop PLANT at seeds held (engine drops
   ALL of a turn's PLANTs for a crop when total exceeds seeds).
3. `_guard_eod_autodrop` — on the last step of a day, prepends cheapest-first
   SELL rows for projected shed overflow so the EOD auto-drop destroys
   nothing.

Engine constants mirrored from `r04_full_router.py` (same values):
`TURNS_PER_DAY = 24`, `SHED_CAPACITY = 100`, `_SHED_CAPACITY = 100`.

## Promotion wiring (key-park pattern, for the runtime-promotion step)

In `r04_full_router.py` (see the wired payload carrier for exact hunks):

- `from r04_defensive_guards import ...` at top (keeps the `r04._guard_*`
  names the tests use); inline guard defs removed
- `R04_DEFENSIVE_GUARDS = False` global
- `v3_agent` seam applies `_apply_defensive_guards(observation, action)` after
  all lane wrappers iff the key is on
- `install(..., defensive_guards=None)` sets the global

In `titan_runtime.py`:

- `Features.r04_defensive_guards: bool = False`; `install` kwarg
  `defensive_guards=...`; `diagnostics['defensive_guards']`

In `TITAN-CONFIG.json`: `"r04_defensive_guards": false` (ships OFF).

## Files

- `r04_defensive_guards.py` — the lane module (byte-identical to the gated
  copy; guard bodies byte-identical to the donor patch)
- `checks/test_v3_r04_defensive_guards.py` — donor's 30 tests, unmodified
  (byte-identical to the donor patch's copy)
