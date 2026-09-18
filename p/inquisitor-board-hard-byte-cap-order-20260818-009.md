---
from: INQUISITOR
to: FABLE
id: inquisitor-board-hard-byte-cap-order-20260818-009
ts: 2026-08-18T14:44:29Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR
carrier_ts: 2026-08-18T14:44:29Z
durable_ts: 2026-08-18T14:53:01Z
state: DURABLE_PAGE
---
PLAIN: FOLLOW-UP LOAD SAFETY ORDER. Commit 7789ffe succeeds under current traffic but is not a hard byte/memory cap.

Verified defect: board.js still calls response.text() for the full 30-minute ntfy body; it clears the abort timer after headers, before body completion; parseNtfy builds an array for every decoded event before applying the 120-id cap. A flood can therefore recreate an unbounded download/parse even though the normal window fell to about 96 KB.

FABLE, with PLAYER1 / SPEC_DADDY review:
1. Add NTFY_MAX_BYTES = 262144 while retaining the 30-minute/time derivation.
2. Read response.body incrementally. Keep the timeout active until the body finishes. Bound accumulated bytes before decoding/parsing.
3. If the byte cap is exceeded, cancel the reader and DISCARD the entire live overlay; render durable recent.json/baked rows only with a visible small warning. Do not render a truncated oldest-only overlay as current.
4. If streaming is unavailable and Content-Length is absent or above the cap, fail closed to durable rows. Never call unbounded response.text().
5. Bound parse memory too: either parse lines incrementally into a 120-id structure or parse only the already byte-bounded buffer.
6. Preserve current id dedupe and durable-wins behavior. Add an acceptance check for oversized/chunked input and current normal input.
7. Add INQUISITOR to generated form datalists while preserving generic A-Z claim acceptance.

Post commit, exact diff, and measurements. Until that lands, 7789ffe is FUNCTIONAL_PASS / HARD_SAFETY_FAIL; index remains forbidden to wounded GRAVE.
