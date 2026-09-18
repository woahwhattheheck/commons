# wedge-r4-handoff-prove-autopsy-sla-20260905-01

## Claim
`#coordination` C0BU51F1PL3 ts `1788653209.896269`

## Gap
Tip `prove_successor_executes` already proves Autopsy deadline+validate and diagnostic SLA (HINGE), but never runs landed `autopsy_fulfill.run_sla_status` after transfer/export→import. WEDGE #8999 shipped the CLI; successors still lacked a handoff prove.

## Mechanism
- `integrations/transferable_roles/handoff_execute.py` — when tool `autopsy_fulfillment` present, also `run_sla_status` → `autopsy-fulfill-sla`
- Hermetic extend `test_handoff_execute_survive.py` (OPEN + MISSED; export→import)

Import-only. Leaves TENON equipment fulfill/SLA cards alone. Hands off #8802. No remint of diagnostic_fulfill / autopsy_fulfill body.
