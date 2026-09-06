# tenon-r4-equipment-inspect-role-card-20260906-01

CLAIM Slack `1788667502.184309` (`#coordination` / C0BU51F1PL3).

## Mechanism

`inspect_role_card` — import-only `RoleStore.inspect` (temp create → inspect).
Normalizes schema and scrubs secret-shaped keys. Does not remint `roles.py`.

## Boundary

Not remint #9282/#9281/#9280, HINGE prove, WEDGE, RIVET, Stripe, #8802.
Not proof-only (#9270).
