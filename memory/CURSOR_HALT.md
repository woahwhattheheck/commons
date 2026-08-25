# Memory — stop giving Cursor work until further notice

Owner 2026-08-25 Slack `1787670330.096089`:
until future notice, stop giving Cursor work. Cursor is at
93% usage.

This upgrades the landed 24-hour grok-app-route leftover.
Do not remint `GROK_APP_ROUTE`. Close is BRYCE / ZERO only.

`ground/CURSOR_QUOTA_HOLD.md` now extends this from assignment policy to
mechanical containment: the Cursor doorbell, delivery, callbacks, and model
invocation are held too. No auth. No gate. Blank `from=` still lands as
`UNSEATED`.

Instrument: `host/cursor_halt.py`. Card: `ground/CURSOR_HALT.md`.
