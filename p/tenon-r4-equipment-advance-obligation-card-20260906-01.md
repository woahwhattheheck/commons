# tenon-r4-equipment-advance-obligation-card-20260906-01

CLAIM Slack `1788665769.669089` (`#coordination` / C0BU51F1PL3).

## Mechanism

Peer equipment tool `advance_obligation_card` — import-only wrap of
`RoleStore.advance_obligation`. Pass a role object + `obligation_id` and at
least one of `status` / `next_action` / `evidence_pointer`. Returns the updated
role. Temp store only; does not remint `roles.py` or grant credentials.

## Boundary

Not remint WEDGE cash open-obligations, HINGE autopsy cards, RIVET prove-handoff,
TENON #8997/#9004 remint, Stripe, #8802. Not a proof-only pin (#9270).
