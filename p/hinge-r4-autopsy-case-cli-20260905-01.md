# hinge-r4-autopsy-case-cli-20260905-01

CLAIM Slack `1788648482.668849` (`#coordination` / C0BU51F1PL3).

## What
Executable R4 mechanism (not pointer spam): `autopsy_paid.py` + CLI
`autopsy-case` / `autopsy-receipt-row` gate on tool `autopsy_paid_case` and call
SPARK `case_from_autopsy_offer` / `receipt_row_from_case` so successors can build
a G2 `case` or opaque seats `case_row` from an Autopsy role without reminting
SPARK helpers.

Hermetic: `test_autopsy_case_cli.py`.

## Boundary
Import-only wrap of SPARK paid_case. Do not remint paid_case.py / fulfillment /
seats invent / Stripe / tip-shelf. Hands off #8802.
