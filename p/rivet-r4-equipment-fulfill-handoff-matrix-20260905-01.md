# rivet-r4-equipment-fulfill-handoff-matrix-20260905-01

CLAIM Slack `1788654711.050439` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Complete #9008 missing fulfill/SLA handoff cells:
- diagnostic fulfill after export→import→equip
- autopsy fulfill after release→equip

Extends `integrations/shared_equipment/test_diagnostic_equipment_cards.py` only
(reuse `_assert_diag_fulfill_cards` / `_assert_autopsy_fulfill_cards`).

## Boundary
No remint TENON card impl / #9008 helpers. Hands off #8802.
