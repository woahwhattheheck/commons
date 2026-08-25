# Hosted processor handoff

This is the stopping boundary for public Commons work. **Never paste or relay
bank account, routing, card, tax-ID, identity-document, credential, or payout
destination values through Commons, Slack, GitHub, prompts, logs, or
receipts.**

## Recommended owner action

Open Stripe's official hosted payout settings directly:

<https://dashboard.stripe.com/account/payouts>

Complete provider onboarding and enter the payout destination there only.
After a real buyer accepts a quote, create a customer-specific hosted invoice
inside:

<https://dashboard.stripe.com/invoices>

The public pipeline does not create a Stripe account, payment link, invoice,
checkout session, customer, or payout. The hosted provider decides which
verification fields are required. Commons never mirrors those values.

## Fallback

If Stripe is unavailable, use the official PayPal Wallet surface:

<https://www.paypal.com/myaccount/money/>

The same boundary applies: connect the withdrawal destination inside the
provider surface only. Do not publish a reusable payment address or private
remittance instructions.

## Receipt truth

The only public processor datum allowed in a future receipt is an opaque
provider reference plus a SHA-256 of the private provider event payload. That
records a reference; it does not independently prove legal acceptance,
delivery, settlement, payout, or bank availability.

`AUTHORIZATION != SETTLEMENT != PAYOUT != BANK_AVAILABLE`.

Current state:

- buyer: **UNKNOWN**
- accepted quote: **NOT_LANDED**
- delivery: **NOT_LANDED**
- processor payment: **NOT_LANDED**
- bank available: **NOT_LANDED**
- collected cash: **USD 0**
