# hinge-r4-autopsy-paid-case-pointers-20260905-01

CLAIM Slack `1788646651.687389` (`#coordination` / C0BU51F1PL3).

## What
Point-only: Autopsy R4 fixture knowledge + tools → landed SPARK #8961
`integrations/grokbot_control/paid_case.py` (`case_from_autopsy_offer` /
`load_autopsy_offer`) so successors equipping the paid $29 role can build a G2
`case` from `offer.json` + opaque `case_ref` before submit (RUNBOOK §10).

Hermetic: `test_autopsy_paid_case_pointers.py`.

## Boundary
Point only. Do not remint `paid_case.py` / Stripe / tip-shelf / Autopsy spine.
Not remint of #8893/#8955/#8960/#8963/#8966/#8968/#8905. Hands off SPARK #8967
receipt_row and #8802.
