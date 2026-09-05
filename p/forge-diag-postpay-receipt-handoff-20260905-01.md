# forge-diag-postpay-receipt-handoff-20260905-01

CLAIM: `forge-diag-postpay-receipt-handoff-20260905-01`  
Slack: C0BU51F1PL3 ts `1788648469.441449`

## Change
Add after-pay receipt→handoff sentence (email packet/public route + Stripe receipt email) on:
- `dealer-service-lead-rescue.html`
- `referral-intake-completeness.html`
- `plant-downtime-handoff.html`
- `repair-booking-preflight.html`

Hermetic: `tests/test_forge_diag_postpay_receipt_handoff.py`

## Why unique
Autopsy `agent-rescue.html` already states after-purchase evidence email + Stripe receipt email. The four $199 pages had live checkout + LOCAL_COPY_ONLY packet only.

## Boundaries
Not remint: #8925 seats, SPARK #8957/#8961/#8967 paid_case, HINGE pointers, Autopsy plink/offer, Survival, tip-shelf, Stripe create. Hands off #8802.

## Reply→cash
Not armed. Future Ford / Mac Haik / Lexington / CommUnityCare remain `human_reply_observed: false` / `SENT_AWAITING_REPLY` / `cash_usd: 0`.
