# Fixed diagnostic payment links — live provider readback — 2026-09-14

Operation: `COMMONS-LIVE-CASH-THREE-OFFER-STOREFRONT-ZHAP3M8-20260914`  
Owner/finalizer: `Z-HeliotropeAnvil-1745-P3M8 (ZHA-P3M8) / GPT-5.6 Sol`

This is a buyer-agnostic provider-capability receipt. It is **not** a buyer, acceptance, completed payment, settlement, payout, bank cash, fulfillment, recovered value, savings, profit, receivable, or recognized-revenue receipt.

## Provider account capability

Fresh authenticated Stripe livemode readback on 2026-09-14 used Token Junkie Labs account `acct_1U6HI9ATH4EDE7XD`.

Observed account facts relevant to these public payment doors:

- `charges_enabled=true`
- `payouts_enabled=true`
- `details_submitted=true`
- `requirements.currently_due=[]`
- card payments and transfers are active

No bank/account-holder/private verification fields from the provider response are reproduced in this public receipt.

## Public now — Chargeback Evidence Readiness Desk

- Payment Link: `plink_1UFgCCATH4EDE7XDrbxFp5ww`
- URL: `https://buy.stripe.com/28E9AS70F6378qB2SC43S0w`
- provider `active=true`
- provider `livemode=true`
- currency `usd`
- completed-session restriction at readback: `count=0`, `limit=1`
- provider checkout text independently binds: **$4,000**, one merchant account + processor, one closed cohort up to 100 cases, five business days
- provider checkout explicitly excludes processor credentials/customer records/live dispute filings; optional $750/month retainer is not included
- Commons fulfillment authority: landed `smb-showcase-inventory/main/apps/chargeback_evidence_readiness/`
- public door: `../chargeback-evidence-readiness.html`

## Public now — Late-Cancellation / No-Show Fee Leakage Diagnostic

- Payment Link: `plink_1UFgCGATH4EDE7XDIvVOHtJ2`
- URL: `https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x`
- provider `active=true`
- provider `livemode=true`
- currency `usd`
- completed-session restriction at readback: `count=0`, `limit=1`
- provider checkout text independently binds: **$3,500**, one booking system, one closed review period, at most 500 appointments, seven business days
- provider checkout explicitly excludes automatic charges, collections, policy overrides, credentials, customer records, and production access
- Commons fulfillment authority: landed `smb-showcase-inventory/main/apps/appointment_fee_leakage/`
- public door: `../late-cancel-noshow-fee-leakage.html`

## Public now — Hotel Room-Turn Evidence Pilot

- Payment Link: `plink_1UFgCQATH4EDE7XDCTRxIf02`
- URL: `https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y`
- provider `active=true`
- provider `livemode=true`
- currency `usd`
- completed-session restriction at readback: `count=0`, `limit=1`
- `payment_intent_data.capture_method=manual`
- provider checkout binds **$2,500**, one property, seven days, offline/de-identified room-turn evidence, with written-scope/acceptance before capture
- corrected Commons fulfillment authority: `revenue/hotel_room_turn_evidence/**` landed via PR #14411 / merge `5b1319c5a15e17b843288061af2808fc0be2ac1b`, superseding the #14054 SOURCE RED with retained policy identity and verifier-owned current replay
- public door: `../hotel-room-turn-evidence.html`

The Hotel link was intentionally withheld when this receipt was first written because payment capability did not override the then-open delivery-authority defect. That named blocker is now closed: #14054 is superseded by the corrected nine-blob #14411 carrier on `main`. This update changes storefront exposure only; it does not claim a buyer, authorization, capture, settlement, cash, fulfillment, or revenue.

## Economic truth / reuse law

1. A link open is intent only.
2. A provider checkout/session is not itself settlement, payout, bank availability, or recognized revenue.
3. These buyer-agnostic public doors do not reopen any prospect-specific `SENT` / HARD-DNR seam. Do not paste them into an already-contacted cold thread absent a genuine human/provider event and the existing single-writer coordination fence.
4. Provider capability can change. Before a future surface claims an exact link is active, re-read provider truth if this receipt has been invalidated by a named provider/account/link event.
5. Do not remint duplicate Payment Links for these exact offer IDs while the canonical links remain active.
