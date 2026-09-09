# tenon-r4-equipment-bind-unbind-route-cards-20260906-01

CLAIM Slack `1788667110.503369` (`#coordination` / C0BU51F1PL3).

## Mechanism

`bind_access_route_card` / `unbind_access_route_card` — import-only
`RoleStore.bind_access_route` / `unbind_access_route`. Temp store; returns
updated role. Does not remint `roles.py`.

## Boundary

Not remint #9280 transfer, #9276 equip/release, export/import leftovers,
HINGE prove, WEDGE, RIVET, Stripe, #8802. Not proof-only (#9270).
