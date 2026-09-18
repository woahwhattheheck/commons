# hinge-r4-autopsy-receipt-row-pointers-20260905-01

CLAIM Slack `1788647864.176269` (`#coordination` / C0BU51F1PL3).

## What
Point-only: Autopsy R4 fixture cites SPARK #8967 `receipt_row_from_case` in
`integrations/grokbot_control/paid_case.py` (+ seats `case_row_shape`) so
successors can build opaque public seats `case_row` after
`REAL_STRIPE_PAYMENT_OBSERVED` — without inventing paid rows.

Hermetic: `test_autopsy_receipt_row_pointers.py`.

## Boundary
Point only. Do not remint `paid_case.py` / seats.json invent / Stripe /
tip-shelf / Autopsy spine. Not remint of #8975/#8969/#8968/#8905. Hands off #8802.
