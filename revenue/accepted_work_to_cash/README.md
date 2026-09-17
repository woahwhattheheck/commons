# Accepted Work to Cash Reconciler

`accepted_work_to_cash` converts retained evidence about delivered/merged/accepted work into a deterministic realization queue without treating proposals, merges, awards, invoices, payment links, or internal claims as cash.

It is intentionally a **read-only evidence compiler**. It cannot send a message, select a Muse claimant, mutate a provider, create an invoice, move money, establish a receivable, post an accounting entry, or recognize revenue. Every such authority bit is hard-coded `false` in output.

## Why this exists

Revenue work spans heterogeneous lanes: bug bounties, contracts/subcontracts, competitions, paid platforms, product work, and other accepted deliverables. Their evidence differs, but the money boundary must stay the same:

`delivered -> accepted/merged/awarded -> route/claim/invoice -> provider-backed payment`

Only `PAYMENT_RECEIVED` backed by `PAYMENT_PROVIDER` evidence is counted as cash. A GitHub merge is acceptance evidence for code work, not payment. An award is not payment. An issued invoice or payment link is not payment.

The compiler ranks **realizability before headline value**, so a smaller accepted item with a live collection route can outrank a large speculative item.

## Input

Input must match `TJL_ACCEPTED_WORK_TO_CASH_V1`. See `schema.json` and `fixtures/portfolio.json`.

Each item binds payer/program, work identity and lane, optional advertised amount, retained evidence events with exact source class/reference/SHA-256/timestamp, and route/purpose only on contact-control events.

Evidence bindings are unique across the whole portfolio. Reusing the same retained receipt across two work items is rejected so one provider payment cannot be double-counted.

### Evidence source constraints

- `MERGED` requires `GITHUB` evidence.
- `ACCEPTED` / `AWARDED` require buyer, sponsor, or platform evidence.
- `CLAIM_SUBMITTED`, `INVOICE_ISSUED`, and `PAYMENT_LINK_ISSUED` require provider/platform receipt evidence.
- `PAYMENT_RECEIVED` requires a positive amount and `PAYMENT_PROVIDER` evidence.
- `CONTACT_REQUIRED`, `MUSE_CLEAR`, and `OUTBOUND_SENT` require an exact route and purpose.

## Settlement target precedence

When amounts differ over time, the controlling retained instrument is selected in this order:

1. `INVOICE_ISSUED`
2. `PAYMENT_LINK_ISSUED`
3. `AWARDED`
4. `ACCEPTED`
5. `CLAIM_SUBMITTED`
6. advertised amount

Conflicting amounts in the **same second and same controlling class** fail closed as `HOLD_CONTRADICTION`; arbitrary event IDs never choose monetary truth.

## Terminal action packets

Typical states include `DONE_PAID`, `COLLECT_REMAINDER_REVIEW`, `RECONCILE_OVERPAYMENT`, `COLLECTION_REVIEW`, `AWAIT_CLAIM_ADJUDICATION`, `OWNER_CLAIM_ACTION`, `MUSE_REQUIRED`, `OWNER_PROVIDER_PREFLIGHT`, `ROUTE_TO_CASH_REQUIRED`, `ACCEPTANCE_EVIDENCE_REQUIRED`, and fail-closed HOLD / DNR / closed states.

`MUSE_REQUIRED` contains the exact retained route and purpose. A matching fresh `MUSE_CLEAR` **still does not grant send authority**; it advances only to `OWNER_PROVIDER_PREFLIGHT`.

## CLI

```bash
python -m revenue.accepted_work_to_cash compile \
  revenue/accepted_work_to_cash/fixtures/portfolio.json \
  /tmp/accepted-work-to-cash.bundle.json

python -m revenue.accepted_work_to_cash verify \
  /tmp/accepted-work-to-cash.bundle.json
```

Compilation uses bounded stable regular-file reads and exclusive output creation. Existing output files are never overwritten.

The bundle embeds the exact source, canonical source hash, compiled portfolio, and receipt hash. Verification recomputes source semantics; merely rehashing a forged output does not make it valid.

## Tests

```bash
python -m py_compile revenue/accepted_work_to_cash/*.py
python -m unittest -q revenue.accepted_work_to_cash.test_money revenue.accepted_work_to_cash.test_guardrails
python -O -m unittest -q revenue.accepted_work_to_cash.test_money revenue.accepted_work_to_cash.test_guardrails
```

Hostile coverage includes duplicate JSON keys, non-finite numbers, future evidence, wrong provider classes, invoice-not-cash, payment-link target precedence, exact/partial/over-payment, DNR/reply chronology, stale contact routes, same-second commercial contradictions, cross-item payment-receipt reuse, order invariance, forged-bundle rehashing, output overwrite resistance, and hard-false authority.

A path-scoped GitHub Actions recipe lives at `ci/workflow-recipes/accepted-work-to-cash.yml`. It is deliberately a recipe rather than a new active `.github/workflows` file so this product does not expand the repository's active hosted-workflow surface. It can be promoted by the repository's workflow-custody lane when that surface is ready.

## Relationship to revenue funnel control

This product does not replace the per-opportunity revenue-funnel compiler. It is a portfolio reconciler across heterogeneous accepted/delivered work and provider evidence, producing cross-item terminal actions and cash/outstanding totals. It deliberately incorporates the same-second monetary-instrument ambiguity defense so lexical IDs cannot decide money truth.

## Truth boundary

Output truth boundary is `RETAINED_EVIDENCE_PROJECTION_NOT_CURRENT_PROVIDER_AUTHORITY`.

The output is a deterministic projection of retained evidence, not a claim that external providers are currently synchronized, not permission to contact anyone, and not an accounting/revenue-recognition system.
