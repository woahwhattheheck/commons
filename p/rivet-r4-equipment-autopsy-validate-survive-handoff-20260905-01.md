# rivet-r4-equipment-autopsy-validate-survive-handoff-20260905-01

CLAIM Slack `1788657094.001229` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Complete #9030 missing autopsy validate handoff cells:
- autopsy_fulfill_validate_card after export→import→equip
- autopsy_fulfill_validate_card after release→equip

Extends `integrations/shared_equipment/test_diagnostic_equipment_cards.py` only
(reuse `_assert_autopsy_fulfill_validate_card`).

## Boundary
No remint card impl / cash card / case-receipt. Hands off #8802.
