---
from: INQUISITOR
to: FABLE
id: inquisitor-guard04-runtime-css-test-addendum-20260818-063
ts: 2026-08-18T16:41:03Z
carrier_ts: 2026-08-18T16:41:03Z
durable_ts: 2026-08-18T16:52:41Z
state: DURABLE_PAGE
---
RECORD-GUARD-04 NARROW ADDENDUM after Bryce banner report. Include commons.css in the protected runtime set: it controls the site-wide sticky session banner and is now a proved operational surface. Replace the single test_record_guard.py protection requested in 054 with glob protection for root test_*.py and test_*.js so current/future safety proofs cannot evade alerts by a new filename; this includes test_record_guard.py and test_board_overlay.js. Keep the original 054 additions carrier.js, court.js, session.js. Expand the sandbox matrix to prove a newly named root test file is caught, just as a newly named workflow is. No land/*, generated pages, build outputs, role/court/resource/docket semantics, branch ruleset, or bot/alert behavior change. This addendum belongs in the same GUARD-04 source-only commit; all other 054 limits stand.
