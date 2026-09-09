# Creative brief — instance slot

SCOUT `scout-demand-instance-creative-brief-20260902-01`. This file is the
shared template. GOAT owns `packs/_template/`; this is one new additive file.
Instance owners copy it to `packs/<instance>/creative_brief.md` and fill the
`OWNER_UNSET` rows from the buyer card for that instance's tier. Empty slots
stay `OWNER_UNSET`. Prices yes. Earnings never. Agents do not mint a pixel ID,
spend ads, or invent a Stripe URL.

Source memos (do not rewrite them): `revenue/business_packs_marketing/`
BUYER_TIERS §3, ADVERTISING_GENERAL §4b, PRICE_ANCHORS §2, FERTILE_GROUND §0.

## Buyer

- Tier: `OWNER_UNSET`
- Pack price USD: `OWNER_UNSET`
- Brand / door: `OWNER_UNSET`
- One line (BUYER_TIERS §3): `OWNER_UNSET`

## Hooks

Three cuts. Spoken line is the first three seconds. Frame 1 is the first
visual. Copy the matching row from ADVERTISING_GENERAL §4b, then name this
instance. Do not invent a new number.

1. Spoken: `OWNER_UNSET`
   Frame 1: `OWNER_UNSET`
   Body (s 3–15): `OWNER_UNSET`
2. Spoken: `OWNER_UNSET`
   Frame 1: `OWNER_UNSET`
   Body (s 3–15): `OWNER_UNSET`
3. Spoken: `OWNER_UNSET`
   Frame 1: `OWNER_UNSET`
   Body (s 3–15): `OWNER_UNSET`

## Runtime

15–25 seconds. Call to action lands at 75–80% of runtime (about second 12–20
on a 15–25 s cut). One hook per cut. Captions on. Brand visible before the
CTA. UGC-style is allowed; produced brand video is not required.

## CTA

One spoken line with the pack price and the running cost next to it. If
`running_cost_usd` is still `OWNER_UNSET`, say that out loud. Do not invent a
monthly expense. Do not run a “for this price” line until the owner pastes
the running cost.

- Line: `OWNER_UNSET`
- Pack price USD: `OWNER_UNSET`
- Running cost USD: `OWNER_UNSET`

## Anchor

PRICE_ANCHORS §2 line for this tier. Research line until the owner pastes it
on the door. Do not write it onto the instance door from this brief.

- Line: `OWNER_UNSET`

## Channel order

SCOUT demand: X + Rumble for Tyler / Owen; TikTok / Meta for Renee; X / TikTok
for Lena. Spend stays Bryce.

- Order: `OWNER_UNSET`

## Launch metros

FERTILE_GROUND §0 for this tier. Consumer $20–$200 can run in all fifty
states; $200 DESK excludes Connecticut unless the pack is priced $199.

- Metros: `OWNER_UNSET`

## Never say

Prices yes. Earnings never. No “done for you”. No franchise or investment
words for the product. No client-count. No “we bring you customers”. No
payback. No “become your own boss” until the owner pastes ToS. No nuts in
the ad. Checkout stays `OWNER_PASTE_REQUIRED` / `NOT_MINTED`.

## UTM

Door and thanks page. `{channel}` is one of `x`, `tiktok`, `meta`, `reddit`,
`rumble`. `{sale_id}` is the instance `sale_id`. Agents do not fire the pixel.

- Door: `?utm_source={channel}&utm_medium=paid&utm_campaign={sale_id}&utm_content=door`
- Thanks: `?utm_source={channel}&utm_medium=paid&utm_campaign={sale_id}&utm_content=thanks`

Marketing execution is Bryce. This brief is the cut, not the spend.
