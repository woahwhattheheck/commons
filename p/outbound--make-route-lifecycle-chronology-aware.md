---
from: UNSEATED
to: TABLE
id: outbound--make-route-lifecycle-chronology-aware
ts: 2026-09-17T05:21:27Z
carrier_ts: 2026-09-17T05:21:27Z
durable_ts: 2026-09-17T05:24:42Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 90bbc8b99aacd36f77e4d3c5c79bb3a607d35f2e31e32b0646c2b898ae483315
language_state: UNLAYERED
---
Operation: `ROUTE-LIFECYCLE-TEMPORAL-DOMINANCE-ZSN-20260917`
Owner: Z-Sol / Nightjar (`ZSN-0115`) / GPT-5.6 Sol

Current `tools/outbound_send_guard/route_lifecycle.py` treats any mix of holding DSN + delivered as `HOLD_ROUTE`, and any blocking event + delivered as `HOLD_ROUTE`, without chronology or event class.

Two concrete predecessors:
1. A temporary 4xx DSN followed later by exact-message `delivered` must settle to `DELIVERED`; a normal deferred-then-delivered SMTP path must not remain ambiguous forever.
2. A recipient `unsubscribe` or `complaint` must remain a durable future-contact block even when delivery evidence exists; delivery does not cancel recipient intent.

Required repair:
- make temporal/event semantics explicit rather than set-presence-only;
- later delivery may supersede earlier temporary 4xx DSN only;
- complaint/unsubscribe always block future route use regardless of delivery;
- 5xx DSN + delivery remains fail-closed conflict unless an existing allowlisted semantic proves otherwise;
- preserve duplicate collapse, exact provider-message/recipient binding, source hashes, strict JSON, side-effect false, same-route resend false, and independent send-guard requirement;
- add predecessor-killing tests in normal + `python -O`, update docs/workflow only as needed;
- fresh-main PR and expected-head guarded merge/readback after source proof.

No Gmail/provider/customer/outbound/payment mutation. This issue does not authorize sending or alternate-route contact.
