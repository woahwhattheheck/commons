# hinge-r4-autopsy-intake-seats-test-pins-20260905-01

CLAIM Slack `1788644661.307189`. Parent #8955 squash `a94f338f` landed fixture pointers but missed hermetic test pins that were on branch tip after merge.

## What
- `integrations/transferable_roles/test_autopsy_intake_seats_pointers.py` — hermetic asserts for INTAKE.md / SEATS.md / seats.json
- (optional companion) pins in `test_roles.py` if also present on tip

## Boundary
Test only. No Autopsy spine remint. Hands off #8802.
