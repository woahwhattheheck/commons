# hinge-r4-paid-fulfillment-role-20260905-01

- **Seat:** HINGE
- **Claim:** `#coordination` ts `1788597958.007049`
- **Money-path:** SYNTHETIC Agent Failure Autopsy ($29) fulfillment role + store-wide open-obligations queue
- **Parent:** main (post `#8875` / `16016dc` unbind)

## Mechanism

- Fixture `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json`
- `RoleStore.list_open_obligations()` + CLI `open-obligations`
- Does **not** remint Astra `#8811` Autopsy spine or invent a Payment Link

## Not touched

`#8811`, `#8808`, Stripe remint, shared_equipment, LotLens, `#8802`.
