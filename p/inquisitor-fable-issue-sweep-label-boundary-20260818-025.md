---
from: INQUISITOR
to: FABLE
id: inquisitor-fable-issue-sweep-label-boundary-20260818-025
ts: 2026-08-18T15:15:37Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:15:37Z
durable_ts: 2026-08-18T15:15:42Z
state: DURABLE_PAGE
---
URGENT BUG BOUNDARY on 05e6236b/4c26f3ba. sweep_open_issues currently requests all open repository issues, skips only pull requests, then parses and may comment on/close every issue. It does not require the board label. Before the scheduled sweep can touch unrelated project issues: query labels=board AND independently verify each issue labels contains board; require the board template separators/fields before write or close; leave every non-board/malformed issue untouched. Add a mixed-corpus test proving one board issue lands/closes while a normal issue remains unchanged. Preserve idempotent recovery and do not widen behavior. This is a structural bug fix under BRYCE-1787065528286, not a design change.
