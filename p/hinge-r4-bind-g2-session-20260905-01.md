# HINGE R4 bind G2 session onto access_route

- Slice: `hinge-r4-bind-g2-session-20260905-01`
- Claim: `#coordination` ts `1788580359.827399`
- Parent: R4 + G2 align + CLI seat (`744d315`)

## Gap (measured)

`kind: grokbot_control` routes are meant to carry durable `session_id` /
`last_run_id` for successor recover. RoleStore had no stamp mechanism —
only hand-edited JSON.

## Change

- `RoleStore.bind_access_route(route_name, session_id=, last_run_id=, pool_id=)`
- CLI `bind-route`
- Export keeps route session fields; clears occupant only
- Occupant seat never copied onto the route by this path

## Not touched

`integrations/grokbot_control/*`, shared_equipment, peer lanes. No remint.
