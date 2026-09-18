# HINGE R4 unbind access route

- Slice: `hinge-r4-unbind-route-20260905-01`
- Claim: `#coordination` ts `1788596633.015019`
- Parent: `f5a44c8d34f0e81b3bb9f48c05ad02fd38e7e299` (main tip at branch cut)

## Gap (measured)

`bind_access_route` / CLI `bind-route` stamp durable G2 `session_id` /
`last_run_id` onto a named `access_route`, but there was no clear path to
remove those recover stamps without rewriting the whole route or wiping the
fixture `pool_id`.

## Change

- `RoleStore.unbind_access_route` — clear stamped bindable fields; keep route
  shell (name/kind/urls); do not touch occupant, purpose, or obligations
- `DEFAULT_UNBIND_FIELDS = ("session_id", "last_run_id")` so default unbind
  leaves fixture `pool_id=grokbot`; optional `fields=` may include `pool_id`
  from `BINDABLE_ROUTE_FIELDS`
- CLI `unbind-route` (`--route` required; optional `--fields` comma-separated)
- Hermetic tests: bind then default unbind keeps pool; unknown route fails;
  CLI round-trip
- README documents `unbind-route` after `bind-route`

## Not touched

shared_equipment, grokbot_control. No remint. Roles confer no credential
access (owner policy). Do not merge from this receipt alone.
