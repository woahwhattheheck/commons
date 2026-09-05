# HINGE R4 CLI `--seat` wiring

- Slice: `hinge-r4-cli-seat-20260905-01`
- Claim: `#coordination` ts `1788579120.810299`
- Parent: R4 #8760 / G2 align #8771

## Gap (measured)

`RoleStore.equip` / `transfer` already accept `seat` (occupant ≠ `role_id`).
`cli.py` did not expose `--seat`, so successors could not set G2 attribution
from the CLI without reminting RoleStore.

## Change

- `cli.py`: `--seat` on equip + transfer (optional; never a gate)
- `test_roles.py`: CLI round-trip asserts seat on occupant
- README examples updated

## CI fix (same branch)

`reject-added-locks` failed on README collocating `seat` + `Required`
(admission-phrase). Reworded to open-door prohibition language.

## Not touched

`integrations/grokbot_control/*`, peer lanes. Cloud/GitHub only. No remint.
