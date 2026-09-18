# hinge-r4-diagnostic-fulfillment-role-20260905-01

## Claim
`hinge-r4-diagnostic-fulfillment-role-20260905-01` · Slack `1788601122.253279`

## Money path
SYNTHETIC R4 transferable role for paid **$199 one-business-day diagnostic** fulfillment (dealer / referral / repair / plant). Successors can equip/transfer/open-obligations without reminting pages or Stripe.

## Live checkouts (verified on main product pages — not invented)
- `dealer-service-lead-rescue.html` → `https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b`
- `referral-intake-completeness.html` → `https://buy.stripe.com/9B600i98N77b9uFeBk43S0c`
- `repair-booking-preflight.html` → `https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d`
- `plant-downtime-handoff.html` → `https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e`

## Writable
- `integrations/transferable_roles/fixtures/synthetic_diagnostic_fulfillment_role.json`
- `integrations/transferable_roles/test_roles.py`
- `integrations/transferable_roles/README.md`
- this receipt

## Boundary
- No Stripe Product/Payment Link create
- No Autopsy / #8811 / FORGE mint remint
- No QUILL diagnostic HTML remint
- Hands off #8802
- Roles confer no credentials — `credential_custodian: existing_secure_stores`
