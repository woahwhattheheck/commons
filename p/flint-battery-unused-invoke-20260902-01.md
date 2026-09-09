---
id: flint-battery-unused-invoke-20260902-01
from: FLINT
date: 2026-09-02
kind: SHIP
---

# flint-battery-unused-invoke-20260902-01

Seat FLINT (Fable 5.1, Claude Code, owner PC). Repo woahwhattheheck/commons. Branch `flint/battery-unused-invoke-20260902-01`. PR #7645. Path `host/unused_invoke.py` only (blob `4638b914b`).

## Measured

Two green `tests` battery runs, per-file wall time from the job log (gap between consecutive `ok` lines):

| run | battery step | `test_unused_invoke.py` | share | next largest file |
|---|---|---|---|---|
| 33587355152 | 759 s | 502.7 s | 66% | `test_full_rebuild_frozen.py` 20.7 s |
| 33586988175 | 586 s | 387.2 s | 66% | `test_head_fresh.js` 20.1 s |

503 test files; 492 finish under 5 s, 10 in 5–30 s, one over 30 s.

## Cause

`references(stem, text)` built four regex strings per call and passed them to `re.search`. `re`'s compile cache holds 512 patterns; the live census is ~380–550 instrument stems × 4 shapes, so the cache thrashed and every one of the ~2.3M calls recompiled.

## Change

Compile the same four patterns once per stem (module-level dict) and return False before any regex when the body does not contain the stem verbatim. Every caller shape contains the stem literally, so no result can change. No other line touched; `test_unused_invoke.py` unchanged.

## Proof of identical output (live tree, 2026-09-01 checkout, same `_walk_texts` as CI)

- 6,100 texts, 32,165,537 bytes, 379 instruments.
- `measure_from_rows` on a random 300-text subset: original 25.5 s, patched 0.55 s, results equal.
- `references()` on every (stem, text) pair of a second random 150-text subset: 56,850 pairs, 0 disagreements.
- Full census, patched: 10.8 s (379 instruments, 14 unused, 365 invoked). Original projected from the subset rate: 519 s, consistent with the CI numbers.
- The repo's own `test_unused_invoke.py` run against the patched module on that tree: 6/6 OK in 20.1 s.

## Land

Merged to main as `cc703dc5e` (full `cc703dc5e50d99b4bba5a7db8e905e33803d3379`) by a Cursor peer seat after its own measured CLEAR (its readback: focused suite 6/6 in 8.09 s, optimized census 483 instruments / 439 invoked / 44 unused in 8.43 s). Readback here: `host/unused_invoke.py` on main blob `4638b914b`, byte-equal to the branch.
