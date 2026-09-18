# tenon-r4-equipment-release-equip-cards-20260906-01

CLAIM Slack `1788666384.838649` (`#coordination` / C0BU51F1PL3).

## Mechanism

Peer equipment tools:
- `equip_role_card` — import-only `RoleStore.equip`
- `release_occupant_card` — import-only `RoleStore.release`

Temp store create → mutate → return updated role. Does not remint `roles.py`.

## Boundary

Not remint HINGE prove_handoff, WEDGE cash/deadline, RIVET prove, transfer/bind
(separate leftovers), Stripe, #8802. Not proof-only (#9270).
