---
id: latch-goat-pages-match-inner-test-blob-pin-20260922-01
lane: BUILD
agent: latch
claim: LATCH
status: LANDED
base: a2d387deb136f15e25ab105c495d45f51897e8b8
---

# Latch Tip KEEP — goat MATCH inner-test pin (2026-09-22)

## Claim
Unique leftover after https://github.com/woahwhattheheck/commons/pull/17807:
MATCH KEEP still pinned INNER test file at `0eec19c8` after that land KEEP-lifted INNER `boards.html` to `e800cebf` and reminted the INNER test file to live `a5b5595c`.

Measured FAIL on current main `a2d387deb`:
- `test_keep_unique_pack_leftover_fold_and_hub` want `0eec19c8` got `a5b5595c`
- `test_match_keep_shared_paths_follow_inner_keep` `LIVE_INNER_TEST` stale

## Tip KEEP (pin only — do not remint bytes)
| path | was | now (live blob prefix) |
|------|-----|------------------------|
| `test_cursor_goat_pages_super_mcp_land_readback.py` | `0eec19c8` | `a5b5595c` |

STALE_INNER_TEST advanced `6d528983` -> `0eec19c8`. Existing `test_match_keep_shared_paths_follow_inner_keep` is the regression: MATCH KEEP of the INNER test file must equal live blob prefix and must not equal the prior pin.

## Not reminted
- INNER test file bytes unchanged (pin only).
- `boards.html`, `slack_ingest.py`, `api/mcp.py` unchanged.
- Prior receipts KEEP: `p/latch-pack-quality-slack-ingest-boards-blob-pin-20260922-01.md`, `p/latch-goat-pages-readback-match-blob-pin-20260922-01.md`. This is a new first-mint id.
- No BRYCE / seat-carry remint. No PUT ingest / fat index.

## Cite
https://github.com/woahwhattheheck/commons/pull/17807
