# Checkout capability — shortest truthful buyer path

Public commerce surfaces expose a Stripe URL only when **all** of these
are proven on a durable observation:

1. livemode
2. account `charges_enabled=true`
3. account `payouts_enabled=true`
4. that exact Payment Link `active=true`
5. the URL matches the canonical recorded SKU URL
6. capability evidence names a provider readback and an offset-aware time

A URL is not chargeability. Chargeability is not settlement. Settlement
is not payout. Payout is not bank-available cash. A click is intent.

Unverified, duplicate, or non-canonical URLs stay **inert**: they may be
stored as machine provenance, never as `<a href>`.

Stripe onboarding cannot freeze the business. When Stripe capability
fails closed, public surfaces hide Stripe URLs and keep the
provider-neutral contact fallback
`mailto:tokenjunkielabs@gmail.com`. Owner-private PayPal wallet and
Stripe hosted invoices stay inside official provider UIs. No bank,
routing, tax, credential, or ACH destination is stored here.

Collected cash stays **USD 0** until an independently evidenced
`BANK_AVAILABLE` event. This leftover does not invent payments,
receipts, buyers, or KYC results.

## Measure

```bash
python3 host/checkout_capability.py
python3 host/checkout_capability.py --self-test
python3 -m unittest -v test_checkout_capability.py test_stripe_payment_links.py test_outcome_commerce.py
```

Human doors: [pay.html](../pay.html) · [commerce.html](../commerce.html) · [tips.html](../tips.html) · [payment-capability.html](../payment-capability.html)
Machine: [revenue/checkout_capability/snapshot.json](../revenue/checkout_capability/snapshot.json)
Registry: [revenue/payment_capability/registry.json](../revenue/payment_capability/registry.json)
Catalog: [revenue/outcome_commerce/catalog.json](../revenue/outcome_commerce/catalog.json)

Cite [ground/PAYMENT_CAPABILITY.md](./PAYMENT_CAPABILITY.md). Cite [ground/STRIPE.md](./STRIPE.md). Cite [ground/COMMERCE.md](./COMMERCE.md).
Cite [digit-payment-links-receipt-20260826-01](../p/digit-payment-links-receipt-20260826-01.md).
Do not remint those ids. Open door stays.
