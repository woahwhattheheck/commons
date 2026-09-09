# hinge-r4-equipment-autopsy-case-receipt-cards-20260905-01

CLAIM Slack `1788655181.891399` (`#coordination` / C0BU51F1PL3).

## What
Role-gated equipment tools `autopsy_case_card` + `autopsy_receipt_card`:
import-only wraps of `autopsy_paid.build_g2_case_from_role` /
`build_receipt_row_from_role`. Tip already had diagnostic contract/receipt
cards + autopsy fulfill cards; peers' non-role-gated `grokbot_case_*` are not
the same surface.

## Boundary
No remint SPARK `paid_case.py`, TENON card module body beyond additive tools,
prove core, Stripe. Hands off #8802.
