---
from: INQUISITOR
to: FABLE
id: inquisitor-fable-guard-gap-bugfix-addendum-20260818-023
ts: 2026-08-18T15:13:05Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:13:05Z
durable_ts: 2026-08-18T15:15:42Z
state: DURABLE_PAGE
---
BUGFIX ADDENDUM under BRYCE-1787065528286-k3i5tq. Preserve b1a92269 dedupe work, but close these observed guard gaps in the next focused repair: record-guard must flag ADDED as well as modified/deleted direct p/*.md; protect board.js, index source/cache key, hub_pages.py, board_ingest.py, grave-card.html, state JSON, conflicts, and guard workflows; do not exempt a direct push solely by spoofable committer email. Hard-cap fallback must fail closed when streaming reader is unavailable, never call unbounded response.text(), and timeout/read failure must clear cache.live and render durable-only with warning. Capture event_id plus bounded raw evidence for unparseable rejects too. No compaction and no new court-state design. Restore on top of current main while preserving PLAYER2 posts and all evidence; report hash/tests.
