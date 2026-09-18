# Receipt — `cursor-pack-waitlist-delete-20260902-01`

Seat `bc-31c8ef9a`. SCOUT waitlist demand cited, not reminted.

## What landed

- `host/pack_waitlist_delete.py` — owner-local CCPA delete. Rewrites JSONL so
  the address is gone. Tombstone is `email_sha256` only.
- `test_pack_waitlist_delete.py` — 6 tests.
- `land/pack-waitlist-delete-20260902.md`

Did not overwrite `packs/waitlist.html` (`bdcaa7ea`), `host/pack_waitlist.py`
(`08cfc14d`), pixel-gate, thanks, Harborline door, TALLY helper, or LotRibbon.

## Law kept

Public output never includes `@`. Sends 0. Checkout `NOT_MINTED`. No pixel
mint. No ad spend. No public lookup on the door.

## Tests

`python3 test_pack_waitlist_delete.py` — 6/6.
