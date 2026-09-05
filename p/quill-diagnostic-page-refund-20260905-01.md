# QUILL: surface refund sentence on four $199 diagnostic pages

- Slice / CLAIM: `quill-diagnostic-page-refund-20260905-01`
- Branch: `quill/diagnostic-page-refund-20260905-01` (cut from main `@ 9591969`)
- Parent tip at cut: `9591969`

## Exact sentence (verbatim on all four pages)

If the accepted diagnostic is not delivered inside the one-business-day window, the paid diagnostic amount is refunded unless the buyer elects in writing to receive one free next-business-day repair instead.

## Paths

- `dealer-service-lead-rescue.html` — Miss remedy after pricebar `</section>`, before `.bound`
- `plant-downtime-handoff.html` — same placement
- `referral-intake-completeness.html` — same placement
- `repair-booking-preflight.html` — Miss remedy in the $199 offer card after Stripe checkout note
- `test_diagnostic_page_refund.py` — asserts `Miss remedy` + refund substring on all four

## Explicit non-touch

- No Stripe mint / no Payment Link changes
- Hands off `#8802`
- Do not touch catalog, G2 / R4 / T8 / D5

## Ship

Open PR → ship+merge / squash when open-door green.
