# HINGE R4 import package

- Slice: `hinge-r4-import-package-20260905-01`
- Claim: `#coordination` ts `1788583811.355879`
- Parent: `05f1d3b` (current main at branch cut `-02`; `-01` was stale)

## Gap (measured)

`export_package` produces a portable JSON with stable `role_id` and bound
route fields, but RoleStore had no adopt path — a successor would remint via
`create` and lose the id.

## Change

- `RoleStore.import_package(raw)` — adopt export without reminting `role_id`;
  drop `export_meta`; force `occupant` None; refuse if role_id already exists
- CLI `import --file PATH`
- Hermetic tests: round-trip, refuse existing, CLI import
- README documents import after export

## Not touched

shared_equipment, grokbot_control, LotLens. No remint. Roles confer no
credential access (owner policy).
