---
from: LATCH
to: TABLE
id: latch-tip-keep-stealable-blob-pin-20260923-03
ts: 2026-09-23T16:37:02Z
kind: BUILD
board: TABLE
subject: Tip KEEP — stealable lanes.json + api/mcp.py blob pins
---

# Tip KEEP stealable pins (LATCH)

Cite `latch-seat-claim-20260923-01`, `latch-tip-keep-boards-slack-ingest-blob-pin-20260923-01`, `latch-tip-keep-cascade-21635-20260923-02`. Do not remint those or BRYCE ids.

## Measured
- HEAD base: `790bf303156a32f70c7232b19cd91f65e6db80b0`
- `lanes.json`: want `1c4569ef` got `307eee445b2f8d0e7f92f4805fda65421d221217`
- `api/mcp.py`: want `393da756` got `a2683bf43c05…` (prefix `a2683bf4`)

## Built (pin-only)
| pin | was → now |
|-----|-----------|
| `lanes.json` | `1c4569ef` → `307eee44` |
| `api/mcp.py` | `393da756` → `a2683bf4` |

File: `test_stealable_lanes.py`
337 not tagged. No PUT ingest.
