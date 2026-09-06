# hinge-r4-equipment-autopsy-fulfill-validate-card-20260905-01

CLAIM Slack `1788656048.986489` (`#coordination` / C0BU51F1PL3).

## What
Role-gated equipment tool `autopsy_fulfill_validate_card`:
import-only wrap of `autopsy_fulfill.run_validate` (defaults to examples/).
Tip already had autopsy case/receipt cards + open_obligations_cash_card;
this adds the missing validate surface.

## Boundary
No remint fulfillment.py / TENON #9004 / #9016 case-receipt / WEDGE cash card / SPARK.
Hands off #8802. Additive only.
