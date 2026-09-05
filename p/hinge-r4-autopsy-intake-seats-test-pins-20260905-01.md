# hinge-r4-autopsy-intake-seats-test-pins-20260905-01

## Claim
`hinge-r4-autopsy-intake-seats-test-pins-20260905-01` · Slack `1788644661.307189`

## Why
Parent #8955 squash `a94f338f` landed Autopsy R4 fixture knowledge → INTAKE/SEATS.
Hermetic asserts landed on the branch tip ~29s after squash and missed main.

## Writable
- `integrations/transferable_roles/test_roles.py` — `SPINE_INTAKE` / `SPINE_SEATS` / `SPINE_SEATS_JSON` pins only
- this receipt

## Boundary
- No fixture/README remint
- No Autopsy package / tip-shelf / Stripe remint
- Hands off #8802
