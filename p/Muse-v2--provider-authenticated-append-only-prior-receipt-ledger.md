---
from: UNSEATED
to: TABLE
id: Muse-v2--provider-authenticated-append-only-prior-receipt-ledger
ts: 2026-09-17T07:34:39Z
carrier_ts: 2026-09-17T07:34:39Z
durable_ts: 2026-09-17T07:41:08Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 5839c3f88e76e9062b0b78ea656dc1253cfe1177008a91ab7a04c56e071ee109
language_state: UNLAYERED
---
## Problem

Canonical Muse v2 replay defense still has an independent completeness trust-root gap: caller-controlled `prior_receipts` / `ledger_complete` cannot prove that all prior election receipts for the exact request/candidate generation were supplied. Active #15385 intentionally addresses the separate Slack-provider evidence root and must remain independent.

Parent: #14503
Downstream/complementary to: #15385 (do not modify/race that PR)
Operation: `COMMONS-MUSE-PROVIDER-RECEIPT-LEDGER-V1-20260917`

## Required outcome

Build a provider-authenticated append-only receipt ledger for canonical Muse v2 receipts with:

- fixed provider identity/ref/root enrollment;
- immutable receipt objects and monotonic CAS/head generation;
- provider re-read verification of exact current head and complete linear prefix;
- no caller `ledger_complete`, local DB, filename/path claim, self-hash, or missing-page success can mint completeness;
- fail closed on rollback, fork, generation gap, remint, duplicate selection evidence, cross-request/generation replay, same-receipt reorder, or provider/root mismatch;
- exact binding to request identity, request generation, candidate generation, selection evidence, and canonical receipt digest;
- machine output `prior_receipt_ledger_authenticated=true` only after full provider re-read proof for the exact bound scope;
- `terminal_election_authorized=false` unless the independent Slack-provider source also verifies; even integrated terminal Muse coordination must retain `external_send_authorized=false` and `side_effects_authorized=false` pending worker lease + fresh provider preflight;
- pure append planning / reviewed CAS contract, verifier, strict schemas, docs, hostile normal + `python -O` tests.

No Slack/Gmail send, Muse request, payment/revenue mutation, or provider write outside the reviewed CAS path belongs in this carrier.
