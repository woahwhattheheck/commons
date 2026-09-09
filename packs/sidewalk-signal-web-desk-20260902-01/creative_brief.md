# Creative brief — Sidewalk Signal (DESK instance)

SCOUT `scout-demand-instance-creative-brief-20260902-01`, filled by the
instance owner (TALLY) from GOAT's `packs/_template/creative_brief.md`
(`f2953322`). Every row below is copied from the source memos in
`revenue/business_packs_marketing/` and then named for this instance; no new
number is invented. Prices yes. Earnings never. Agents do not mint a pixel
ID, spend ads, or invent a Stripe URL. Marketing execution is Bryce; this
brief is the cut, not the spend.

Source memos (not rewritten here): BUYER_TIERS §3 ($200 DESK card),
ADVERTISING_GENERAL §4b (hook bank, Lena/Dan row) and §3 (channel plan),
PRICE_ANCHORS §2 ($200 desk row), FERTILE_GROUND §0 and §4 ($200 DESK row),
MESSAGING_ANGLE §2–3.

## Buyer

- Tier: `$200 DESK`
- Pack price USD: `200`
- Brand / door: `Sidewalk Signal` / `packs/sidewalk-signal-web-desk-20260902-01/index.html`
- One line (BUYER_TIERS §3): `Laptop Lena / Desk Dan — 28–45, employed, household income $70–120k, comfortable with site or AI builders, wants a legitimate service business run from a laptop on evenings and weekends: "a service I can sell to local businesses, with the demo and the price sheet already made."`

## Hooks

Three cuts. Spoken line is the first three seconds. Frame 1 is the first
visual. Cut 1 is the ADVERTISING_GENERAL §4b row verbatim; cuts 2 and 3 name
this instance's own assets. No number appears that is not a price on the
price sheet or a time budget in the runbook.

1. Spoken: `Every business on this street has a broken website.`
   Frame 1: `a phone scrolling a real "online booking coming soon" page (anonymised; no business name on screen)`
   Body (s 3–15): `the Sidewalk Signal demo site (the owner-delivered SMB-Website-Showcase.pdf pages), then the four-offer price sheet ($1,500 · $2,500 · $4,000 · from $6,000), then the outreach e-mail with the subject line that carries no price`
2. Spoken: `Tap "Get a quote" on a local site. Watch it fail.`
   Frame 1: `a thumb tapping a quote button and the error state that comes back`
   Body (s 3–15): `the nine-signal worksheet filling in row by row (S1 broken form, S2 "coming soon", S4 2018 footer), then the daily loop from instructions.md: three checks, three first touches, one dated log line`
3. Spoken: `Everything the coaching tells you to build. Already built.`
   Frame 1: `the pack's file list on a laptop: instructions, worksheet, scripts, price sheet, delivery checklist, contract placeholder, paperwork checklist, week-1 calendar`
   Body (s 3–15): `open each file for one second, land on week1.md day 1, then the door with the price`

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

- Line: `Two hundred dollars, one time. Your desk. The monthly running cost is posted on the door once the owner sets it.`
- Pack price USD: `200`
- Running cost USD: `OWNER_UNSET`

## Anchor

PRICE_ANCHORS §2 line for this tier. Research line until the owner pastes it
on the door; this brief does not write it onto the instance door.

- Line: `Everything the coaching tells you to build, already built.`
- The number in the buyer's head (PRICE_ANCHORS §2): `$695–$1,095 Starter Story memberships; $997 for three months of side-hustle coaching` — the pack is a fifth of the coaching package and includes the demo, the price sheet and the outreach script the coaching would tell you to build.

## Channel order

SCOUT demand: X / TikTok for Lena. ADVERTISING_GENERAL §3 for $200: X
look-alikes + keywords first; Reddit; Meta retargeting. Spend stays Bryce.

- Order: `X (look-alikes: thejustinwelsh, gregisenberg, thedankoe, levelsio, marc_louvion, IndieHackers, starterstory, thepatwalls; keywords: web design business, start an agency, freelance web, local SEO, one-person business, solopreneur, AI website builder) → TikTok (organic "what's inside" post first, then Spark) → Reddit (r/smallbusiness, r/Entrepreneur, r/SideHustle interest layer) → Meta retargeting only`

## Launch metros

FERTILE_GROUND §0 and §4 for the $200 DESK tier: national on X/TikTok, 49
states; Connecticut excluded unless the pack is priced $199 (its
business-opportunity statute applies from $200 with a marketing program;
owner decision, FERTILE_GROUND §6 item 2).

- Metros: `Indianapolis, Columbus, Nashville, Kansas City, Phoenix, Charlotte, Tampa, Milwaukee, Pittsburgh — mid-size metros with dense small-business bases and thin web presence, where the 9/1 #leads sweep found broken quote forms and "booking coming soon" pages. Exclude Connecticut in geo targeting until the price decision.`

## Never say

Prices yes. Earnings never. No "done for you". No franchise or investment
words for the product. No client-count line (no number of clients per week or per month). No promise that customers, accounts or a list come with the pack; it ships
the method, not the customers (16 CFR 437 posture). No payback. No "become your own
boss" / "become a business owner" until the owner pastes the ToS slots
(`terms.md` is `OWNER_UNSET`). No "we did most of the work" until the owner
pastes the running cost (running-cost law). No nuts in the ad. No results in
a period. Checkout stays `OWNER_PASTE_REQUIRED` / `NOT_MINTED`; the door's
mailto stays the only route until a Payment Link is pasted.

## UTM

Door and thanks page. `{channel}` is one of `x`, `tiktok`, `meta`, `reddit`,
`rumble`. The instance `sale_id` is unset until a sale is recorded, so the
slug stands in for `{sale_id}`. Agents do not fire the pixel.

- Door: `packs/sidewalk-signal-web-desk-20260902-01/index.html?utm_source={channel}&utm_medium=paid&utm_campaign=sidewalk-signal-web-desk-20260902-01&utm_content=door`
- Thanks: `packs/thanks.html?value=200&utm_source={channel}&utm_medium=paid&utm_campaign=sidewalk-signal-web-desk-20260902-01&utm_content=thanks`

## Assets the cut needs (all on main or owner-delivered)

- `assets/showcase-manifest.json` names the two demo files (PDF walkthrough, 1080p workflow video) the owner delivers with the pack; they are the "demo site" frames.
- `assets/price-sheet.md`, `assets/gap-finder-worksheet.md`, `assets/outreach-script.md`, `instructions.md`, `week1.md` — the on-screen files.
- The door badge and anchor slot land with `scout-demand-door-sold-once-badge-20260902-01` once the peer blob pins on this door are lifted; until then the door shows price, inclusions and `NOT_MINTED` only.

Marketing execution is Bryce. This brief is the cut, not the spend.
