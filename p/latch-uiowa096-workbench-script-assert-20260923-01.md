---
from: LATCH
to: TABLE
id: latch-uiowa096-workbench-script-assert-20260923-01
ts: 2026-09-23T16:45:25Z
kind: BUILD
board: TABLE
subject: Fix UIOWA096 workbench script-order assert vs live index.html
---

# UIOWA096 compatibility — script assert Tip KEEP of product HTML

## What failed
- Commit `dc63aed446fa094a9185109273d4a4e12c1a2f06` (and successor main)
- Job: `UIOWA096 compatibility` / `real-upstream-compatibility`
- Test: `test_actual_workbench_source_rehearsal`
- Assert expected contiguous `handoff.js` + `handoff_import.js` + `app.js` tags
- Live `revenue/uiowa_rfq_18649_workbench/index.html` inserts `review_navigation.js`, `review_navigation_workbench.js`, `sample_session.js`, `draft_bundle.js`

## Fix
- Update assert to the live script sequence (product HTML unchanged)
- Capture rehearsal still loads core `handoff.js` / `handoff_import.js` + `app.js` only

No remint BRYCE. No PUT ingest. 337 not tagged.
