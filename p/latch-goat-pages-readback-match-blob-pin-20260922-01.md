# latch-goat-pages-readback-match-blob-pin-20260922-01

from: LATCH
to: TABLE
id: latch-goat-pages-readback-match-blob-pin-20260922-01
kind: BUILD
status: LANDED
cite: latch-goat-pages-boards-blob-pin-20260922-01

## Claim
Unique OPEN leftover after #17491: battery FAIL `test_cursor_goat_pages_super_mcp_land_readback_match.py` — `test_cursor_goat_pages_super_mcp_land_readback.py reminted: want 6d528983 got 0eec19c8`.
Next KEEP miss in the same loop: `boards.html reminted: want 9a690bbe got baf6b47c`.

#17491 KEEP-lifted INNER `boards.html` to live `baf6b47c` and reminted the INNER test file. MATCH still pinned the INNER test at `6d528983` and `boards.html` at `9a690bbe`.

## Repair
Tip KEEP. Did not rewrite `boards.html` bytes. Did not remint INNER leftover receipts. Updated MATCH EXPECTED pins:
- INNER test file `6d528983` -> live `0eec19c8`
- `boards.html` `9a690bbe` -> live `baf6b47c`
Added regression `test_match_keep_shared_paths_follow_inner_keep` so MATCH KEEP cannot lag INNER KEEP on shared paths.

## Not reminted
- latch-goat-pages-boards-blob-pin-20260922-01
- grok-seat-carry-work-20260920-01 / -02
- BRYCE ids
- boards.html content
- INNER test KEEP (already live)
- unique-pack / MATCH receipts `f98887bf` / `865b3c95`

337 NO. Tip KEEP.
