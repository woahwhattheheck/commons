# HINGE R4 import package

- Slice: `hinge-r4-import-package-20260905-01` (clean ship on `hinge/r4-import-package-20260905-02`)
- Claim: `#coordination` ts `1788583811.355879`
- Parent: `05f1d3b` (current main tip at clean rebuild)

## Gap (measured)

`export_package` produces a portable JSON with stable `role_id` and bound
route fields, but RoleStore had no adopt path — a successor would remint via
`create` and lose the id.

## Change

- `RoleStore.import_package(raw)` — scrub via normalize; require `role_id`;
  refuse if `_path(role_id).exists()`; drop `export_meta`; force `occupant`
  None; keep purpose, obligations, tools, bound access_routes
- CLI `import --file PATH`
- Hermetic tests: export→import round-trip, conflict RoleError, CLI round-trip

## Not touched

shared_equipment keyring, grokbot_control, LotLens. No remint. Roles confer no
credential access (owner policy).
