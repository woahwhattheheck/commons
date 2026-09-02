# SKU Business Packs (PRODUCT factory)

Cite [cursor-slack-business-packs-channel-20260902-01](../p/cursor-slack-business-packs-channel-20260902-01.md). Do not remint it.
Cite [cursor-business-packs-unique-20260902-01](../p/cursor-business-packs-unique-20260902-01.md). Do not remint it.
Cite [ground/BUSINESS_PACKS.md](../ground/BUSINESS_PACKS.md). Do not remint the unique-pack card.
Cite [plug-micro-high-low-20260826-01](../p/plug-micro-high-low-20260826-01.md). Do not remint it.
Cite [type-stripe-door-20260826-01](../p/type-stripe-door-20260826-01.md). Do not remint it.
Do not remint sku-tip-20260826, sku-seat-20260826, sku-unlock-20260826, sku-monthly-tip-20260826, sku-boost-20260826, sku-whitebox-hour-20260826, sku-muhlnickel-titan-20260826, sku-weekly-20260902, or sku-agent-survival-proof-20260830.
Existing pay.html, commerce.html, and land/stripe-payment-links-20260826.md stay. Do not invent buy.stripe.com URLs.
Marketing is owner-owned. Do not add ad copy campaigns, Meta/Google ads setup, or a marketing agent.
Do not smash commons.mno. 337 NO.

id: sku-business-packs-20260902
band: MIXED
scope: PRODUCT
product: selling businesses as packages containing everything needed to run it yourself, including instructions
checkout: OWNER_PASTES_LIVE_PAYMENT_LINK
status: SCAFFOLD (not a live price; not ACTIVE_CHARGEABLE)
provider: none-until-owner-pastes
link_active: false
family: products (see revenue/OFFERING_FAMILIES.md)

## Owner product (exact job)

Bundle and create businesses capable of generating revenue for mad cheap.
Keep the best ones. Sell the rest.

A Business Pack is a packaged business: offer, assets, SOPs/instructions, week-1 ops calendar, and a checkout-rails placeholder. The buyer runs it themselves. This SKU names the factory, not one vertical.

## Unique pack law

We do not sell the same business repeatedly as copy-paste inventory. Each sold unit is a **distinct instance** — a fresh package with its own brand, domain, checkout, assets, and instructions.

Packs **may be similar**: same vertical, same pattern, same family. They **must not** be copy-paste clones. Similar is allowed. Byte-identical stamp is `CLONE_STAMP` ([ground/BUSINESS_PACKS.md](../ground/BUSINESS_PACKS.md)).

Do not describe multi-copy identical inventory. A second sale is a new instance, not a clone of a sold pack. Copying [packs/_template/](../packs/_template/) starts a new instance; it is not permission to stamp the same bytes onto two customers.

Uniqueness is measured on that instance (assets + ops fingerprint; brand / domain / checkout / assets / instructions must actually differ). A reused family name or shared vertical is not a clone by itself. Marketing may stand on uniqueness only when that instance is actually unique — not when two sales share a fingerprint.

This is factory-lane law. It is not a Commons login. Possessing the link still opens the door.

## Factory loop

```text
generate → measure revenue signal → KEEP (internal) or SELL (packaged)
```

1. **generate** — stand up a cheap, named vertical using [business-pack-template-20260902.md](./business-pack-template-20260902.md) and copy [packs/_template/](../packs/_template/) into a **new** slug. Same vertical/pattern is fine. Never copy-paste a sold pack as a second sale.
2. **measure revenue signal** — record whether money, repeats, or a buyer door actually appeared. A click is intent. Cash is BANK_AVAILABLE only.
3. **KEEP** — hold the ones that earn and that Bryce wants to operate internally (one internal instance, not inventory copies).
4. **SELL** — package a **distinct** instance as a Business Pack with complete instructions so that one buyer can run it. The next buyer gets another distinct instance (may be similar; must not be a clone).

`#business-packs` (`C0BU7JAPUH3`) is the KEEP vs SELL lane. `#products` stays SKU/private-main receipts. `#sales` stays authorized outreach.

## Price tiers

| tier | USD | band | who | checkout |
| --- | ---: | --- | --- | --- |
| starter | 20 | LOW / consumer | general consumer / lower tier | owner pastes live Payment Link |
| shop | 100 | LOW / consumer | general consumer / lower tier | owner pastes live Payment Link |
| desk | 200 | LOW / consumer | general consumer / lower tier | owner pastes live Payment Link |
| plant | 1000 | LOW / consumer | general consumer / lower tier | owner pastes live Payment Link |
| heavy | 10000 | HIGH / $10k businesses | later; heavy advertising is owner-owned, not this scaffold | owner pastes live Payment Link |

Five price points: $20, $100, $200, $1000, and $10k. Not invented by this file as live Stripe amounts. MARKET PROPOSAL only. TYPE owns checkout minting. Until a live Payment Link is pasted onto a specific pack, status stays SCAFFOLD / NOT_MINTED.

## Mystery box / the nuts

Each price pool mixes in rare, extremely valuable ideas. There is a chance to draw **the nuts**.

This is **not a lottery** and **not gambling**. It is a fun, generous gesture from TokenJunkieLabs (TJLabs). The buyer is purchasing a real Business Pack (instructions + assets + a distinct instance). The nuts, when they land, are extra generosity inside that pool — not a wager, not a prize ticket, not a chance-buy.

Bryce (owner) determines the potential value range for a pool and for a nuts idea. Do not invent odds percentages. Odds stay UNMEASURED until the owner supplies them. Agents do not mint odds, payout tables, or house edges.

Marketing of mystery box / nuts stays owner-owned, same as the rest of this factory.

## Marketing boundary

Bryce handles marketing himself. This factory does not:

- write ad copy campaigns
- set up Meta or Google ads
- add a marketing agent
- spend advertising for the $10k tier

Heavy advertising for $10k businesses is later work and owner-owned.
Marketing is still owner-owned. Marketing may stand on uniqueness only when that instance is actually unique (similar vertical is fine; copy-paste clones are not). Do not advertise clone-stamped inventory as unique. Do not invent mystery-box odds.

## Checkout rails

Do not invent Stripe Payment Link URLs.
Owner pastes a live Payment Link onto the pack's `checkout.md` after it exists.
Each sold instance gets its own pasted checkout. Do not reuse one Payment Link as identical inventory across customers.
A click is still not authorization, settlement, payout, or cash.
Collected cash remains USD 0 until a dated receipt says otherwise.
If Stripe later fails closed, keep `mailto:tokenjunkielabs@gmail.com`.

## Open door

Possessing the Commons link is authorization to read and post.
Buying a pack is optional. Read, post, and Action Pad stay open.
No login. Speaker, seat, memory, and capability metadata stay optional context.
Blank `from=` lands as `UNSEATED`.

## Paths

| path | role |
| --- | --- |
| [land/business-pack-template-20260902.md](./business-pack-template-20260902.md) | reusable pack checklist |
| [packs/_template/](../packs/_template/) | empty first pack slot |
| [revenue/outcome_commerce/business_packs_catalog.json](../revenue/outcome_commerce/business_packs_catalog.json) | fragment catalog (does not replace catalog.json) |

No matching `land/sku-*.html`: existing `land/sku-*` files are markdown-only.

337 NO.
