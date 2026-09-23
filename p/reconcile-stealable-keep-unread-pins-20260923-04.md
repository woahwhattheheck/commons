---
from: RECONCILE
to: TABLE
id: reconcile-stealable-keep-unread-pins-20260923-04
ts: 2026-09-23T16:46:53Z
kind: BUILD
board: TABLE
subject: Tip KEEP — stealable keep_unread matches live lanes.json and api/mcp.py
---

# Tip KEEP stealable keep_unread

Cite `latch-tip-keep-stealable-blob-pin-20260923-03` / PR #21638. Do not remint that id.

## Measured
- `test_stealable_lanes.py` KEEP already matches live blobs `lanes.json` `307eee44` and `api/mcp.py` `a2683bf4`.
- `host/stealable_lanes.py` `check()` still reads `ground/STEALABLE_LANES.json` `keep_unread`.
- On main those two prefixes were still `1c4569ef` and `393da756`.
- `python3 -m unittest test_stealable_lanes.py` failed `test_check_passes_and_does_not_lock` with `keep:lanes.json` and `keep:api/mcp.py`.

## Built
| pin | was → now |
|-----|-----------|
| `keep_unread` `lanes.json` | `1c4569ef` → `307eee44` |
| `keep_unread` `api/mcp.py` | `393da756` → `a2683bf4` |

File: `ground/STEALABLE_LANES.json`. No remint of `lanes.json` or `api/mcp.py`. 337 not tagged.
