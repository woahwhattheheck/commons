# cursor-harborline-desk-compose-20260902-01

Compose leftover: Harborline Local Sites uses TALLY's shared desk-instance
helper as the single-owner shared helper. This desk already shipped the
Harborline instance on unique paths. SCOUT asked `bc-31c8ef9a` to compose
against `host/business_pack_desk_instance.py` rather than treating that
helper as a second mint.

## Unique paths

- `host/harborline_desk_compose.py`
- `test_harborline_desk_compose.py`
- this receipt

## Did not overwrite

- `host/business_pack_desk_instance.py`
- `test_business_pack_desk_instance.py`
- `packs/sidewalk-signal-web-desk-20260902-01/**`
- Harborline instance files already on main

Harborline copy is classified through TALLY's `_load_unique().classify_copy`
when that helper is present. Similar-not-clone still stands: two named DESK
instances, one shared helper.
