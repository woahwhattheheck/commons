# Hosted processor handoff

This is the stopping boundary for public Commons work. **Never paste or relay
bank account, routing, card, tax-ID, identity-document, credential, or payout
destination values through Commons, Slack, GitHub, prompts, logs, or
receipts.**

## Public manual-capture checkout

The owner explicitly approved one bounded public checkout for the existing
Same-Day Agent Survival Proof after the authorization/capture boundary was
reviewed. Live OAuth readback at `2026-08-30T06:54:21Z` proved:

- active Payment Link `plink_1UA2ZuATH4EDE7XDZUJ9wx1k` at
  <https://buy.stripe.com/8x25kC3Ot9fj5ep1Oy43S0a>;
- active Product `prod_VANEgGPRVMVZLJ` and active one-time USD `250000`
  Price `price_1UA2UMATH4EDE7XDGuL1POjW`;
- `capture_method=manual`, dynamic payment methods, and
  `customer_creation=always`;
- required `failure_sentence`, optional `public_link`, and a completed-session
  restriction of `count=0`, `limit=1`;
- account `charges_enabled=true` and `payouts_enabled=true`.

Completing checkout asks Stripe to create the customer and place the USD 2,500
authorization. Bernays then confirms the binary scope, exclusions, refund
choice, and exact one-business-day window in writing. Capture occurs only after
the buyer accepts those terms. A bad-fit or unaccepted scope cancels the
authorization. One completed checkout consumes the link's one-buyer capacity;
do not reactivate it or mint a duplicate while that buyer is being resolved.

Hosted invoices remain an alternate customer-specific route for later accepted
quotes; none is created or implied by this public link:

<https://dashboard.stripe.com/invoices>

The hosted provider decides which verification fields are required. Commons
never mirrors card, bank, identity, tax, credential, or private event-payload
values. Payout destinations stay inside Stripe's official hosted settings.

<https://dashboard.stripe.com/account/payouts>

Enter the payout destination there only.

## Fallback

If Stripe is unavailable, use the official PayPal Wallet surface:

<https://www.paypal.com/myaccount/money/>

The same boundary applies: connect the withdrawal destination inside the
provider surface only. Do not publish a reusable payment address or private
remittance instructions.

## Receipt truth

The public Payment Link, Product, and Price identifiers may be recorded because
they are public catalog and checkout references. A future buyer-specific receipt
may add only an opaque provider reference plus a SHA-256 of the private provider
event payload. That records a reference; it does not independently prove legal
acceptance, capture, delivery, settlement, payout, or bank availability.

`AUTHORIZATION != CAPTURE != SETTLEMENT != PAYOUT != BANK_AVAILABLE`.

Current state:

- buyer: **UNKNOWN**
- accepted quote: **NOT_LANDED**
- checkout completions: **0 / 1**
- no authorization has landed
- capture: **NOT_LANDED**
- delivery: **NOT_LANDED**
- processor payment: **NOT_LANDED**
- bank available: **NOT_LANDED**
- collected cash: **USD 0**
