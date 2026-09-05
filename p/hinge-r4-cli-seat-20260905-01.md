# HINGE R4 CLI `--seat` wiring

- Slice: `hinge-r4-cli-seat-20260905-01`
- Claim: `#coordination` ts `1788579120.810299`
- Parent: R4 #8760 / G2 align #8771

## Gap (measured)

`RoleStore.equip` / `transfer` already accept `seat` (occupant ≠ `role_id`).
`cli.py` did not expose `--seat`, so successors could not set G2 attribution
from the CLI without reminting RoleStore.

## Change

- `cli.py`: `--seat` on equip + transfer
- `test_roles.py`: CLI round-trip asserts seat on occupant
- README examples updated

## Not touched

`integrations/grokbot_control/*`, peer lanes. Cloud/GitHub only. No remint.
