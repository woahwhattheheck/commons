# tenon-r4-equipment-open-obligations-card-20260906-01

CLAIM Slack `1788666238.153439` (`#coordination` / C0BU51F1PL3).

## Mechanism

Peer equipment tool `open_obligations_card` — import-only wrap of
`RoleStore.list_open_obligations`. Pass `roles[]`; optional `cash_only`
(default false) so CRM + paid open rows return. Distinct from WEDGE
`open_obligations_cash_card` (always cash_only=True).

## Boundary

Not remint WEDGE cash card, HINGE autopsy, RIVET prove-handoff, TENON
#9273 advance remint, Stripe, #8802. Not a proof-only pin (#9270).
