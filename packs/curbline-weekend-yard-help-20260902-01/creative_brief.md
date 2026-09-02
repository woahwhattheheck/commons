# Creative brief — Curbline Weekend (SHOP instance)

SCOUT `scout-demand-instance-creative-brief-20260902-01` and
`scout-demand-yard-card-instance-20260902-01`, filled from GOAT's
`packs/_template/creative_brief.md`. Every row below is copied from the
source memos in `revenue/business_packs_marketing/` and then named for this
instance; no new number is invented. Prices yes. Earnings never. Agents do
not mint a pixel ID, spend ads, or invent a Stripe URL. Marketing execution
is Bryce; this brief is the cut, not the spend.

Source memos (not rewritten here): BUYER_TIERS §3 ($100 SHOP / Tyler card),
ADVERTISING_GENERAL §4b (Tyler hook bank) and §3 (channel plan),
PRICE_ANCHORS §2 ($100 shop row), FERTILE_GROUND §0 and §4 ($100 Tyler row),
MESSAGING_ANGLE §2–3.

## Buyer

- Tier: `$100 SHOP`
- Pack price USD: `100`
- Brand / door: `Curbline Weekend` / `packs/curbline-weekend-yard-help-20260902-01/index.html`
- One line (BUYER_TIERS §3): `Truck-and-weekend Tyler — 20–35, male, suburban or exurban, has a vehicle and free weekends, wants cash this weekend rather than a laptop business: "a route and a price sheet so I am working by noon Saturday."`

## Hooks

Three cuts. Spoken line is the first three seconds. Frame 1 is the first
visual. Cut 1 is the ADVERTISING_GENERAL §4b Tyler row verbatim; cuts 2 and 3
name this instance's own assets. No number appears that is not a price on the
price sheet or a time budget in the runbook.

1. Spoken: `A route, a price sheet, and you're working by noon.`
   Frame 1: `truck tailgate, bins, the price sheet taped to the door`
   Body (s 3–15): `flyer → door → bin-out, hands only, no faces needed`
2. Spoken: `Fifty cards. Two hours. Three prices.`
   Frame 1: `a stack of Curbline Weekend cards and a two-hour walk on a suburban sidewalk`
   Body (s 3–15): `the $40 / $60 / $80 sheet, then the phone script, then the invoice`
3. Spoken: `Weekend yard-help route. Not a greeting sign.`
   Frame 1: `the door with the words weekend yard-help route and the $100 pack price`
   Body (s 3–15): `card copy, route log, job checklist, then the mailto checkout line`

## Runtime

15–25 seconds. Call to action lands at 75–80% of runtime (about second 12–20
on a 15–25 s cut). One hook per cut. Captions on. Brand visible before the
CTA. UGC-style is allowed; produced brand video is not required. Hands and
screens; no faces needed.

## CTA

One spoken line with the pack price and the running cost next to it. The
instance's `running-cost.md` slot is still `Amount: OWNER_UNSET`, so the
line says so out loud; the itemised typical ranges in that file are for the
owner to paste from, not for the ad. No "for this price" line runs until the
owner pastes the running cost.

- Line: `One hundred dollars. Your route. The weekend running cost is posted on the door once the owner sets it.`
- Pack price USD: `100`
- Running cost USD: `OWNER_UNSET`

## Anchor

PRICE_ANCHORS §2 line for this tier. Research line until the owner pastes it
on the door; this brief does not write it onto the instance door.

- Line: `One route. One price sheet. Working by noon Saturday.`
- The number in the buyer's head (PRICE_ANCHORS §2): `$97 templates; $695 Starter Story` — the pack is one-tenth of the membership, and it is a route with a price sheet, not a database of other people's routes.

## Channel order

SCOUT demand: X + Rumble for Tyler. ADVERTISING_GENERAL §3 for $100: X
look-alikes + keywords first; Rumble pre-roll; Reddit optional. Spend stays
Bryce.

- Order: `X (look-alikes: sweatystartup, Codie_Sanchez, thepatwalls, starterstory, ShaanVP; keywords: lawn care business, pressure washing business, junk removal, door hangers, side hustle this weekend) → Rumble (pre-roll, trades / trucks / outdoors) → Reddit (r/SideHustle, r/sweatystartup) → Meta retargeting only`

## Launch metros

FERTILE_GROUND §0 and §4 for the $100 Tyler tier: year-round or long yard
seasons, single-family-lot density. Consumer $20–$200 can run in all fifty
states.

- Metros: `Phoenix, Nashville, Atlanta, Dallas–Fort Worth, Houston, Tampa, Orlando, Charlotte, Raleigh, Las Vegas, Kansas City, St. Louis, Denver, Indianapolis`

## Never say

Prices yes. Earnings never. No "done for you". No greeting-sign rental words
on the door. No client-count line. No promise that houses, accounts or a list
come with the pack; it ships the method, not the customers (16 CFR 437
posture). No payback. No "become your own boss" / "become a business owner"
until the owner pastes the ToS slots (`terms.md` is `OWNER_UNSET`). No "we
did most of the work" until the owner pastes the running cost. No nuts in
the ad. No results in a period. Checkout stays `OWNER_PASTE_REQUIRED` /
`NOT_MINTED`; the door's mailto stays the only route until a Payment Link is
pasted.

## UTM

Door and thanks page. `{channel}` is one of `x`, `rumble`, `tiktok`, `meta`,
`reddit`. The instance `sale_id` is unset until a sale is recorded, so the
slug stands in for `{sale_id}`. Agents do not fire the pixel.

- Door: `packs/curbline-weekend-yard-help-20260902-01/index.html?utm_source={channel}&utm_medium=paid&utm_campaign=curbline-weekend-yard-help-20260902-01&utm_content=door`
- Thanks: `packs/thanks.html?value=100&utm_source={channel}&utm_medium=paid&utm_campaign=curbline-weekend-yard-help-20260902-01&utm_content=thanks`

Marketing execution is Bryce. This brief is the cut, not the spend.
