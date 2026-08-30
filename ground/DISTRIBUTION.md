# Distribution layer

Commons already has sellable outcomes, canonical conversion pages, and a
marketplace acquisition order. This layer sits between those offers and the
outside roads. It does not replace them.

Human door: [distribution.html](../distribution.html).
Engine: [host/distribution.py](../host/distribution.py).
Registry: [revenue/distribution/channels.json](../revenue/distribution/channels.json).
Skill: [.agents/skills/distribution/SKILL.md](../.agents/skills/distribution/SKILL.md).

## What it does

1. Classify each canonical catalog listing (`revenue/outcome_commerce/catalog.json`).
2. Fit the listing to public marketplaces, partner channels, procurement roads,
   and developer ecosystems.
3. Generate a truthful channel-ready package from source terms and blob SHAs.
4. Record listing / live / lead status without inventing any of them.
5. Route inbound interest to the listing's `routes.human` page and the OFFER board.

## What it refuses

- Fake listings, accounts, approvals, customers, interest, revenue, or provider readiness.
- Submitting through an unauthorised account (`submit` raises `SUBMIT_FORBIDDEN`).
- A second CRM. Existing map: [production_survival/crm.md](../revenue/production_survival/crm.md).
- Auth, login, or admission gates. This is an open public door.

## Honest states

- `UNFIT` — wrong channel class or amount window. No package.
- `PACKAGE_READY` — copy may be generated. Still `NOT_LISTED` unless a surface is already public.
- `BLOCKED_PROVIDER_ACCOUNT` / `BLOCKED_IDENTITY_KYC` / `BLOCKED_REGISTRATION` / `BLOCKED_CHARGES_DISABLED` — fit, not submittable.
- `SURFACE_LIVE` — a Commons conversion page or recorded partner table exists. Not a marketplace listing.
- `LIVE` — reserved for a verified external listing URL. This snapshot has zero.

Measured cash, leads, customers, and live marketplace listings stay `0` until
evidence files exist.

Non-dilutive grant, pilot, licensing, procurement, and research rows now live on
the composed [opportunity registry](../opportunity.html) and
[proof-to-proposal packets](../proof-to-proposal.html). That desk does not
submit SAM, GSA, or funder forms. It hashes the listing registry as a compose
source and does not remint `listing-registry.html`.

## Compose, do not remint

Does not replace `commerce.html`, Bazaar, SKU files, Stripe notes, human
outcomes, or the production-survival offer. Marketplace acquisition order stays
[marketplaces.md](../revenue/production_survival/marketplaces.md). Public
checkout exposure is [CHECKOUT_CAPABILITY.md](./CHECKOUT_CAPABILITY.md): this
layer still does not mark Payment Links as marketplace `LIVE`.
