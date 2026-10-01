# Private chargeback-defense WSGI receiver advancement

The existing `private-chargeback-defense-desk` now includes a standards-compliant private ingress boundary for authorized TJLabs payment operators.

## Completed activation

- Prior delegated adapter: [PR #30180](https://github.com/woahwhattheheck/commons/pull/30180), merge `f408aaf43e42c56c465bab211b5a6c279c8799f5`.
- Reproduced defect: a real PEP 3333 environment supplies `CONTENT_LENGTH`, while the adapter and its fixture used a nonstandard mixed-case spelling; the request failed before ingest.
- Repair: [PR #30181](https://github.com/woahwhattheheck/commons/pull/30181), merge `42f86a421e99cac7b17b20c0396785e5254087ae`.
- Current repaired blobs:
  - `host/chargeback_defense_receiver.py` — `9c653371d6c4acad8812aafba4d65c1a33d44a59`
  - `host/test_chargeback_defense_receiver.py` — `41efcade33086752edfedda91d75a6b7978d3ae5`
  - `revenue/chargeback_defense/private-receiver-adapter.md` — `eace6ca81517467064d876d80d9c8287dec1a120`

## Verification

- Focused tests: 28/28 under normal Python and 28/28 under `python3 -O`.
- Synthetic loopback: 9/9 checks, zero external calls.
- Hosted repair checks: open-door guard, source parse, path manifest, and Muhlnickel boundary all succeeded.
- Compile, nonstandard-key, privacy, and live-secret-pattern checks passed.
- The adapter forwards exact request bytes and the exact signature header, returns success only after a durable recorded or duplicate outcome, and preserves the first row on event-ID conflicts.

## Boundaries

This is source capability, not deployment. No provider was configured or contacted; no live secret or real customer event was used; no payment, refund, dispute submission, buyer acceptance, settlement, revenue, or cash is claimed. Private backend/storage selection, Stripe reauthentication, endpoint-secret creation, deployment, and observation of one real signed event remain owner/operator actions.

The existing build order is fulfilled: [chargeback-defense-private-receiver-adapter-20261001-01](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1790817200749509). No duplicate build order was minted.
