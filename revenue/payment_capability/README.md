# Payment-capability registry

Provider-neutral rails for Commons checkout. Source of truth:
`registry.json`. Projector: `host/payment_capability.py`.

A rail is public only when `capability_state=CHARGEABLE` and
`public_presentation=EXPOSE`. Owner-dashboard chargeability is not a
public URL. Inert rails keep one-click official provider UIs and stay
unpublished. Cash stays USD 0 without `BANK_AVAILABLE` evidence.

This leftover reuses:

- `revenue/checkout_capability/snapshot.json`
- `revenue/outcome_commerce/catalog.json`
- `revenue/payment_ready/pack.json`
- `revenue/reply_to_revenue/funnel.json`
- `revenue/scope_to_delivery/catalog_bindings.json`
- `ground/RESOURCE_LEDGER.json`
- `ground/PROFITABILITY_BUILD_MAP.md`
- `ground/FEATURES.md`

It does not remint SKUs, Payment Links, or catalog listings.
