# rivet-r4-handoff-prove-diag-sla-diagnostic-usd-20260905-01

CLAIM Slack `1788657850.208299` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Hermetic pin `diagnostic_usd == 199` (+ refund text mentions 199) on
`diagnostic-fulfill-sla` after handoff — mirror WEDGE autopsy `amount_usd` pin.
Core already returns the field; tests only.

Extends `integrations/transferable_roles/test_handoff_execute_survive.py`
(transfer / export→import / release→equip).

## Boundary
Leave WEDGE #9136 alone. No remint prove core / equipment / cash. Hands off #8802.
