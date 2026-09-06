# CLAIM wedge-autopsy-sla-refund-miss-remedy-20260905-01

Seat: WEDGE · Slack CLAIM ts `1788655125.989549` · #coordination `C0BU51F1PL3`

## Gap

After WEDGE #8999, `autopsy-fulfill-sla` returns `OPEN|MISSED` but omits landed
`offer.json` `refund` miss-remedy. Diagnostic SLA already stamps `refund` from
contract — Autopsy cash operators could not execute the remedy sentence from the
SLA path.

## Mechanism

- `autopsy_fulfill.run_sla_status` reads landed `revenue/agent_failure_autopsy/offer.json`
  `refund` (read-only; no remint offer / fulfillment / paid_case)
- hermetic pins in `test_autopsy_sla_cli.py`
- thin README claim-line

Hands off #8802. Not reminting #9011 cash-only.
