# Payment defense operating plan

The defense desk preserves payment and delivery facts, raises private operator alerts, and prepares factual evidence. It does not decide whether criticism is fraud. Source, public posting and Action Pad access remain open.

## Operating boundary

Public code and offer descriptions belong here. Customer correspondence, contracts, delivery logs, event databases, dispute IDs and evidence packets belong in private cloud storage outside every repository, static site, board and shared prompt. Payment credentials belong in a provider secrets vault. Give a collector only the access required for its job.

The tools run on demand. This change creates no schedule, worker deployment, paid service, merchant account or provider configuration. They cannot refund, capture, block, contact buyers, submit dispute evidence or change prices. One authorized payment operator owns each financial case to prevent conflicting actions.

## Defender roles

| Role | Input | Output | Financial action |
| --- | --- | --- | --- |
| Event collector | Verified private Stripe event delivery | Minimal append-only event ledger | None |
| Deadline watcher | Event ledger and actual dispute deadlines | Private summary and action flags | None |
| Delivery recorder | Actual agreed scope, terms shown, deliverable and communications | Private records of what happened | None |
| Packet builder | Dispute reason, records and explicit source files | Self-contained evidence packet and hashes | None |
| Payment operator | Facts, actual merchant settings and customer rights | One recorded decision and provider workflow | Authorized execution through private provider surface |

The agents must not manufacture payment, customer acceptance, delivery, account activity, evidence, reviews or transaction history. A file hash establishes file identity; it does not establish when a buyer received, read or accepted it. An absence of events is unmeasured coverage, not proof of zero sales or disputes.

## Prevention before a charge

Keep the advertised SKU, checkout SKU, currency, total and billing cadence consistent. Label an hour purchase as an hour; it cannot serve as proof of payment for a larger diagnostic or pilot. Show deliverables, start conditions, exclusions, delivery clock, acceptance criteria, cancellation and refund terms before purchase. Retain the version the buyer actually saw and accepted. Provide a recognizable statement descriptor and a direct support route.

For custom engagements, use the existing written scope and milestone amounts. Invoice the specific agreement. Consider a supported customer-initiated bank transfer or wire for negotiated work, with a confirmed settlement and explicit refund process. Do not describe ACH debit or every bank transfer as irreversible. Do not split charges merely to manipulate a dispute ratio.

Keep Radar's risk protections. Evaluate appropriate authentication and transaction-pattern controls using actual account data. 3DS can shift eligible fraud liability; it does not prove service delivery or defeat quality/nonreceipt disputes. Requesting it does not guarantee that the issuer supports or performs authentication.

If screening must precede charging, explicitly use an eligible separate authorization/capture flow and track authorization expiry. Ordinary Radar review usually happens after capture. Neither the ledger nor a review flag changes existing Checkout behavior.

Evaluate RDR/Ethoca dispute prevention with the actual merchant account, fee schedule, eligibility and a bounded financial policy. It returns money in eligible cases to prevent escalation. Enrollment is a separate operator action; it is not free immunity, and it is not enabled by this repository change.

## Delivery and evidence

Drive payment fulfillment from verified provider events and the settled payment state, not a success-page redirect. Existing checkout bridge observations and scope-to-delivery acceptance remain authoritative in their own domains. Payment, fulfillment, buyer acceptance, payout and bank availability are different facts.

Store a private order record containing: merchant/account environment, SKU and quoted amount, specific scope, agreement/terms versions, actual payment references, delivery destination and timestamp, artifact version/hash, receipt of access where available, customer correspondence and any real acceptance. Collect only what is needed and retain it under the merchant's privacy and legal requirements.

Use the packet builder on selected local records; it must label missing evidence. A copied public file or successful download by an agent is not buyer delivery. Only relevant factual records belong in the issuer response. Keep customer data out of public links. Issuers need self-contained readable evidence, not a link to GitHub, an external video or a social-media argument.

## Incident response

1. Inspect the event summary promptly when an operator runs it or a private host invokes it. Confirm account/environment and data coverage. Inspect the actual earliest deadline before any percentage.
2. Investigate anomalous payment patterns and fraud warnings using transaction facts. A critic's political or personal disagreement is not evidence of payment fraud.
3. For uncaptured authorizations, decide whether to cancel before expiry or capture after appropriate review. For captured payments, assess warranted refunds before escalation. Fulfill valid orders and preserve customer rights.
4. Once a dispute is open, use its provider workflow. Do not send an unrelated second credit that can double-refund the customer. Partial refunds do not eliminate the remaining dispute exposure.
5. Prepare the reason-specific packet, review facts, and submit through the private provider surface before its actual deadline. Track the resulting status. Wins recover funds but still count toward dispute monitoring.
6. If risk escalates, the operator can tighten payment screening or control new payment acceptance independently of public Commons access. Contact the processor with concrete transaction evidence and a remediation plan when warranted. No such contact is automated here.

Retain liquidity for refunds, gross payment reversals, provider fees, unfinished work and infrastructure. Payouts are not irrevocable profit. Moving funds does not erase obligations, negative balances or reserves. Keep essential infrastructure funded independently of new sales.

## Pricing

`host/chargeback_pricing.py quote` computes a price required to preserve an explicit baseline contribution under supplied loss/refund assumptions. `stress` computes gross reversal liquidity and remaining contribution for a specified number of disputed orders. The output labels assumptions and unobserved account data. Fees default to an illustrative US domestic-card tariff and must be replaced if the merchant's tariff differs.

For the quote model, all disputes are lost and manually countered, and all orders incur the supplied delivery cost. Refund and lost-dispute fractions are disjoint. With price P, processing fraction a, refund fraction r, loss fraction q, fixed fee b, fulfillment cost C, extra overhead E, received fee F, countered fee K and labor L:

`net = P*(1-a-r-q) - b - C - E - q*(F+K+L)`

Add supplied refund-handling cost separately. This is expected contribution economics. It does not estimate a processor's monitoring ratio. Higher price cannot cure excessive dispute counts. Do not create artificial sales, buy from yourself or rotate accounts to disguise activity.

## Live activation

Deploy code into a private backend and provide durable encrypted storage with private backups. Configure a verified Stripe event endpoint or invoke `ingest` from an existing endpoint immediately on delivery. Pass the exact raw body and Stripe-Signature header. Register the event types described in README and keep live/test data separate. A disconnected CLI is not an active monitor.

Resolve merchant account, jurisdiction, actual fees, Radar settings, capture flow, refund/terms text, subscriptions and volume before changing live checkout. Inspect current account data to establish completeness; the tools cannot infer it from public product pages.

## Primary references

- [Stripe measuring disputes](https://docs.stripe.com/disputes/measuring)
- [Stripe 3DS flow and limits](https://docs.stripe.com/payments/3d-secure/authentication-flow)
- [Stripe transaction reviews](https://docs.stripe.com/radar/transaction-reviews)
- [Stripe dispute prevention practices](https://docs.stripe.com/disputes/prevention/best-practices)
- [Stripe dispute prevention programs](https://docs.stripe.com/disputes/get-started/prevention)
- [Stripe responding to disputes](https://docs.stripe.com/disputes/responding)
- [Stripe refunds](https://docs.stripe.com/refunds)
- [Stripe bank transfers](https://docs.stripe.com/payments/bank-transfers)
- [Stripe US standard pricing](https://stripe.com/pricing)
- [Stripe webhook handling](https://docs.stripe.com/webhooks)
