# hinge-r4-open-obligations-cash-marker-20260905-01

CLAIM Slack `1788651674.052769` (`#coordination` / C0BU51F1PL3).

## What
`RoleStore.list_open_obligations` stamps `payment_capability: true` on open
rows when the role has access_route name `payment_capability`. CRM rows omit
it. Hermetic mixed-store prove in `test_roles.py`.

## Boundary
Not remint #8979/#8980/#8982/#8988. Hands off #8802.
