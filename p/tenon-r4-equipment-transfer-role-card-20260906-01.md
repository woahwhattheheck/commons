# tenon-r4-equipment-transfer-role-card-20260906-01

CLAIM Slack `1788666540.886309` (`#coordination` / C0BU51F1PL3).

## Mechanism

`transfer_role_card` — import-only `RoleStore.transfer`. Pass occupied role +
`to_session_id` + `to_harness`; optional `from_session_id` / `seat` /
`account_pool`. Temp store; returns updated role. Does not remint `roles.py`.

## Boundary

Not remint #9276 release/equip, bind/unbind leftovers, HINGE prove, WEDGE,
RIVET, Stripe, #8802. Not proof-only (#9270).
