# HINGE R4 last_released / prior_* round-trip

- Slice: `hinge-r4-last-released-roundtrip-20260905-01`
- Parent: `#8812` squash `8a344d54`; seat/export repair `f7986469`
- Does not remint `p/hinge-r4-obligation-advance-20260905-01.md` or
  `p/repair-role-occupant-seat-export-meta-20260905-01.md`

## Gap (measured on current main after those commits)

`inspect()` after `release()` returned `last_released=None` even though
`_write` persisted it. `get()` after `transfer()` dropped `prior_session_id`
and `prior_harness`. `normalize_role` rebuilt occupant from a whitelist that
omitted those fields.

#8812 `advance-obligation` CLI was landed without README entry points.

## Change

- Keep `last_released` through get/inspect
- Keep occupant `prior_session_id` / `prior_harness` / `prior_seat`
- README documents `advance-obligation`
- Sibling + invalid-status coverage for advance

## Not touched

shared_equipment keyring, grokbot_control, peer lanes. No remint.
