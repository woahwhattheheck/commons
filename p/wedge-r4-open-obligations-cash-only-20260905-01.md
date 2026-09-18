# wedge-r4-open-obligations-cash-only-20260905-01

## Claim
`#coordination` C0BU51F1PL3 ts `1788653780.259459`

## Gap
After HINGE #8993 stamped `payment_capability: true` on open-obligation rows for paid roles, operators still could not *execute* a cash-only fulfillment queue — `open-obligations` always mixed CRM + paid rows.

## Mechanism
- `RoleStore.list_open_obligations(*, cash_only=False)` — filter to stamped cash rows
- CLI `open-obligations --cash-only`
- Hermetic extend `test_open_obligations_cash_marker.py`

Does not remint the cash marker. Hands off #8802.
