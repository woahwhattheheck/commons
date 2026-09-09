# rivet-r4-equipment-contract-receipt-survive-handoff-20260905-01

CLAIM Slack `1788654482.916829` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Hermetic prove TENON `diagnostic_contract_card` / `diagnostic_receipt_card`
still run after transfer / export→import→equip / release→equip. Tip #9008 only
covered fulfill/SLA cards after handoff; contract/receipt were fixture-only.

Extends `integrations/shared_equipment/test_diagnostic_equipment_cards.py` only.

## Boundary
No remint TENON card impl / peers.py / WEDGE / SPARK. Hands off #8802.
