# PAYMENT_CAPABILITY — provider-neutral storefront failover

Stripe is one rail. It is not the only lawful payment path Commons can name.
This leftover records every connected or candidate rail with exact provenance
and keeps the public storefront inert until a rail is truly chargeable.

Cite [ground/CHECKOUT_CAPABILITY.md](./CHECKOUT_CAPABILITY.md). Cite
[ground/PAY.md](./PAY.md). Cite [ground/STRIPE.md](./STRIPE.md). Cite
[ground/COMMERCE.md](./COMMERCE.md). Do not remint those cards.

## Current measured truth (2026-08-28T16:43:00Z)

- Token Junkie Labs Stripe `acct_1U6HI9ATH4EDE7XD` is **CHARGEABLE**:
  livemode, `charges_enabled=true`, `payouts_enabled=true`,
  `currently_due=[]`, verified external account last4 `7243`.
- Seven canonical Payment Links remain the public storefront.
- PayPal, GitHub Sponsors, and Square are **INERT**. Activating any of
  them requires owner KYC / bank / OTP / provider onboarding inside the
  official UI. Agents do not enter those values.
- Hosted Stripe invoices are owner-usable on the same chargeable account
  and stay off the public storefront.
- Collected cash is **USD 0**. AUTHORIZATION, SETTLEMENT, PAYOUT, and
  BANK_AVAILABLE remain `NOT_LANDED`.

## Failover

Public surfaces expose the first `CHARGEABLE` + `EXPOSE` rail. If Stripe
later fails closed, those URLs hide. The switcher then shows one-click
`EXTERNAL_OWNER_ACTION` links (PayPal signup, GitHub Sponsors setup,
Square signup, Stripe invoice dashboard) plus
`mailto:tokenjunkielabs@gmail.com`. No invented checkout.

## Measure

```bash
python3 host/payment_capability.py
python3 host/payment_capability.py --self-test
python3 -m unittest -v test_payment_capability.py test_payment_capability_door_hub.py test_payment_capability_hub_pages.py test_payment_capability_compose.py test_checkout_capability.py
```

Human door: [payment-capability.html](../payment-capability.html) ·
[pay.html](../pay.html) · [tips.html](../tips.html) ·
[commerce.html](../commerce.html)
Machine: [revenue/payment_capability/registry.json](../revenue/payment_capability/registry.json)

Composes reply-to-revenue, accepted-scope delivery, the resource ledger,
the feature board, and the profitability map. It does not replace them.

Open door stays. No auth. No secrets.
