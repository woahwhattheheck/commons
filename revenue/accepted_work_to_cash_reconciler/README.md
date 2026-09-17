# Accepted Work to Cash Reconciler

`accepted_work_to_cash_reconciler` is the operational composition layer above
`revenue_funnel_control`. The upstream compiler proves an evidence-bound economic
stage; this module answers the next narrower question:

> Given retained acceptance, route, contact and provider-cash evidence, what is
> the terminal **owner action** for each item without accidentally authorizing a
> send, invoice, payment mutation, receivable, accounting entry, or revenue claim?

It exists for merged/delivered work, paid-work platforms, subcontract/workshare
promises, accepted proposals, invoices/payment links, sponsor adjudications, and
provider cash evidence. It is deliberately stricter than "merged = paid".

## Important boundaries

- `MERGED` alone becomes `MERGED_WORK_ONLY`, not buyer/sponsor acceptance.
- `ACCEPTED` is externally accepted only when its retained source class is
  `BUYER_MESSAGE` or `SPONSOR_MESSAGE`.
- A retained `PAYMENT_RECEIVED` event is **not** enough for `DONE_PAID`.
  Every payment event must also have a separately bound provider confirmation.
- Provider confirmation remains retained evidence, not a live bank/Stripe/provider
  query. The output truth boundary says so explicitly.
- New contact is never authorized. If contact is the next step and a source-bound
  route exists, the product emits `MUSE_REQUIRED` with exact recipient + purpose.
  Even a historical `MUSE_CLEAR` event does not become reusable send authority.
- A prior outbound becomes `WAIT_EXTERNAL`; `DNR` becomes `INBOUND_ONLY`;
  collision becomes `HOLD_COLLISION`; a later human inbound becomes
  `INBOUND_REVIEW`.
- Queue order is by deterministic realizability band, then opportunity id. Headline
  amount is reported but never used to rank the queue.
- All authority bits are hard false.

## Composition contract

Input schema: `TJL_ACCEPTED_WORK_TO_CASH_V1`

The document contains:

1. `funnel_input`: the ordinary `TJL_REVENUE_FUNNEL_V1` source ledger. This module
   calls the merged upstream compiler itself rather than trusting caller-authored
   stage labels.
2. `routes`: zero or one evidence-bound route per opportunity. Route evidence must
   be a buyer/sponsor message, provider directory, or organizer rules source.
3. `payment_confirmations`: zero or one provider confirmation per upstream
   `PAYMENT_RECEIVED` event, bound by opportunity id + payment event id.

The compiler emits a content-addressed
`TJL_ACCEPTED_WORK_TO_CASH_BUNDLE_V1` and the verifier recompiles both the upstream
funnel semantics and the reconciler semantics from embedded input.

## Terminal actions

Representative terminal actions are:

- `VERIFY_PROVIDER_CASH`
- `RECONCILE_PAYMENT_EVIDENCE`
- `INBOUND_REVIEW`
- `MUSE_REQUIRED`
- `WAIT_EXTERNAL`
- `INBOUND_ONLY`
- `HOLD_COLLISION`
- `OWNER_INVOICE_PREPARATION_REVIEW`
- `ACCEPTANCE_EVIDENCE_REQUIRED`
- `ROUTE_EVIDENCE_REQUIRED`
- `DONE_PAID`
- `DONE_ZERO_VALUE`

`OWNER_INVOICE_PREPARATION_REVIEW` is an internal review state only. The authority
map still forbids invoice creation or delivery.

## CLI

```bash
python -m revenue.accepted_work_to_cash_reconciler.engine compile \
  revenue/accepted_work_to_cash_reconciler/example.json /tmp/work-to-cash.bundle.json

python -m revenue.accepted_work_to_cash_reconciler.engine verify \
  /tmp/work-to-cash.bundle.json
```

CLI input is a bounded regular UTF-8 JSON file with duplicate keys, floats,
non-finite constants and oversized integers rejected. Output is create-exclusive
mode `0600` and is never silently overwritten.

## Tests

```bash
python -m py_compile revenue/accepted_work_to_cash_reconciler/*.py test_accepted_work_to_cash_reconciler.py
python -m unittest -v test_accepted_work_to_cash_reconciler.py
python -O -m unittest -v test_accepted_work_to_cash_reconciler.py
```

The root test is enrolled by the existing Commons `test_*.py` retained-test path.
This product intentionally adds no new standalone workflow slot; exact-head CI is
read from the retained Commons battery before merge.
