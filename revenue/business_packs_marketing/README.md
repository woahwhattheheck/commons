# Business packs — marketing research (SCOUT)

Owner-assigned research lane (Bryce, 2026-09-02): find the exact buyer for each business-pack tier, map every pack to its buyer, and research X Ads so Bryce can decide his own spend. This directory is that research. It is not marketing execution, not ad copy shipped, not spend, not a checkout.

| file | what it is |
|---|---|
| [BUYER_TIERS.md](./BUYER_TIERS.md) | one buyer card per tier ($20 · $50 · $100 · $200 · $1,000 · $10,000): who, trigger, job to be done, what the pack must contain, where they are on X, creative angle, words that work and words that break policy, objections, evidence, confidence. Plus the break-even table that says which tiers paid X can carry. |
| [X_ADS_BRIEF.md](./X_ADS_BRIEF.md) | X Ads in September 2026: costs, targeting types, formats, Grok features, measurement (pixel + thank-you page gap), budget scenarios, kill criteria, owner prerequisites. |
| [LAW_AND_POLICY_FLAGS.md](./LAW_AND_POLICY_FLAGS.md) | FTC 16 CFR 437 (when a pack becomes a "business opportunity"), the Jan 2025 NPRM, X ad policies read directly, the three-element lottery test for "mystery nuts", chargeback thresholds, the word "franchise". Items marked OWNER need Bryce or counsel. |
| [PACK_BUYER_MAP.json](./PACK_BUYER_MAP.json) | machine-readable map: tier → persona → handles → keywords → verdict; existing shelf SKUs → buyer → X role; build demands posted. |

Laws this research lives under: [ground/BUSINESS_PACKS.md](../../ground/BUSINESS_PACKS.md) (unique instance; similar is not clone; mystery nuts not lottery, no invented odds; marketing = Bryce; no invented Stripe URLs). Slack lane: `#marketing-research` `C0BUFLK7TNY`; factory lane `#business-packs` `C0BU7JAPUH3`.

Update rule: when a pack lands or changes tier, add or edit its row in `PACK_BUYER_MAP.json` and its finding in `BUYER_TIERS.md`; post the delta in `#marketing-research` with the SHA.
