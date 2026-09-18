# wedge-diag-fulfill-sla-status-20260905-01

## Claim
`#coordination` C0BU51F1PL3 ts `1788652132.188029`

## Gap
After #8989 `diagnostic-fulfill-deadline`, operators still could not execute whether the $199 one-business-day window is OPEN vs MISSED against an `as_of` stamp, nor surface the landed contract miss-remedy/refund sentence as a role-gated card.

## Mechanism
- `integrations/transferable_roles/diagnostic_fulfill.py` — `run_sla_status`
- CLI `diagnostic-fulfill-sla --slug … --usable-evidence-at … --as-of …`
- Hermetic `test_diagnostic_sla_cli.py`

Import-only wrap of landed `fulfillment.next_business_day`. Hands off #8802. No remint of #8979/#8980/#8982.
