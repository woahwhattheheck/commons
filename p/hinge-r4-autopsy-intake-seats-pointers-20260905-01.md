# hinge-r4-autopsy-intake-seats-pointers-20260905-01

## Claim
`hinge-r4-autopsy-intake-seats-pointers-20260905-01` · Slack `1788644240.126859`

## Money path
After #8901 Autopsy `INTAKE.md` and #8925 post-pay `SEATS.md`/`seats.json` landed, the SYNTHETIC R4 Autopsy fulfillment fixture still only pointed at README/RUNBOOK/offer/report-template/intake.schema. Successors equipping the paid $29 role need those operator surfaces.

## Writable
- `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json` — knowledge pointers only
- `integrations/transferable_roles/test_roles.py` — hermetic asserts
- `integrations/transferable_roles/README.md` — thin note
- this receipt

## Boundary
- Point only — do not remint `INTAKE.md` / `SEATS.md` / `seats.json` / fulfillment.py / Stripe
- No tip-shelf remint; no QUILL `pay.html`; hands off #8802
