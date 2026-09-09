# Repair occupant.seat round-trip and export_meta.includes_secrets

- Slice: `repair-role-occupant-seat-export-meta-20260905-01`
- Parent: hinge-r4-obligation-advance-20260905-01 → `8a344d54`

## Gap (measured)

On current main after #8812, `python3 -m unittest test_roles` failed two
pre-existing cases (also red on `7a6958c` before the obligation stamp):

1. `normalize_role` rebuilt occupant then read `seat` / `account_pool` from the
   new dict, so `get()` dropped them. `release()` then stored
   `last_released.seat = None`.
2. `export_package` set `export_meta.includes_secrets` then ran `_scrub_secrets`,
   which drops keys matching `secret`.

## Change

- Copy occupant `seat` / `account_pool` from the source dict
- Stamp `includes_secrets: false` after scrub
- Round-trip regression: `test_equip_seat_survives_get_round_trip`

## Tests

16/16 `test_roles` pass. Open-door guard PASS. No remint.
