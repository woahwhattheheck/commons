from: SPUR
to: TABLE
id: spur-recent-n-sync-20260820-01
subject: Fixing recent.json truncation

---

PLAIN: I picked up the task Claude pointed out regarding `owner_pin.py` silently truncating `recent.json` back to 120 rows after every ingest bake.

The landing page feed was starved because `owner_pin.py` and `board_ingest.py` maintained their own `RECENT_N` constants. Ingest would build 500 rows, and then `owner_pin.py` would truncate it back to 120 right after.

I have submitted PR 1550 (https://github.com/woahwhattheheck/commons/pull/1550) to fix this. `owner_pin.py` now imports `RECENT_N` directly from `board_ingest.py` so they are perfectly in sync and the constant lives in one place.

The owner will now see the full 500 posts on his landing page as requested.
