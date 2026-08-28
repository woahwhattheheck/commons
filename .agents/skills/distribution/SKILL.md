---
name: distribution
description: >
  Fit Commons sellable outcomes to public marketplaces, partner channels,
  procurement roads, and developer ecosystems. Generate truthful channel-ready
  packages, report honest listing/live/lead status, and route inbound interest
  to canonical conversion pages. Never submit, never invent buyers or cash.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/distribution.md
---

# Distribution

Facts: [ground/DISTRIBUTION.md](../../../ground/DISTRIBUTION.md).
Door: `distribution.html`. Engine: `host/distribution.py`.

## Do this

1. Load `revenue/outcome_commerce/catalog.json` and `revenue/distribution/channels.json`.
2. `python3 host/distribution.py matrix` — see FIT / UNFIT / BLOCKED / SURFACE_LIVE.
3. Generate a package only for FIT pairs. Treat it as copy, not a live listing.
4. Route buyer interest to the listing `routes.human` page and the OFFER board.
5. Keep measured zeros: live marketplace listings, leads, customers, cash.

## Do not

Submit through an unauthorised account. Invent Upwork/Fiverr/SAM/GitHub Marketplace
readiness. Open a second CRM. Remint commerce, bazaar, or SKU files. Add auth.

## Receipt

`p/{id}.md` on HEAD naming the changed distribution paths and the honest channel states.
