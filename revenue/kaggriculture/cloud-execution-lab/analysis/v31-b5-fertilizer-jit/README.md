# TITAN V3.1 B5 — JIT fertilizer audit

Operation: `TITAN-V31-B5-JIT-FERTILIZER-REFRESH-20260911-01`

This packet is an **analysis carrier only** on frozen V3.1 base
`508b342fc46fa91e3d7cdc3f0b7e44934a187c14`. It does not edit an overlay,
`TITAN-CONFIG.json`, a package builder, the frozen gate panel, an evaluator,
or any submission/provider state.

## Why the original “daily fertilizer sweep” premise is too broad

The pinned official engine (`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`) makes
`FERTILIZE` consume one carried fertilizer and set
`fertilized_until_day = max(old, day + 2)`: three days of inclusive coverage.
Repeated daily fertilization can therefore spend an action/input merely to roll
forward already-live coverage.

The marginal crop benefit is also event-bound, not continuous:

- annual crops receive one extra unit when a qualifying WATER occurs while
  fertilized, capped by remaining crop yield room;
- ongoing crops receive one extra unit at a scheduled production refresh only
  when that day was WATERed and fertilizer coverage is live.

Older exact-engine retained-service evidence separately found that deleting an
authored late `FERTILIZE` was always worse in its tested bank. B5 therefore starts
from **preserve incumbent fertilizer; look for uncovered valuable refreshes**,
not blanket deletion or blanket daily insertion.

## What this carrier measures

`audit_b5_fertilizer.py` decodes the exact committed V3/R04 `r01_tapes.py` and
emits a deterministic JSON receipt containing, per route/day/worker:

- authored `FERTILIZE`, `WATER`, `COLLECT_FERTILIZER`, and literal `PASS` counts;
- fertilizer BUY/SELL market rows in the executable first-ten prefix;
- exact fertilizer-service event steps;
- literal idle streaks of at least six authored PASS rows, matching the bounded
  round-trip size used by the older idle-fertilizer salvage mechanism;
- source SHA-256 plus a deterministic route-census digest.

Run from this directory:

```bash
python -B test_audit_b5_fertilizer.py
python -B audit_b5_fertilizer.py --summary-only
python -B audit_b5_fertilizer.py --output /tmp/b5-r04-census.json
```

## Truth boundary / next gate

This is a **static authored-tape census**. It does not prove that a worker exists,
an authored action is legal/effective, the action targets a given plant, a PASS
is economically free, or a proposed refresh increases game score.

A gameplay successor should not be written until the census is paired with exact
official-engine replay from a manifest-pinned `build_v3.py` materialization and
can identify a public-state crop whose next valuable WATER/production event lies
outside current fertilizer coverage. Any candidate should remain default OFF and
must preserve R04 market/L3, cattle-early, H4/H5 and terminal behavior until a
paired competitive panel is complete.
