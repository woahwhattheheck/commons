# Business Pack template (reusable checklist)

Cite [sku-business-packs-20260902](./sku-business-packs-20260902.md). Do not remint SKUs.
Cite [cursor-slack-business-packs-channel-20260902-01](../p/cursor-slack-business-packs-channel-20260902-01.md). Do not remint it.
Cite [cursor-business-packs-unique-20260902-01](../p/cursor-business-packs-unique-20260902-01.md). Do not remint it.
Cite [ground/BUSINESS_PACKS.md](../ground/BUSINESS_PACKS.md).
Copy [packs/_template/](../packs/_template/) to `packs/<vertical-slug>/` for a **new** instance. Do not clone a sold pack.
Do not invent Stripe Payment Link URLs. Owner pastes a live Payment Link.
Marketing is owner-owned. 337 NO. Do not smash commons.mno.

Open door stays. Possessing the Commons link is enough to read and post. A pack sale is optional money, never a seat.

## Unique pack law

We do not sell the same business repeatedly as copy-paste inventory. Each sold unit is a **distinct instance** (a fresh package) — own brand, domain, checkout, assets, and instructions.

Packs **may be similar** (same vertical / same pattern). They **must not** be copy-paste clones. Similar is allowed. Byte-identical stamp is `CLONE_STAMP`.

Do not describe multi-copy identical inventory. Marketing may stand on uniqueness only when this instance is actually unique (assets + ops fingerprint unique among sales). A reused family name or shared vertical is not a clone by itself. Same fingerprint on two sales is `CLONE_STAMP`.

## 1. Vertical name

- Slug (`packs/<slug>/`) — new directory per instance, not a copy of a sold pack:
- Public name (this instance's brand):
- One-line what it is:
- Family: product (packaged business the buyer keeps and runs)
- Tier ($20 / $100 / $200 / $1000 / $10k):
- This instance's domain:
- Distinct from prior sale_id (if any):
- Same vertical/pattern as another pack? (similar is allowed; copy-paste clone is not):

## 2. Offer

Fill `offer.md`.

- Who buys it:
- What they can run on day one:
- What they keep (files, instructions, assets):
- What they do not get (owner marketing, live ads accounts, invented checkout URLs, `.mno` actuation):
- Price USD (one of the five tiers):
- Status: SCAFFOLD until checkout.md has an owner-pasted live Payment Link
- This purchase is a distinct instance (similar vertical/pattern allowed; not a copy-paste clone): yes / no

## 3. Assets list

Fill `assets.md`. List every file the buyer needs to run it. Missing asset = pack is not SELL-ready.

- Brand / name assets (unique to this instance):
- Templates / forms / scripts (this instance, not a clone stamp):
- Public pages or doors (optional; Commons stays open either way):
- Data the buyer may reuse (license + provenance, or UNMEASURED):
- assets fingerprint / ops fingerprint (for [host/business_pack_unique.py](../host/business_pack_unique.py)):

## 4. SOPs / instructions

Fill `instructions.md`. The product is the business plus the instructions to run it yourself.

- Start:
- Daily loop:
- Weekly loop:
- Stop / pause:
- How to record a revenue signal without inventing cash:

## 5. Checkout rails placeholder

Fill `checkout.md`. Exact sentence to keep:

> Owner pastes live Payment Link.

Do not write a `buy.stripe.com` or `donate.stripe.com` URL here.
TYPE owns minting. This template does not mint.
A pasted link is still not authorization, settlement, payout, or cash.
This instance's checkout is its own. Do not reuse another customer's Payment Link as identical inventory.

## 5b. Mystery box / the nuts

Each price pool ($20 / $100 / $200 / $1000 / $10k) may mix in rare, extremely valuable ideas. Chance to draw **the nuts**.

Not a lottery. Not gambling. Fun generous gesture from TokenJunkieLabs (TJLabs). The sold unit is still a real Business Pack. The nuts are extra generosity inside the pool, not a wager.

- Price pool for this instance:
- Owner-set potential value range (Bryce fills; leave UNMEASURED if blank):
- Is this instance a nuts mix-in? (owner marks; do not invent):
- Odds: UNMEASURED unless the owner supplies them. Do not invent percentages.

Marketing of mystery box / nuts is owner-owned.

## 6. Ops calendar — week 1

Fill `week1.md`.

| day | operator action | done when |
| --- | --- | --- |
| 0 | copy this template into a **new** slug; name this instance | slug directory exists and is not a sold-pack clone |
| 1 | fill offer + assets | both files nonempty |
| 2 | write instructions | a stranger can start |
| 3 | run the smallest real loop | one measured signal or a dated zero with search space |
| 4 | complete week-1 calendar | seven days named |
| 5 | decide KEEP vs SELL | criteria below filled |
| 6 | if SELL: paste live Payment Link or leave NOT_MINTED | no invented URL |
| 7 | receipt as a new `p/{id}.md` if anything shipped | exact id, do not remint |

## 7. KEEP vs SELL criteria

Fill `keep-vs-sell.md`. Factory loop: generate → measure revenue signal → KEEP (internal) or SELL (packaged).

**KEEP (internal)** when most of these are true:

- A dated revenue signal exists (not a click, not a bake)
- Repeats without a new invention each time
- Bryce wants to operate it
- Holding it is cheaper than packaging it

**SELL (packaged)** when most of these are true:

- A buyer can run it from instructions.md without Bryce as operator
- Assets list is complete
- Week-1 calendar is complete
- Support boundary below is honest
- Marketing remains owner-owned and is not bundled as an ads setup
- This sale is a **distinct instance** (own brand / domain / checkout / assets / instructions). Similar vertical/pattern is allowed. Copy-paste clone is not. Marketing uniqueness only if actually unique.

Neither KEEP nor SELL is a Commons admission condition. The board stays open.

## 8. Support boundary

What the pack includes:

- The named offer, assets, SOPs/instructions, week-1 calendar
- Checkout placeholder until the owner pastes a live Payment Link

What the pack does not include:

- Ad copy campaigns, Meta / Google ads setup, or a marketing agent
- Invented Stripe URLs
- Device or `commons.mno` actuation (337 NO)
- Closing Commons read or post; possessing the link stays enough

Buyer questions after a sale: public Commons post or `mailto:tokenjunkielabs@gmail.com`. Secrets stay off the board.

## Factory law

Cheap generate. Measure. Keep the best. Package the rest.
Each sold unit is a distinct instance. Similar vertical/pattern is allowed. Copy-paste clones are not.
Mystery box / the nuts: rare valuable ideas mixed into each price pool. Not a lottery. Not gambling. TJLabs generosity. No invented odds.
Marketing is still owner-owned. Checkout URLs are pasted, never invented.
337 NO.
