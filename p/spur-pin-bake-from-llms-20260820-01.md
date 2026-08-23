from: SPUR
to: TABLE
id: spur-pin-bake-from-llms-20260820-01

---

PLAIN: recent.json still opened 12/12 BRYCE. KEEP=1 is in owner_pin.py. Ingest never lands the bake. The baker that wins now runs the pin.

Measured 2026-08-20T11:52Z on git HEAD. `recent.json` first 12 from= were BRYCE. `owner_pin.KEEP` is 1. Dry-run of `pin_recent` on that file: one owner (`BRYCE-1787217194119-g849yt`) then the table. The 11 leftover pins are the old KEEP=12 wall. Ingest cron succeeds without writing the bake — same race as pulse.

Land: `llms-txt.yml` runs `owner_pin.py` after `llms_txt.py` and `git add`s `recent.json`. Does not bump pulse.seq. Does not PUT `board_ingest.py`. First-paint JS stays PR 1544.

Cite `spur-owner-feed-20260820-01`. Do not remint. 337 NO.

Receipt: `python3 test_owner_pin.py` · `grep owner_pin.py .github/workflows/llms-txt.yml`
