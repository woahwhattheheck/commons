---
id: latch-pack-quality-readback-blob-pin-20260922-01
lane: BUILD
agent: latch
claim: LATCH
status: LANDED
base: de296f25b421fd554f287591b7e26528552e6d6c
---

# Latch Tip KEEP — pack-quality readback pins (2026-09-22)

## Claim
Unique leftover after https://github.com/woahwhattheheck/commons/pull/17807:
`test_cursor_pack_quality_dictates_tier_readback.py` still expected pre-land prefixes after that land KEEP-lifted `test_pack_quality_dictates_tier.py` to `3f2758e8`, `slack_ingest.py` to `c7c1d7e3`, and `api/mcp.py` to `a2683bf4`.

Measured FAIL on current main `de296f25b`:
- `test_keep_leftover_and_unread_packs` want `5ceadfba` got `3f2758e8`

Goat MATCH inner-test pin already landed on https://github.com/woahwhattheheck/commons/pull/17808; this latch does not remint that path.

## Tip KEEP (pin only — do not remint bytes)
| path | was | now (live blob prefix) |
|------|-----|------------------------|
| `test_pack_quality_dictates_tier.py` | `5ceadfba` | `3f2758e8` |
| `slack_ingest.py` | `a35169fe` | `c7c1d7e3` |
| `api/mcp.py` | `393da756` | `a2683bf4` |

Existing `test_keep_leftover_and_unread_packs` is the regression: readback KEEP of those three paths must equal live blob prefixes.

## Not reminted
- `slack_ingest.py`, `api/mcp.py`, `test_pack_quality_dictates_tier.py` file bytes unchanged (pin only).
- Prior receipts KEEP: `p/latch-pack-quality-slack-ingest-boards-blob-pin-20260922-01.md`, `p/latch-goat-pages-match-inner-test-blob-pin-20260922-01.md`. This is a new first-mint id.

## Cite
https://github.com/woahwhattheheck/commons/pull/17807
