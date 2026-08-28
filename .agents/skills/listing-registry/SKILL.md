---
name: listing-registry
description: >
  Canonical Commons listing registry. Use when generating GitHub Marketplace-style
  listings, MCP directory rows, partner/vendor directory copy, procurement packs,
  service-catalog packages, or community-channel drafts from verified offers.
  Never submit, never invent publication, buyers, or cash.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
---

# Listing registry

Facts: [ground/LISTING_REGISTRY.md](../../../ground/LISTING_REGISTRY.md).
Door: [listing-registry.html](../../../listing-registry.html).
Engine: [host/listing_registry.py](../../../host/listing_registry.py).

## Do this

1. Read current `revenue/outcome_commerce/catalog.json`, `revenue/distribution/channels.json`, `revenue/checkout_capability/snapshot.json`, and `ground/MCP_INVENTORY.json`.
2. `python3 host/listing_registry.py validate`.
3. Generate or copy an asset with `python3 host/listing_registry.py asset --id <offer>__<surface>`.
4. Route buyer interest to the listing's `human_route`. Do not open a second CRM.

## Do not

- Create external accounts or accept provider terms
- Submit a listing
- Claim `EXTERNAL_LIVE`, buyers, or cash without a receipt
- Duplicate-post the same SKU onto the same surface
- Remint distribution, commerce, checkout, current-work, or the profitability map

`submit` raises `SUBMIT_FORBIDDEN`.
