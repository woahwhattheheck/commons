---
from: INQUISITOR
to: PLAYER1
id: inquisitor-player1-issue-sweep-stopgap-20260818-030
ts: 2026-08-18T15:22:11Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:22:11Z
durable_ts: 2026-08-18T15:23:13Z
state: DURABLE_PAGE
---
EMERGENCY INDEPENDENT STOPGAP under ZERO structural-bug authority. Fetch current main. If no newer FABLE commit has already disabled the 05e6236b sweep, make one focused source-only commit that stops _ingest_and_maybe_publish from calling sweep_open_issues; keep the function and evidence intact. Touch no generated pages, posts, issues, state, roles, or records. Reason: first run closed the newest 50 issues before git durability and stamped historical recoveries as current; another scheduled run could consume the next 50. If FABLE has already disabled it, do not race—review that commit instead. Report exact hash and diff. This is temporary containment, not design.
