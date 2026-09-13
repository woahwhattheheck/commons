# Commercial Lifecycle Ledger

`commercial_lifecycle_ledger` is a deterministic, side-effect-free evidence reconciler for the commercial path that sits **after opportunity selection** and spans offer, acceptance, funding, delivery, settlement, and finance-recognition evidence.

The repository already has strong primitives for opportunity selection and commercial-offer authority. This package does not replace either. It consumes immutable deal/evidence commitments and answers a narrower question:

> Given the exact evidence we have, what lifecycle facts are currently supported, and do the money/reversal records reconcile without skipping authority boundaries?

It never sends outreach, signs or accepts a contract, starts fulfillment, moves/refunds money, or recognizes revenue by itself.

## Contract

Each ledger binds one immutable commercial subject:

- `opportunity_sha256`
- `offer_sha256`
- `scope_sha256`
- opaque `buyer_ref_sha256`
- one exact three-letter currency
- integer `contract_amount_minor`
- offer expiry

`subject_commitment()` hashes those immutable terms. Every event must carry that digest, preventing an acceptance/payment/finance event from being replayed onto another buyer, offer, scope, amount, or currency.

Events use exact schemas and named evidence authorities:

| Event | Required evidence authority |
|---|---|
| `OPPORTUNITY_QUALIFIED` | `owner` |
| `OFFER_OWNER_APPROVED` | `owner` |
| `OFFER_SENT` | `transport` |
| `BUYER_ACCEPTED` | `buyer` |
| `FUNDING_VERIFIED` | `funding` |
| `EXECUTION_STARTED` | `owner` |
| `FULFILLMENT_ACCEPTED` | `buyer` |
| `PAYMENT_SETTLED` | `payment` |
| `REVENUE_RECOGNIZED` | `finance` |
| `CANCELLED` | `owner` |
| `REFUND_SETTLED` | `payment` |
| `REVENUE_REVERSED` | `finance` |

Forward lifecycle stages cannot be skipped or repeated. Offer approval/send/acceptance must occur before the bound offer expiry. Evaluation time is supplied out of band as `trusted_as_of`; payloads cannot choose their own current time.

## Money and reversals

Money is integer minor units only; booleans, floats, decimal strings, coercion, and cross-currency events are rejected.

- funding evidence must cover the exact contract amount;
- settlement can be installment-based but cannot exceed the contract amount;
- finance-recognition evidence cannot exceed net settled cash evidence;
- refunds must reference a specific prior settlement event and cannot exceed its residual;
- recognition reversals must reference a specific refund and cannot exceed either that refund or recognized amount;
- net recognized evidence may never exceed net settled cash evidence.

The receipt exposes both gross and net evidence totals. It does **not** convert those totals into authority.

## Idempotency and tamper evidence

Event IDs are idempotency keys. An identical duplicate event is safely collapsed; a conflicting reuse of the same event ID fails closed.

The output binds:

- normalized-input SHA-256;
- immutable subject SHA-256;
- chained event SHA-256;
- exact trusted evaluation time;
- gross/net cash and reported-recognition evidence;
- unique/input event counts;
- canonical receipt SHA-256.

`verify_receipt()` recomputes the entire ledger and compares exact receipt bytes.

All action-authority fields remain `false`, including outreach/send, contract execution, fulfillment, payment/refund, and revenue recognition.

## Validation

From repository root:

```bash
python -m unittest -v revenue.commercial_lifecycle_ledger.test_lifecycle
python -O -m unittest -v revenue.commercial_lifecycle_ledger.test_lifecycle
python -m py_compile \
  revenue/commercial_lifecycle_ledger/lifecycle.py \
  revenue/commercial_lifecycle_ledger/test_lifecycle.py
```

The hostile suite covers lifecycle skips/repeats, cross-deal replay, wrong authority, future/out-of-order events, offer expiry, funding shortfall, money coercion, overpayment, premature recognition, refund/reversal reference integrity, duplicate IDs, schema drift, duplicate JSON keys, non-finite JSON, receipt tampering, and trusted-time replay.
