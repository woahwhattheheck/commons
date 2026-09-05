# Commons distribution layer

Machine snapshot for [distribution.html](../../distribution.html).

Canonical offers stay in `revenue/outcome_commerce/catalog.json`. This directory
only maps those offers onto channels, writes packages, and reports honest
status.

```bash
python3 host/distribution.py validate
python3 host/distribution.py matrix
python3 host/distribution.py status
python3 host/distribution.py package --offer ho-issue-to-pr --channel upwork-project-catalog
python3 host/distribution.py inbound --offer ho-issue-to-pr --channel contra-services
python3 host/distribution.py export
```

`submit` always fails. Packages are not live listings. `status.json` counts
`live_marketplace_listings=0`, `verified_leads=0`, `collected_cash_usd=0.00`
on this snapshot.

Do not remint commerce, bazaar, SKU, or CRM files from here.
