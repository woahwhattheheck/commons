# Checkout capability snapshot

Measured provider truth for public Commons checkout. This folder stores
**no** bank, routing, tax, card, credential, address, or private buyer
data.

`snapshot.json` is the observation. `host/checkout_capability.py`
projects public rails from it and fails closed when catalog, SKU files,
or HTML disagree.

A public rail is chargeable **and** payout-capable only when livemode,
`charges_enabled`, `payouts_enabled`, link `active=true`, and the
canonical recorded URL all match. Duplicate Payment Links on the same
SKU metadata stay inert.
