# wedge-autopsy-fulfillment-cli-deadline-cash-20260912-01

## Claim
`#coordination` C0BU51F1PL3 ts `1789196982.058129`

## Gap
After R4 `autopsy-fulfill-deadline` stamps landed offer `amount_usd` + `refund`
(`wedge-autopsy-deadline-amount-usd-20260906-01`), the product spine CLI

`python3 revenue/agent_failure_autopsy/fulfillment.py deadline --usable-evidence-at …`

still returned timestamps only — operators on the hermetic landed CLI missed the
$29 cash unit / miss-remedy unless they routed through transferable_roles.

## Mechanism
- `fulfillment.py` `_load_offer_deadline_cash()` reads `offer.json` (refund +
  `price.amount` as `amount_usd`); forbid `sk_`/`rk_`/`whsec_`/`prod_`/`price_`/`plink_`
- `deadline` CLI card stamps those fields alongside `delivery_due_at`
- hermetic pin in `test_agent_failure_autopsy.py::test_deadline_cli_stamps_offer_cash`

Does not remint R4 wraps / RoleStore / TENON equipment cards / prove_handoff.
Hands off #8802. No Stripe invent.
