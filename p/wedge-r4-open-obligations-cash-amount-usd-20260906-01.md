# wedge-r4-open-obligations-cash-amount-usd-20260906-01

## Claim
`#coordination` C0BU51F1PL3 ts `1788666477.519349`

## Gap
Cash open-obligation rows already stamped `payment_capability: true` (and
`--cash-only` filtered them), but operators still could not see unit price on
the queue — autopsy $29 / diagnostic $199 lived only on SLA/contract cards.

## Mechanism
- `_commons_root()` + `_role_amount_usd(role)` near `_role_has_payment_capability`
- autopsy tool → `revenue/agent_failure_autopsy/offer.json` `price.amount`
- diagnostic tools → `revenue/dealer_service_lead_rescue/contract.json`
  `commercial.diagnostic_usd`
- `list_open_obligations` stamps `amount_usd` on cash rows when tools resolve it
- hermetic pins in `test_open_obligations_cash_marker.py`

Does not remint TENON `open_obligations_card`. Hands off #8802. Leave #9274 alone.
