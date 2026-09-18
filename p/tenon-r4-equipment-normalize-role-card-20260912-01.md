# tenon-r4-equipment-normalize-role-card-20260912-01

CLAIM Slack `1789198160.505099` (`#coordination` / C0BU51F1PL3).

## Mechanism

`normalize_role_card` — import-only `roles.normalize_role` (in-memory; no RoleStore write).
Scrubs secret-shaped keys and stamps schema. Does not remint create/inspect/get/list.

## Boundary

Not remint HINGE create/list/get/prove, WEDGE cash, Stripe, #8802.
