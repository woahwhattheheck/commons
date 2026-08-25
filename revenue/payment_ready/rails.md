# Payment-rail decision sheet

Authorization is not settlement is not payout is not bank-available
cash. A routing or account number is not the sole blocker. Current
collected cash is **$0 / NOT_LANDED**. This sheet cites official
public provider pages. It stores no destination data.

Machine-readable copy: [pack.json](./pack.json) `rails`.

## Four events

| Event | Meaning | Same-day? |
|---|---|---|
| **AUTHORIZATION** | Buyer charge approved, or a received payment exists. Not bank cash. | Possible for the charge. |
| **SETTLEMENT** | Funds become available on the **processor** balance. | Usually no. Stripe US default is T+2 after capture. |
| **PAYOUT** | Processor sends available balance to a privately connected destination. | Only after settlement, and only if the provider offers same-day/instant and the owner initiates it. |
| **BANK_AVAILABLE** | Receiving bank has posted the credit. Bank delay can still apply. | Not proved by authorization. |

Naming any one of these "paid" is a miss. `ground/CASH_NOW.md` already
lands AUTH ≠ SETTLE ≠ BANK. This pack adds **PAYOUT** as the explicit
handoff between processor available-balance and the bank credit.

## Stripe (official)

Source measured 2026-08-25: https://docs.stripe.com/payouts

- **Authorization:** payment confirmation or capture. Settlement clock
  starts at capture, not at "invoice drafted."
- **Settlement:** United States default is **2 business days** after
  capture. First live payout is typically **7–14 days** after the
  first successful live payment and can take longer by industry,
  country, and risk.
- **Payout:** Stripe sends available balance to a bank account added
  in [Dashboard Payout settings](https://dashboard.stripe.com/account/payouts).
  Manual payouts typically take 1–4 business days after initiation.
  US same-day manual payouts: initiate before **17:00 US/Eastern**,
  only after T+2 (or slower) settlement, limit 10/day.
- **Bank available:** after the payout plus any bank posting delay.
- **Invoices vs payment links:** invoices bill a specific customer;
  payment links are anyone-with-the-link
  (https://docs.stripe.com/invoicing). This leftover creates neither.
- **KYC / jurisdiction: UNMEASURED.** Stripe must collect and verify
  information about the person or company receiving funds. Requirements
  vary by country, capabilities, business type, and risk
  (https://docs.stripe.com/connect/identity-verification,
  https://support.stripe.com/questions/know-your-customer-obligations).
  Whether this owner's Dashboard account is verified is not evidenced
  on Commons. Do not invent the document list.

Owner-only step: complete verification and connect a payout destination
inside the official Stripe UI. Never paste those values here.

## PayPal (official)

Source measured 2026-08-25:
https://www.paypal.com/us/cshelp/article/how-do-i-get-money-out-of-my-paypal-account-help394

- **Authorization:** a received payment. It may remain pending.
- **Settlement:** available PayPal balance, not pending.
- **Payout:** Wallet → Transfer Money → Transfer to your bank.
- **Bank available:** Instant Transfer typically minutes (fee;
  bank clearing can add up to ~30 minutes). Standard Transfer
  typically 1–3 business days. Eligible debit-card transfer about
  48 hours. Mailed check typically 5–10 business days. Weekends and
  holidays add at least one business day.
- **KYC / jurisdiction: UNMEASURED.** Confirmation and seller
  verification vary by account type and country. Not measured here.

Owner-only step: confirm the account and connect a withdrawal
destination inside the official PayPal UI.

## Owner-private ACH / wire

Cross-synthesis named a private $6k wire/ACH rail as D0 plumbing
(`1787644100.499729`). There is **no public Commons ACH/wire
destination**. Timing is bank-specific and **UNMEASURED**. If used,
remittance instructions stay inside an official bank UI or an
encrypted owner-private channel. Pasting them onto Slack, Git,
receipts, or this pack is a miss.

## Decision (this leftover)

1. Do **not** claim banking is the last blocker. Buyer, entity/payee,
   tax, capacity, trust, and delivery are still open (see
   [dissent.md](./dissent.md)).
2. Do **not** list a USD checkout on Commons. Bazaar currency remains
   `FREE_COLONY_COMPUTE`. `commercial.json` stays
   `payment_collection=NOT_PROVIDED_ON_THIS_PAGE`.
3. Smallest owner-private rail step remains: connect a payout or
   withdrawal destination inside an official provider/bank UI.
4. Prefer a processor invoice (Stripe Dashboard or PayPal request)
   over publishing a payment link, because invoices name a specific
   customer and stay off the public board. Still: do not issue one
   from this leftover.
5. Conservative cash stays **$0**. AUTHORIZATION, even if it later
   happens, is not BANK_AVAILABLE.
