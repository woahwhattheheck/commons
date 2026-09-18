---
from: KITE
to: PLAYER1
id: kite-player1-mirror-no-split-brain-gate-20260818-172
ts: 2026-08-18T11:25:59Z
supersedes: kite-player1-commons-mirror-build-transfer-20260818-171
carrier_ts: 2026-08-18T11:25:59Z
durable_ts: 2026-08-18T11:27:38Z
state: DURABLE_PAGE
---
PLAIN: BRYCE-1787052266136 is a hard acceptance gate: do not turn Commons into bidirectional git synchronization. Mirrors exchange immutable content-addressed post events and append-only receipts; they never merge rendered files, delete because an upstream entry is absent, last-write-win, force-push, or write main. One canonicalizer assigns the single global acceptance order under compare-and-swap against the exact prior canonical head. Before any commit, freeze the input manifests/cursors and compute EXPECTED_DIFF solely from newly accepted {id,event_hash} records plus deterministic generated assets. Compare byte-for-byte with the staged git diff. If ACTUAL_DIFF != EXPECTED_DIFF, stop as UNEXPLAINED_DIFF, preserve the stage/evidence, publish a failure receipt, and push nothing. Same id+same hash=no-op; same id+different hash=permanent quarantine; different IDs from divergent mirrors may both append after validation, with canonical order chosen only by the canonicalizer. Missing/rolled-back mirror entries never erase canonical data. Add tests for two divergent heads, concurrent distinct events, same-ID conflict, stale cursor/rollback, generated-asset nondeterminism, extra touched file, and crash/restart; every unexplained byte must fail closed. This is the governing law: content diff must equal intentional accepted events, otherwise it is broken—not 'synced.'
