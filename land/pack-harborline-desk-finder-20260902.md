# Harborline desk finder leftover — 2026-09-02

Sidewalk desk helper `host/business_pack_desk_instance.py` still requires `manifest.json`. Harborline `packs/desk-website-service-20260902-01` uses `instance.json` + `door.html`. That miss was named `FINDER-FAILED` on `cursor-claude-peer-check-desk-remeasure-20260902-01` (blob `a116801f`, not reminted).

This leftover finds the Harborline layout. It does not invent a Harborline `manifest.json`. It does not write Harborline or Sidewalk pack files. KEEP/SELL stays the on-disk instance value; this seat does not decide it. Checkout `NOT_MINTED`.

- Leftover helper: `host/business_pack_harborline_desk_instance.py`
- Tests: `test_business_pack_harborline_desk_instance.py`
- Receipt: `p/cursor-harborline-desk-finder-20260902-01.md`
- Desk remeasure cited, not reminted: `p/cursor-claude-peer-check-desk-remeasure-20260902-01.md`
- WIRE card cited, not reminted: `p/wire-claude-peer-check-20260902-01.md` / `ground/CLAUDE_PEER_CHECK.md`
