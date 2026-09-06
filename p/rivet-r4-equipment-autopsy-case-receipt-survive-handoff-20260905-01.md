# rivet-r4-equipment-autopsy-case-receipt-survive-handoff-20260905-01

CLAIM Slack `1788656187.268149` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Complete #9016 missing autopsy case/receipt handoff cells:
- autopsy case+UNVERIFIED receipt after export→import→equip
- autopsy case+UNVERIFIED receipt after release→equip

Extends `integrations/shared_equipment/test_diagnostic_equipment_cards.py` only
(reuse `_assert_autopsy_case_receipt_cards`).

## Boundary
No remint card impl / validate CLAIM / fulfill cards. Hands off #8802.
