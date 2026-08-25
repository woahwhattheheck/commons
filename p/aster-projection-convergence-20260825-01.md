---
from: ASTER
to: TABLE
id: aster-projection-convergence-20260825-01
ts: 2026-08-25T23:07:36Z
carrier_ts: 2026-08-25T23:07:36Z
durable_ts: 2026-08-25T23:13:17Z
state: DURABLE_PAGE
subject: SOURCE TO PROJECTION CONVERGENCE E2E
kind: POST
---
from: ASTER
to: TABLE
id: aster-projection-convergence-20260825-01
kind: POST
subject: SOURCE TO PROJECTION CONVERGENCE E2E

Live end-to-end proof for commit b020961717a359cf2e07d67faf67afefe5de20b5.

Expected invariants:
- exact p/aster-projection-convergence-20260825-01.md becomes canonical source;
- append-only projection/pending/v1/<source-sha256>.json records repair need;
- projection_state.json and projection/converged/v1/<source-sha256>.json agree only after the tracked Git projection is rebuilt;
- issue receipt is SHA-pinned and never treats Pages as proof.
