# forge-autopsy-postpay-receipt-handoff-20260906-01

## Claim
CLAIM `forge-autopsy-postpay-receipt-handoff-20260906-01` · Slack `1788668181.451679`

## What
`agent-rescue.html` gains the same post-purchase receipt→handoff pin the four
$199 diagnostic pages got in #8981: `data-postpay-handoff="1"`, mailto to
`tokenjunkielabs@gmail.com`, Stripe receipt cite, clock-start sentence.

Autopsy Stripe plink stays byte-identical:
`https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g`

Hermetic: `tests/test_forge_autopsy_postpay_receipt_handoff.py`.

## Paths
- `agent-rescue.html`
- `tests/test_forge_autopsy_postpay_receipt_handoff.py`
- this receipt

## Boundary
Hands off #8802. No remint Autopsy plink / offer.json / tip-shelf / Survival /
second CRM. Do not invent VERIFIED_HUMAN_YES.
