# HINGE R4 autopsy spine pointers

- Slice: `hinge-r4-autopsy-spine-pointers-20260905-01`
- Claim: `#coordination` ts `1788604782.481049`
- Parent: `120f4b9e1ee0177769c0d27e6c6c51c6cc0c0bc4` (main tip at branch create)
- Spine land: `#8811` → `c8e40bc`

## Gap (measured)

#8811 Autopsy spine is on main (`c8e40bc`: README, RUNBOOK, offer.json,
report-template, fulfillment.py, schemas). The SYNTHETIC R4 fulfillment fixture
still only pointed at `agent-rescue.html` / #8889 live CTA and a coordination
note that "#8811 owns fulfillment spine" — successors lacked knowledge/tools
into the landed paths.

## Change

- Fixture `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json`
  — `synthetic_note` / coordination knowledge: #8811 spine **LANDED** on main
  (`c8e40bc`); knowledge pointers to
  `revenue/agent_failure_autopsy/{README.md,RUNBOOK.md,offer.json,report-template.md,intake.schema.json}`
  (`offer.json` labeled ACTIVE_VERIFIED / payment_url LIVE_VERIFIED — do not
  remint IDs here); tool `autopsy_fulfillment` →
  `python3 revenue/agent_failure_autopsy/fulfillment.py`; keep `agent-rescue.html`
  + live `buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g` on `payment_capability`
- Hermetic tests — assert knowledge includes `RUNBOOK.md` + `offer.json`; tools
  include `autopsy_fulfillment` entry; no `prod_`/`price_`/`acct_`/`plink_` in
  fixture blob
- README Paid fulfillment — note spine pointers after #8811 land

## Boundary

**Point only** at `revenue/agent_failure_autopsy/*` — do **not** remint
fulfillment.py / schemas / offer.json contents. Do **not** invent plinks; keep
existing live #8889 checkout. Stripe product/price/plink/account IDs stay in
`offer.json` only. Hands off **#8893**, **#8802**, **agent-rescue.html**.
Do not merge from this receipt alone.
