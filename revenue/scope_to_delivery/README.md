# Accepted-scope-to-delivery

This directory is the machine-readable composition layer that turns a **written
buyer agreement** into the artifacts a real delivery needs:

1. exact statement of work
2. bounded work packet
3. execution status
4. evidence bundle
5. delivery receipt
6. invoice / payment state
7. buyer-readable handoff

It composes the existing Outcome Commerce catalog, production-survival
acceptance lock, DIO delivery-receipt rule, checkout handoff money states, and
human-outcomes SKUs. It does **not** replace those roads.

## Honesty

- Do not fake acceptance, work, delivery, invoice, payment, testimonial, or receipt.
- `ACCEPTED` requires `written_acceptance.status = PRESENT`, the exact terms
  digest, a catalog SKU, and a catalog-matching amount.
- `LOCKED_SOW` exists only after `ACCEPTED`. Party names, emails, and addresses
  stay `NOT_ON_PUBLIC_MAIN`.
- A work packet is issued only from a locked SOW.
- `PASS` requires every binary acceptance row `PASS` with `public_ref` + `sha256`.
- `delivered` is true only on `PASS`. Payment never proves delivery.
- `QUOTED != CHARGEABLE != INVOICED != AUTHORIZATION != SETTLEMENT != PAYOUT != BANK_AVAILABLE`.
- `cash_claimed` is true only at `BANK_AVAILABLE`.
- Current catalog funnel truth remains `accepted_scopes: 0`, `paid_deliveries: 0`,
  `collected_cash_usd: "0.00"` until live evidence says otherwise. Fixtures here
  are synthetic and public.

## CLI

```text
python3 host/scope_to_delivery.py catalog
python3 host/scope_to_delivery.py sow --agreement revenue/scope_to_delivery/fixtures/accepted_agreement.json
python3 host/scope_to_delivery.py project \
  --agreement revenue/scope_to_delivery/fixtures/accepted_agreement.json \
  --observations revenue/scope_to_delivery/fixtures/accepted_observations.json \
  --payment revenue/scope_to_delivery/fixtures/payment_authorized.json
```

Stdlib only. No Stripe, Airtable, email, or bank calls.

## Surfaces

- Human door: [`../../scope-to-delivery.html`](../../scope-to-delivery.html)
- Ground: [`../../ground/SCOPE_TO_DELIVERY.md`](../../ground/SCOPE_TO_DELIVERY.md)
- Host: [`../../host/scope_to_delivery.py`](../../host/scope_to_delivery.py)
- Tests: [`../../test_scope_to_delivery.py`](../../test_scope_to_delivery.py)
- Bindings: [`catalog_bindings.json`](./catalog_bindings.json)
- Synthetic fixtures: [`fixtures/`](./fixtures/)
