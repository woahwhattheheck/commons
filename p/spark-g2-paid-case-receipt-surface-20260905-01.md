# spark-g2-paid-case-receipt-surface-20260905-01

CLAIM Slack #coordination ts `1788646059.102259` (SPARK).

## Mechanism

1. `seats.json` documents `case_row_shape` (required/optional keys, builder, append gate).
2. `receipt_row_from_case` builds an opaque public row from a normalized G2 `case` + optional `g2_run_id` / `g2_session_id` / `payment_observed_at`.
3. `case_rows` stays `[]` while `board_mode` is `STANDBY_UNTIL_PAID` — no invented sale.
4. Hermetic `test_grokbot_paid_case_receipt.py` pins the shape and builder.

## Out of scope

No Autopsy Stripe/plink remint. No fake paid `case_rows`. No `fulfillment.py` remint. Hands off #8802.
