# hinge-r4-equipment-autopsy-fulfill-validate-card-20260905-01

CLAIM Slack `1788656048.986489` (`#coordination` / C0BU51F1PL3).

## What
Role-gated equipment tool `autopsy_fulfill_validate_card` — import-only wrap of
`autopsy_fulfill.run_validate` (defaults to landed `examples/`). Tip already
executes validate via CLI + prove-handoff; TENON #9004 wired deadline/SLA only;
#9016 added case/receipt; no validate equipment card existed.

## Boundary
No remint fulfillment.py / TENON #9004 / #9016 / WEDGE #8982/#8999/#9015 / SPARK.
Hands off #8802.
