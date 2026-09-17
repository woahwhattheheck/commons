# Invoice Resolution Portal Pilot — authenticated payment-link receipt

Observed against the Token Junkie Labs Stripe account on **2026-09-17** before publication of the public product door.

This receipt records provider configuration only. It does **not** prove buyer acceptance, capture, settlement, payout, bank cash, or recognized revenue.

## Provider object

- Product / line-item description: `Invoice Resolution Portal Pilot`
- Payment Link ID: `plink_1UFiB3ATH4EDE7XDOqZlYdCS`
- Live URL: `https://buy.stripe.com/8x23cuckZ2QV9uFfFo43S0z`
- Provider mode: `livemode=true`
- Active: `true`
- Currency: `usd`
- Unit amount: `250000` minor units (`$2,500.00`)
- Capture method: `manual`
- Customer creation: `always`
- Billing-address collection: `required`
- Completed-session restriction: `count=0`, `limit=1` at observation
- Required custom field: exact invoice ID / revision for the pilot
- Offer ID: `invoice-resolution-portal-pilot`
- Capture boundary: `written_scope_acceptance`
- Fulfillment capacity: `one-active-buyer`

## Provider-facing boundary

The live checkout copy says the $2,500 action is an **authorization**, not settlement or cash. Exact invoice/revision, intake surface, and written acceptance criteria are confirmed before capture; if the scope cannot be accepted, the authorization is canceled. Production credentials and customer records are out of scope for checkout intake.

The provider object therefore authorizes publication of the exact Payment Link as an available commercial rail. It does not authorize this repository, static HTML, or fulfillment compiler to infer later provider state.

## Fulfillment binding

The matching shipped fulfillment carrier is:

- `revenue/invoice_resolution_portal_pilot/`
- Commons PR `#15386`
- merge commit `816d867ebe04e5cdd1440e8eba74e50f29b978d1`
- product ID `invoice-resolution-portal-pilot`
- fixed pilot price `$2,500`
- commercial state in the compiler: `PROPOSED_NOT_ACCEPTED`
- optional `$5,000` integration: separate proposed follow-on only; no checkout asserted here

The fulfillment package and this receipt deliberately keep buyer-send, payment-taking, plan approval, dispute adjudication, invoice mutation, accounting/legal conclusion, customer-acceptance, payment, and revenue authority false unless separately evidenced by the proper provider or owner process.
