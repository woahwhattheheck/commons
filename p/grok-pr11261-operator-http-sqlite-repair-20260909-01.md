# Repair PR #11261 Hive028 operator HTTP SQLite + dispatch

Operation: `grok-pr11261-operator-http-sqlite-repair-20260909-01`

Original composition already merged as Commons PR #11261 /
`d027c924ab86d2d0a3434e72c77c76ac634dcb2d` with head
`600910625c3412c9cf84e0fbc7c5afb74e07f255`. Landed HTTP tests failed because
`ThreadingHTTPServer` used the OutboundDesk SQLite connection on a different
thread than construction. The same head also added an `unknown action`
rejection that `open_door_guard.py` classifies as an unlisted-action lock.

This repair keeps the landed `desk.py` blob
`55ca1568f0ed4a5fe88acf536beb57311219eec3` unchanged. The adapter reopens that
connection with `check_same_thread=False` and a lock. Names without a bound
OutboundDesk method still reach dispatch as local `transport=NONE` receipts.

Regression: `test_operator.py` now covers concurrent `/state` workers and
`action=send` with no provider transport. No live sends, calendar/CRM mutation,
or force-push.
