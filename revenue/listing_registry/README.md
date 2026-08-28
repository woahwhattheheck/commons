# Commons listing registry

Machine snapshot for [listing-registry.html](../../listing-registry.html).

Canonical offers stay in `revenue/outcome_commerce/catalog.json`. Distribution
channels stay in `revenue/distribution/`. This directory is the listing
registry: one row per offer × surface, plus ready-to-submit copy from real
evidence.

```bash
python3 host/listing_registry.py validate
python3 host/listing_registry.py registry
python3 host/listing_registry.py asset --id same-day-agent-survival-proof__upwork-project-catalog
python3 host/listing_registry.py export
python3 host/listing_registry.py submit   # always SUBMIT_FORBIDDEN
python3 host/listing_registry.py --self-test
```

`submit` always fails. Assets are not live listings.
`registry.json` counts `external_live_listings=0`, `submitted=0`,
`verified_buyers=0`, `collected_cash_usd=0.00`, `duplicate_postings=0`.

Do not remint commerce, distribution, checkout, current-work, or the
profitability map from here.
