# HINGE R4 autopsy checkout wire

- Slice: `hinge-r4-autopsy-checkout-wire-20260905-01`
- Claim: `#coordination` ts `1788600635.950329`
- Parent: `102182e3d733341d95fe2bab99695ea88ae0290b` (main tip at branch create)

## Gap (measured)

#8883 landed the SYNTHETIC paid Autopsy fulfillment role; #8889 put the live
$29 checkout CTA on `agent-rescue.html`
(`https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g`). The R4 fixture still said
Payment URL pending / do-not-invent-plink with no public link stamp — successors
could not see the real public checkout from the role package.

## Change

- Fixture `integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json`
  — knowledge pointer `agent-rescue.html`; `payment_capability.base_url` =
  public Payment Link only (no secret IDs); note → UTM-safe CTA on
  `agent-rescue.html`; `ob-settle` summary/next_action/evidence_pointer mark
  checkout LIVE; `synthetic_note` clarifies SYNTHETIC role + real public link
- Hermetic `test_autopsy_fixture_wires_live_checkout_url` — create from fixture;
  assert knowledge / access_routes / ob-settle carry
  `buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g` and `agent-rescue.html`
- README Paid fulfillment: live checkout URL now on fixture + `agent-rescue.html` (#8889)

## Boundary

Copies the **existing** #8889 public CTA — does **not** mint a second plink.
Hands off **#8811** spine, **agent-rescue.html**, Stripe mint, **#8802**.
No remint. Do not merge from this receipt alone.
