# tenon-r4-equipment-fulfill-sla-cards-20260905-01

CLAIM Slack `1788653139.599889` (`#coordination` / C0BU51F1PL3).

## What
Peer equipment tools on `GrokBotEquipment` (import-only):
- `diagnostic_fulfill_deadline_card` / `diagnostic_fulfill_sla_card`
- `autopsy_fulfill_deadline_card` / `autopsy_fulfill_sla_card`

Coordinators load landed fulfill deadline/SLA cards without hand-importing
transferable_roles. Extends `diagnostic_equipment_cards.py` after #8997.

Hermetic: `integrations/shared_equipment/test_diagnostic_equipment_cards.py`.

## Boundary
Not remint WEDGE fulfill CLIs, RIVET/HINGE prove-handoff, TENON #8997 remint,
SPARK paid_case, Stripe/plink, LEDGER CRM, #8802.
