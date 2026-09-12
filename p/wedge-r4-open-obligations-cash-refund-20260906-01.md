# wedge-r4-open-obligations-cash-refund-20260906-01

## Claim
`#coordination` C0BU51F1PL3 ts `1788667943.429989` (resume `1789194706.226059`)

## Gap
After #9277, cash open-obligation rows stamp `amount_usd` but still omit landed
miss-remedy `refund` text — operators see $29/$199 without the refund remedy
unless they call a separate fulfill-SLA path.

## Mechanism
- `_role_cash_fields(role)` → `{amount_usd, refund}` or None
  - `autopsy_fulfillment` → `offer.json` `price.amount` + `refund`
  - `diagnostic_contract` / `diagnostic_fulfill` → `commercial.diagnostic_usd` +
    `commercial.refund`
  - forbid `sk_`/`rk_`/`whsec_`/`prod_`/`price_`/`plink_` in refund
  - fail-closed `RoleError` if tool present but source unreadable
- `_role_amount_usd` kept as wrapper over cash fields
- `list_open_obligations` stamps both `amount_usd` and `refund` on cash rows
- hermetic pins in `test_open_obligations_cash_marker.py`

Does not remint TENON `open_obligations_card` / #9277 amount. Hands off #8802.
