# Paid Fulfillment Release Gate

A deterministic, offline decision layer between **money received** and **goods/services released**.

It is designed for workflows such as installers, rental/equipment release, field-service scheduling, order fulfillment, and automation systems where payment events and operational readiness arrive independently and may be retried or reordered.

## What it proves

A new `RELEASE` is emitted only when one normalized snapshot proves all of the following:

1. Payment-provider evidence is complete and fresh.
2. Captured funds in the order currency meet the exact minor-unit amount due.
3. There is no refund, chargeback, or cancellation in the snapshot.
4. Operations' latest readiness state is `FULFILLMENT_READY`.
5. Order, operations, payment, and fulfillment-history snapshots are all complete and fresh.
6. Fulfillment history does not already contain a release.

The module is deliberately read-only: it **does not** charge, refund, release inventory, schedule work, contact customers, or mutate a provider. Its output is the receipt another workflow can consume.

## Decisions

- `RELEASE` — exact snapshot permits one new release (`release_authorized: true`).
- `HOLD` — evidence is incomplete/stale or payment/readiness is insufficient.
- `EXCEPTION` — contradictory or reversal state needs explicit handling (refund, chargeback, cancellation, conflicting IDs, multiple release IDs, post-release reversal).
- `ALREADY_RELEASED` — release history already records the order; replay does not authorize another release.

## Normalized input contract

The input has four authoritative source snapshots:

- `PAYMENT_PROVIDER`
- `OPERATIONS_SYSTEM`
- `ORDER_SYSTEM`
- `FULFILLMENT_SYSTEM`

Every source reports `{ "complete": bool, "observed_at": RFC3339 }`. `freshness_window_seconds` is measured against `snapshot_at`. Events are order-bound and source-bound; a payment event cannot masquerade as an operations event.

Supported events:

- `PAYMENT_CAPTURED`
- `PAYMENT_REFUNDED`
- `PAYMENT_CHARGEBACK`
- `FULFILLMENT_READY`
- `FULFILLMENT_NOT_READY`
- `ORDER_CANCELLED`
- `FULFILLMENT_RELEASED`

Money is integer minor units only. Exact duplicate `event_id` rows are deduplicated, so at-least-once webhook delivery cannot double-count a payment. Reusing an event ID with different bytes is rejected. Captures are also reconciled by `payment_id`; refund and chargeback identities must reference a known capture.

## Run

```bash
python revenue/paid_fulfillment_release_gate/gate.py input.json
python revenue/paid_fulfillment_release_gate/gate.py input.json --output receipt.json
```

`--output` writes atomically and refuses to overwrite the input through the same path. The receipt contains normalized financial state, readiness, source freshness, release history, a SHA-256 over normalized events, and a SHA-256 over the receipt itself.

A complete runnable fixture is in `example.json`.

## Test

```bash
python -m unittest discover -s revenue/paid_fulfillment_release_gate -p 'test_*.py' -v
python -O -m unittest discover -s revenue/paid_fulfillment_release_gate -p 'test_*.py' -v
```

The suite covers happy release, partial payment, multi-payment totals, exact webhook replay, conflicting event/payment IDs, wrong currency, refunds, chargebacks, cancellation, readiness revocation/conflict, incomplete/stale source snapshots, cross-order/source injection, already-released replay, multiple releases, post-release reversal, deterministic ordering/digests, duplicate JSON keys, boolean-money rejection, and atomic output custody.
