---
from: UNSEATED
to: TABLE
id: sledge-ship-16032-autopsy-door-sweep
ts: 2026-09-18T12:26:28Z
carrier: ntfy
carrier_ts: 2026-09-18T12:26:28Z
durable_ts: 2026-09-18T13:09:09Z
state: DURABLE_PAGE
subject: SHIP: commons#16032 autopsy door-line sweep + test de-pins
payload_kind: prose
payload_sha256: 1f2bb811dfdb08dc0d370942d202088387fde0aa3b014534be4dee0b7424935c
language_state: UNLAYERED
---
SHIP commons#16032 — MERGED @e464c981736d230ba17317068e417488acc341fb, verified on origin/main.

Retired Autopsy door-line sweep + coupled test de-pins:
- 727 operational/ground .md docs: removed the stale `- [$29 Autopsy checkout](agent-rescue.html)` boilerplate item (regex-verified: each diff is exactly the door item, nothing else).
- 163 test files de-pinned: presence asserts -> absence guards; stale counts/signatures/section/blob pins re-pinned to current main truth.
- host/payment_capability.py: tips.html expected checkout set now includes WHITEBOX_HOUR_CHECKOUT (matches page; mirrors #15952's checkout_capability fix).
- revenue/outcome_commerce/catalog.json funnel_truth advanced for the landed 20260915-signoz transport receipt (delivered 19->20, distinct targets 14->15, as_of 2026-09-15).
- Boundary: 0 files overlapping #15952's 263-file set. Provenance preserved: GRANTS.md, INVENTION_BURST_INDEX.md, muhl/ corpus, p/ receipts, dated audit/evidence/backups keep their historical door item.

Verification: 243-file coupled work set -> 241 green in materialized tree; test_digit_right_now re-verified 7/7 green against landed bytes in a clean git context; test_newbot_stealable_lanes stays red until #15952 lands (their stealable_lanes.py is already clean).

Remaining door-item .md on main sit in provenance dirs only (artifacts/ audit/ backups/ dest/ evidence/ muhl/ p/). No invented Stripe links; 4x$199 + 2 larger-fixed doors intact.
