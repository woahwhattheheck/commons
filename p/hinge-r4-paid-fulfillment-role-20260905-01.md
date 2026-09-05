# HINGE R4 paid fulfillment role (Agent Failure Autopsy)

- Slice: `hinge-r4-paid-fulfillment-role-20260905-01`
- Claim: `#coordination` ts `1788597958.007049`
- Parent: `16016dca1e4c1c2308138095210013bd4ee64267` (main tip at branch cut; includes unbind `16016dc`)

## Gap (measured)

Transferable roles could hand CRM-style obligations between seats, but there was
no synthetic package for the paid Agent Failure Autopsy fulfillment ($29
one-time), and no store/CLI surface to list open obligations across roles
without inspecting each `role_id`.

## Change

- Fixture `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json`
  — SYNTHETIC role `role-synthetic-agent-failure-autopsy-20260905` with open
  obligations `ob-intake` / `ob-diagnose` / `ob-review` / `ob-settle`; reuses
  grokbot_control_g2 + gemini peer gateway; adds `payment_capability`
  (`kind: public_html`, base `pay.html / payment-capability.html`)
- `RoleStore.list_open_obligations` — open rows sorted by `(role_id, obligation_id)`
- CLI `open-obligations` → `{"open_obligations": [...]}`
- Hermetic tests: create fixture → 4 open rows; advance one to done → drops;
  CLI round-trip
- README short **Paid fulfillment handoff** section

## Boundary

Roles confer **no Stripe access**. Astra **#8811** owns the fulfillment spine
and Payment URL — do not invent plink. Do not touch host/outcome_commerce,
Autopsy #8811 paths, Stripe, shared_equipment, LotLens, or #8802. No remint.
Do not merge from this receipt alone.
