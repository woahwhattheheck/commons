# Canonical listing registry

Commons already has a storefront (commerce / bazaar / pay), a distribution
layer, proof-to-proposal and accepted-scope roads, feature and resource
trackers, checkout capability, and marketplace acquisition order. This leftover
does not replace them.

It is the **canonical listing registry**: one row per offer × surface for
GitHub Marketplace-style listings, MCP directories, partner/vendor directories,
procurement portals, service catalogs, and community channels.

Human door: [listing-registry.html](../listing-registry.html).
Engine: [host/listing_registry.py](../host/listing_registry.py).
Registry: [revenue/listing_registry/registry.json](../revenue/listing_registry/registry.json).
Assets: [revenue/listing_registry/assets.json](../revenue/listing_registry/assets.json).
Schema: [revenue/listing_registry/schema.json](../revenue/listing_registry/schema.json).
Skill: [.agents/skills/listing-registry/SKILL.md](../.agents/skills/listing-registry/SKILL.md).

## Each row shows

- exact offer / SKU
- evidence packet (source path + blob SHA)
- chargeability state
- submission status
- published status
- account / owner
- URL (Commons conversion URL only when the surface is already public; otherwise null)
- last verified time
- next action
- `duplicate=false` — a second post of the same SKU on the same surface is refused

## Honest states

- `NOT_PUBLISHED` — draft or package only. Not a live listing.
- `SURFACE_PUBLISHED` — a Commons conversion page or the existing Slack table. Not marketplace `LIVE`.
- `OWNER_PLATFORM_UNCLAIMED` — GitHub About/topics. Peers do not fake the owner act.
- `EXTERNAL_LIVE` — reserved. This snapshot has zero.
- `NOT_SUBMITTED` / `submit_allowed=false` on every row.
- Chargeability: Stripe `ACTIVE_CHARGEABLE` is Commons checkout only. External surfaces stay `NOT_CHARGEABLE_ON_THIS_SURFACE`. MCP is `NOT_A_PRICED_SKU`.

Measured cash, buyers, submissions, and live marketplace listings stay `0`
until evidence files exist.

## What it refuses

- Creating external accounts
- Accepting provider terms
- Submitting listings
- Claiming publication, buyers, revenue, or cash without exact receipts
- Duplicate posting
- Auth, login, or admission gates

`python3 host/listing_registry.py submit` raises `SUBMIT_FORBIDDEN`.

## Compose, do not remint

Does not replace [DISTRIBUTION.md](./DISTRIBUTION.md), [COMMERCE.md](./COMMERCE.md),
[CHECKOUT_CAPABILITY.md](./CHECKOUT_CAPABILITY.md), [SCOPE_TO_DELIVERY.md](./SCOPE_TO_DELIVERY.md),
[CURRENT_WORK.md](./CURRENT_WORK.md), [PROFITABILITY_BUILD_MAP.md](./PROFITABILITY_BUILD_MAP.md),
or [RESOURCE_LEDGER.md](./RESOURCE_LEDGER.md).

Profitability map traffic items 3–5 (Show HN draft, MCP directories, GitHub
About) bind here as drafts. Current-work close still requires a 40-character
main SHA plus claimed paths.
