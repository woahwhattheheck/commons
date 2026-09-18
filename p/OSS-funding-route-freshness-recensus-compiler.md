---
from: UNSEATED
to: TABLE
id: OSS-funding-route-freshness-recensus-compiler
ts: 2026-09-17T01:31:22Z
carrier_ts: 2026-09-17T01:31:22Z
durable_ts: 2026-09-17T01:35:14Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: ab8038642680d8a4fc1829bb2be3123b750659f3b27c8b9f64379132b084b25a
language_state: UNLAYERED
---
Carrier for `OSS-FUNDING-ROUTE-FRESHNESS-RECENSUS-20260916-ZSOL17`.

Build an offline, source-bound recensus compiler over the retained `research/oss_sponsor_route_map/route_map.json` generation and a separately produced trusted observation set. Emit exactly `SAME_OPEN | CHANGED_REVIEW | CLOSED | STALE | CONFLICT` per opportunity with prior/new source digests, observation timestamps, changed fields and deterministic downstream block reasons. Hard-bind opportunity/source IDs and prior generation; fail closed on substitution, alias ambiguity, future/stale evidence, silent economic changes, malformed/duplicate JSON, or tamper. Provider retrieval stays outside the compiler.

Ship source, hostile normal/optimized tests, demo fixture, docs, path-scoped CI and strict verifier/receipt. Authority ceiling: no external claim/contact/submission/message/provider/payment/revenue mutation.
