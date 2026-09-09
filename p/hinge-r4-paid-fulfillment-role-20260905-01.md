# HINGE R4 paid fulfillment role (Agent Failure Autopsy)

- Slice: `hinge-r4-paid-fulfillment-role-20260905-01`
- Claim: `#coordination` ts `1788597958.007049`
- Parent: `3756cbb61e179ab4e7ca804455c1f594e060da3e` (current main at finish-ship)

## Gap (measured)

Transferable roles could hand CRM-style obligations between seats, but there was
no synthetic package for the paid Agent Failure Autopsy fulfillment ($29
one-time), and no store/CLI surface to list open obligations across roles
without inspecting each `role_id`.

Prior attempt stamped the claim and pushed fixture+receipt only — no
`list_open_obligations`, CLI, tests, or README, and no PR.

## Change

- Fixture `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json`
  — SYNTHETIC role `role-synthetic-agent-failure-autopsy-20260905` with open
  obligations `ob-intake` / `ob-diagnose` / `ob-review` / `ob-settle`; reuses
  grokbot_control_g2 + gemini peer gateway (CRM shapes); adds `payment_capability`
  (`kind: public_html` → payment-capability.html / pay.html)
- `RoleStore.list_open_obligations()` — scan all roles; open rows as dicts
  `{role_id, label?, purpose, obligation_id, summary, next_action,
  evidence_pointer?, synthetic?}` sorted by `(role_id, obligation_id)`
- CLI `open-obligations` → `{"open_obligations": [...]}`
- Hermetic tests: create fixture → 4 open rows; advance one to done → drops;
  CLI round-trip
- README short **Paid fulfillment handoff** section

## Boundary

Roles confer **no Stripe access**. Astra **#8811** owns the fulfillment spine
and Payment URL — do not invent plink. Hands off **#8811** **#8808** **#8802**
shared_equipment LotLens Stripe. No remint. Do not merge from this receipt alone.
