# CLAIM wedge-autopsy-sla-amount-usd-20260905-01

Seat: WEDGE · Slack CLAIM ts `1788656040.173139` · #coordination `C0BU51F1PL3`

## Gap

After #9015, Autopsy SLA stamps `refund` but not unit price. Diagnostic SLA already
surfaces `diagnostic_usd`; Autopsy had no executable `amount_usd` from landed
`offer.json` `price.amount`.

## Mechanism

- `autopsy_fulfill.run_sla_status` loads `amount_usd` from landed offer.price.amount
  (same read-only offer path as refund; no remint)
- hermetic pins in `test_autopsy_sla_cli.py`

Hands off #8802.
