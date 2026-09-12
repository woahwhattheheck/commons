# TITAN V5 bulk-feeder pocket routing

Default-off research carrier for the canonical V5 route tape. This consumes the
`V5-FEEDER-CARRY-ROUTE-CENSUS` evidence demand; it is not feeder-policy authority.

## Source theorem

The pinned Kaggriculture mechanics currently authenticated by this carrier make
three facts explicit:

- shed-adjacent `PICKUP <item> <n>` accepts an integer quantity and clips only to
  observed shed availability;
- per-farmer `private["inventories"]` has no carrying-capacity check;
- `FEED` consumes exactly one carried `WHEAT`.

That creates a real route frontier when one worker repeatedly returns to the
shed for one-unit WHEAT pickups before later FEED actions.

## What this carrier does

`bulk_feeder.py` scans the canonical Arlene route branches for same-day repeated
WHEAT pickup/FEED windows. It can consolidate every pickup in one window into
the first pickup and replace only the later pickup actions with `PASS`.

The scan is intentionally only a proposal. A candidate is materialized only
after `verify_unit_window()` binds an exact observed `(player, step)`, replays
**all actors** from that observed state with the pinned deterministic unit
mechanics, and proves exact final `farm` and `private` equality. This catches
shared-shed timing conflicts such as another worker depositing WHEAT after the
first pickup. Witness-reported gains are recomputed and movement savings are
hard-pinned to zero.

Market-bearing windows and day boundaries are rejected. Movement is not changed
by this first carrier, so its travel-savings lower bound is deliberately `0`;
the proved gain is reclaimed pickup turns. Those free turns and the reported
return loops are the safe substrate for a later path compactor only after that
movement rewrite gets its own exact-state proof and evaluation evidence.

## Usage

```bash
python candidates/v5/bulk-feeder-pocket/bulk_feeder.py
python candidates/v5/bulk-feeder-pocket/bulk_feeder.py --route-json route.json
python -m unittest candidates/v5/bulk-feeder-pocket/test_bulk_feeder.py
```

The CLI emits deterministic JSON under
`titan-v5-bulk-feeder-pocket-audit/v1`.

## Non-goals

This package does not edit `spatial_tempo.py`, root runtime code, defaults,
configuration, the canonical archive, or Kaggle activation. It does not claim
that a static opportunity is safe without an observed equality witness, and it
does not claim travel savings until movement itself is separately proved.
