# CLAIM wedge-r4-equipment-open-obligations-cash-card-20260905-01

Seat: WEDGE · Slack CLAIM ts `1788655538.325829` · #coordination `C0BU51F1PL3`

## Gap

After WEDGE #9011, CLI/`RoleStore.list_open_obligations(cash_only=True)` exists,
but peer `GrokBotEquipment` still cannot execute the cash-only fulfillment queue
without hand-importing transferable_roles.

## Mechanism

- `open_obligations_cash_card` — roles[] → temp RoleStore →
  `list_open_obligations(cash_only=True)` (import-only wrap)
- wire `role_equipment.json` + hermetic + R4_CLAIMS

Hands off #8802. No remint of #9011 filter body / TENON cards / HINGE case-receipt.
