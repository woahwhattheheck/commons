# TITAN V4 annual relay rotation (ASTRA-RELAYROTATE)

Research-only source package for the sole canonical `main:candidates/v4` line.  It does **not** author actions, add a feature key, edit production/runtime/defaults, or create a second controller.

## Source theorem

Official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

For one player's unit phase, the interpreter first computes the raw per-crop PLANT demand, then executes the main farmer followed by hands in actor order.  Each `_apply_unit_action` reads the tile at the instant that actor runs.  That makes this source-real relay possible when three already-existing actors are co-located on one mature annual crop:

1. earlier actor `HARVEST`s WHEAT/CARROT/MELON; annual HARVEST transfers the standing yield and replaces the tile with `None`;
2. later actor `PLANT`s an already-owned annual seed into that now-empty tile;
3. still-later actor `WATER`s the newly created plant during the same callback.

The new plant starts `consecutive_unwatered=1` because planting day counts as unwatered.  The later same-callback WATER sets `watered_today=True`, and end-of-day refresh resets the streak to zero instead of converting the plant to WEED.  The reversed `HARVEST -> WATER -> PLANT` order does not work: WATER sees an empty tile, the new plant reaches EOD unwatered, and its streak becomes two.

This is stronger than the older next-callback V2.5 crop-release theorem: with three correctly ordered co-located actors, there is no callback gap between annual harvest, replacement planting, and required planting-day water.

## Hard boundaries

- Seed must already be physically present before the unit phase.  A same-callback market `BUY_SEED` is too late because unit actions execute before market actions.
- The interpreter's atomic raw PLANT prefilter still applies.  If raw PLANT demand for the replacement crop exceeds pre-unit seed stock, every raw PLANT row for that crop is blocked before actor execution.
- Only non-ongoing WHEAT/CARROT/MELON are certified.  TOMATO/STRAWBERRY lifecycle remains HYDRA/ongoing-crop territory.
- The certifier is read-only and requires exact actor/action cardinality, in-bounds public positions, mature positive-yield source crop, strict integer seed counts, and no same-tile mutator between relay stages.
- W1/H1 retain dead/terminal WATER->HARVEST custody.  SEEDGHOST retains ghost-row atomic admission custody.  This package does not compose or replace them.
- Physical reachability, whether current native routes naturally co-locate three actors at a useful annual harvest boundary, extra hire/travel cost, seed funding, shed capacity, downstream SELL timing, and competitive EV are **not assessed** here.

## Files

- `annual_relay_rotation.py` — read-only admission/certificate logic for an already-authored relay.
- `test_annual_relay_rotation.py` — focused fail-closed regression suite.
- `engine_witness.py` — repository-checkout executable that refuses engine blob drift, then applies exact official `_apply_unit_action` / `_daily_refresh_plants` functions over all 3x3 annual old->new crop pairs plus the reversed-order kill control.
- `RECEIPT.json` — exact authored hashes and local validation scope.

## Validation executed before publication

Python 3.13.5 authoring container:

```text
python -B -m unittest -v test_annual_relay_rotation.py      14/14 PASS
python -O -B -m unittest -v test_annual_relay_rotation.py   14/14 PASS
python -m py_compile annual_relay_rotation.py test_annual_relay_rotation.py engine_witness.py  PASS
```

The local authoring container did not have a Commons checkout, so `engine_witness.py` was compiled but not falsely reported as locally executed.  Its first operation in-repo is an exact `git hash-object` refusal unless the official engine is still blob `3c202c7e...`.

## Next gate

Consume this certificate in the existing single V4 scheduler/native-assembler path.  First run a current-native census for naturally reachable annual harvest boundaries with >=3 co-located actors and pre-owned seed.  If natural reachability is nonzero, evaluate a default-OFF candidate that preserves raw-slot/seed/funding constraints and compare both seats with realized HARVEST/PLANT/WATER, shed, sale, own cash, rival cash and margin receipts.  Zero natural opportunity is a routing result, not permission to invent a second controller.
