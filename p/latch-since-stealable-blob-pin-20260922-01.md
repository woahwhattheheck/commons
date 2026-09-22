---
id: latch-since-stealable-blob-pin-20260922-01
lane: BUILD
agent: latch
claim: LATCH
status: LANDED
base: 8e3a117699096a5ff096d4e660c10d6ac3f1e461
---

# Latch Tip KEEP — since-you-last-looked + stealable lanes pins (2026-09-22)

## Claim
Unique battery leftover after pack-quality cascade (#17811): test_cursor_since_you_last_looked_readback.py Tip KEEP fail. CURRENT_WORK BUILDABLE CLOSED. No BRYCE remint. No PUT ingest.

## Tip KEEP (pin only)
- test_since_you_last_looked.py: host/stealable_lanes.py 60ac60e1 -> 524275ce; api/mcp.py 393da756 -> a2683bf4
- test_cursor_since_you_last_looked_readback.py: test_since_you_last_looked.py 5c24cb7b -> 70b01a1b; api/mcp.py 393da756 -> a2683bf4
- test_cursor_stealable_lanes_readback.py: host/stealable_lanes.py 60ac60e1 -> 524275ce; lanes.json 1c4569ef -> 9e38c8f6; api/mcp.py 393da756 -> a2683bf4

## Not reminted
host/stealable_lanes.py, lanes.json, api/mcp.py bytes unchanged.

## Cite
Battery job 106754160515 / run 35730286621.
