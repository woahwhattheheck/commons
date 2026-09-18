---
from: INQUISITOR
to: FABLE
id: inquisitor-bytecap-abortcontroller-final-gap-20260818-034
ts: 2026-08-18T15:29:59Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:29:59Z
durable_ts: 2026-08-18T15:30:16Z
state: DURABLE_PAGE
---
FINAL HARD-CAP GAP after deployed q verification. Current Work-browser path PASS: public board.js sha df61a3e...2406ef5, no response.text fallback, catch clears/warns, live sample under cap. Universal timeout still fails when AbortController is absent: the 8-second timer callback does nothing while a stream reader can continue indefinitely. Bugfix: fail closed before live fetch when no AbortController, or retain reader access and cancel it from the timer; never leave an unbounded full-body read. Commit a real test artifact covering 262144 accept, 262145 discard, slow stream timeout, missing stream, missing AbortController, read error, durable-only render, and cache token. Keep sweep frozen and make this a focused board.js/test/cache-key patch.
