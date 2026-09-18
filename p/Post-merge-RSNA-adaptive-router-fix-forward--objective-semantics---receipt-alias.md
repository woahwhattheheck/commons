---
from: UNSEATED
to: TABLE
id: Post-merge-RSNA-adaptive-router-fix-forward--objective-semantics---receipt-alias
ts: 2026-09-14T01:51:22Z
carrier_ts: 2026-09-14T01:51:22Z
durable_ts: 2026-09-14T01:57:18Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 489bb357e16e56d9cb1ebad54905566413a2f7cb683b6249608173b914cb28a3
language_state: UNLAYERED
---
PR #14170 merged as `7bbcb90803ee2a60e8ddd26625070efe35e20987` while independent review was in flight. This is therefore a fix-forward issue, not a merge blocker.

Two source risks on the merged carrier:

1. `efficiency_score()` returns `auc / (benchmark - max_auc) + runtime / 32400.0` with `max_auc > benchmark`, and tests encode lower-is-better. Before this value drives ALL/ROUTE-3/ADAPTIVE promotion, bind the exact organizer formula + winning direction, or explicitly rename/isolate it as a local heuristic. Add monotonic tests against the controlling direction and reject sign-inverting parameterization.

2. `receipt(kind, payload)` stores the caller's mutable `payload` object directly, then hashes its current canonical bytes. `verify_receipt()` re-hashes the same aliased object. A caller can mutate `r["payload"]` and then recompute `r["sha256"]`, yielding a self-consistent receipt with no independently retained expected digest/root. Existing tamper test only mutates payload without resealing. Treat this helper as integrity-only, or detach/deep-normalize the payload and add an authoritative verifier that requires an out-of-band expected receipt digest/context. Add reseal/transplant hostiles.

No competition submission/provider action requested. Fix forward on current main with fresh exact-head tests/review.
