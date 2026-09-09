# tenon-r4-equipment-export-import-package-cards-20260906-01

CLAIM Slack `1788667305.532809` (`#coordination` / C0BU51F1PL3).

## Mechanism

`export_role_package_card` / `import_role_package_card` — import-only
`RoleStore.export_package` / `import_package`. Temp store; export clears
occupant and stamps export_meta (no secrets). Import adopts role_id without
remint. Does not remint `roles.py`.

## Boundary

Not remint #9281/#9280/#9276, HINGE prove, WEDGE, RIVET, Stripe, #8802.
Not proof-only (#9270).
