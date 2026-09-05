# HINGE R4 release occupant

- Slice: `hinge-r4-release-occupant-20260905-01`
- Claim: `#coordination` ts `1788582460.484979`
- Parent: bind-g2-session `#8799` → `2ebc660`

## Gap (measured)

`equip` refuses while occupied; only `transfer` moved the occupant. Ending a
session without a known successor had no store mechanism — README also still
omitted `bind-route` after #8799.

## Change

- `RoleStore.release(from_session_id=)` clears occupant; records `last_released`
- Bound `access_routes` (session_id / last_run_id) preserved
- CLI `release`; hermetic re-equip after release
- README documents `bind-route` + `release`; seat stays on occupant

## Not touched

`integrations/grokbot_control/*`, agent-rescue/pagespeed, peer lanes. No remint.
