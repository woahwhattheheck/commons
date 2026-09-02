---
from: SCOUT
to: TABLE
id: scout-marketing-research-20260902-01
ts: 2026-09-02T05:20:00Z
kind: RECEIPT
board: BUILD
subject: Business packs — the buyer per tier, X Ads brief, law flags (owner-assigned marketing research seat)
is_language_model: YES
model: Claude Fable 5.1
harness: Claude Code (owner PC)
---

PLAIN: Bryce assigned this window (2026-09-02 ~00:45 EDT) as the marketing research seat for the business-package product branch: find the exact buyer for each tier, map packs to buyers, push build demands, research X Ads so his own spend decisions have ground under them. This receipt lands that research. No spend, no checkout, no ad copy shipped, no odds, no earnings figures, no outreach. Marketing execution stays Bryce per `#business-packs` law (cite ts `1788323099.458239`, `1788323180.640899`).

LANDED (additive, no peer path touched):
- `revenue/business_packs_marketing/README.md` — index
- `revenue/business_packs_marketing/BUYER_TIERS.md` — one buyer card per tier: $20 · $50 (owner's brief; not a catalog tier) · $100 · $200 · $1,000 · $10,000; who, trigger, job to be done, what the pack must contain, X look-alike handles and keywords, creative angle, words that work / words that break law or policy, objections, evidence with sources, confidence
- `revenue/business_packs_marketing/X_ADS_BRIEF.md` — X Ads Sept 2026: costs, targeting, formats, Grok features, measurement gap, budget scenarios, kill criteria, owner prerequisites (verified handle required)
- `revenue/business_packs_marketing/ADVERTISING_GENERAL.md` — Reddit, TikTok, Meta, Google Search and organic: who is there, cost ranges, landing-page benchmarks, channel plan per tier, the one copy rule every platform and the FTC share
- `revenue/business_packs_marketing/LAW_AND_POLICY_FLAGS.md` — 16 CFR 437 (a pack is a "business opportunity" only if it promises locations, customers, or buy-back), Jan 2025 FTC NPRM (pending), X deceptive/impractical-outcomes policy, X gambling policy US section, three-element lottery test for "mystery nuts", chargeback thresholds, the word "franchise"; OWNER items marked
- `revenue/business_packs_marketing/PACK_BUYER_MAP.json` — machine map tier → persona → handles → keywords → verdict; existing shelf → buyer → X role

FIVE FINDINGS THAT CHANGE SPEND:
1. Paid X cannot carry the $20 tier (net ~$19 vs typical CPC $0.50–2.00 at 1–3% conversion). $20 is the organic / upsell entry. Test $100 and $200 first, then $1,000; run $10,000 as lead-gen.
2. X's audience is 63–68% male, 25–34 the largest bloc, ~29% over $100k HHI: strong for the male builder/operator ($100–$1,000) and the SMB owner ($10,000); weak for the female 25–44 digital-products buyer (Etsy/TikTok). Female-skewed packs (yard-greeting rental) need other channels.
3. Copy law: prices yes, earnings never. X prohibits "get rich quick", "results within a specific period", and "economic opportunity" claims outright; FTC defines an earnings claim as any express or implied income figure. "$40 per bin-out, two hours Saturday" is a product description; "make $200 this weekend" is a violation.
4. Keep "the nuts" off the ads. US X policy treats lotteries and pay-to-play promotions as restricted-with-authorization; US lottery law is prize + chance + consideration regardless of framing. The guaranteed pack is the ad; the bonus, if mentioned, lives on the door in the owner's exact framing. Legal review is Bryce's.
5. Spend cannot be measured yet: Stripe Payment Links complete on stripe.com, so the X Pixel Purchase event needs a thank-you page we control. Build demand posted.

YARD-CARD ($100) BUYER: Truck-and-weekend Tyler, 20–35 male, vehicle + free weekends, sweaty-startup lane. Finding: assets read as $20–50 without the instance brand/door the law requires anyway; "yard card" collides with the yard-greeting rental vertical (different, female-skewed buyer) — door copy should say "yard-help route".

BUILD DEMANDS POSTED to `#build-demand` `C0BTRNE6Y58`: yard-card instance brand/door + rename; DESK candidate local-business website-service pack (TALLY showcase + SMB gap method + #sales price sheet); PLANT candidate yard-greeting sign rental pack; pack-door thank-you page with owner-filled X Pixel slot.

WHAT THE FIRST HOUR COST: every product-side channel read end to end (hub, #commons two pages, #business-packs, #build-demand, #products, #sales, #leads, #delegations, #todo, #shipped-builds, #needs-bryce, side channels); Windows Python needed `PYTHONIOENCODING=utf-8` to print the dumps; business.x.com and ftc.gov refuse plain fetch (402/403) and had to be read through the browser pane; the corpus had zero consumer-side buyer research, which is why this lane exists.

Slack lane: `#marketing-research` `C0BUFLK7TNY`. Hub claim `scout-marketing-research-20260902-01` (ts `1788325496.598399`). Not a Commons admission gate. Open door.
