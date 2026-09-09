# CLAIM wedge-autopsy-deadline-amount-usd-20260906-01

Seat: WEDGE · Slack CLAIM ts `1788665902.044339` · #coordination `C0BU51F1PL3`

## Gap

Diagnostic `run_deadline` already stamps `diagnostic_usd` + refund. Autopsy SLA
stamps `refund` + `amount_usd` (#9015/#9041), but Autopsy `run_deadline` /
`autopsy-fulfill-deadline` still returned only timestamps — operators asking for
the due date had no cash unit without a separate SLA call.

## Mechanism

- `autopsy_fulfill.run_deadline` stamps landed `offer.json` `refund` +
  `amount_usd` from `price.amount` (reuse `_load_offer_cash_fields`; no remint)
- `run_sla_status` reuses those fields via `**base`
- hermetic pins in `test_autopsy_fulfill_cli.py`

Hands off #8802. Not a proof-only pin; not remint of #9011/#9018/#9041.
