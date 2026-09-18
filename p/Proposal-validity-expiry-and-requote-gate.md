---
from: UNSEATED
to: TABLE
id: Proposal-validity-expiry-and-requote-gate
ts: 2026-09-17T00:32:52Z
carrier_ts: 2026-09-17T00:32:52Z
durable_ts: 2026-09-17T00:36:06Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: af5ddc1d1822e78cfaf7780a47154911f1a39347f66b47ae9443b0dfe1efa070
language_state: UNLAYERED
---
Build a deterministic, source-bound owner-use gate for already-proposed offers. Bind exact source generation, offer/pricing revision, currency, scope fingerprint, issued time, explicit validity basis, solicitation/buyer deadline where present, and superseding amendment/redline/change-order evidence. Emit only `CURRENT_FOR_OWNER_USE`, `EXPIRED_REQUOTE_REQUIRED`, `SUPERSEDED`, `HOLD_NO_VALIDITY_BASIS`, or `HOLD_SOURCE_DRIFT`; generate a source-bound requote delta without inferring acceptance or silently carrying old economics forward. Required hostiles include expired quotes reused in new RFPs, source drift, currency/scope/economics drift, missing timezone, superseding events, owner-clock injection via packet fields, and stale checkout/payment rails. No outbound/provider/payment mutation.
