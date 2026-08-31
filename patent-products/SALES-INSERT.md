# PATENT PRODUCTS — SALES INSERT

Drop this into a package. It is a catalog sheet, not outreach and not a quote.

**Door (no login, no clone to open):**
https://woahwhattheheck.github.io/commons/patent-products.html

Raw / pin: `patent-products.html` on current `woahwhattheheck/commons` main.
Work id: `patent-products-20260831-01`
Patent source: `muhl/docs/PROVISIONAL_SESSION.pdf` — 51 claims, sole inventor Bryce Muhlnickel. Cite, do not remint.

## What is sellable today

Three working software products, each a practical application of the patent family, each re-runnable from public main:

1. **GERMLINE — germ delivery / Instant Download.**
   Send the seed once; after that the wire carries only the change. Destination manufactures a byte-exact body, sha256-proven. Measured: 1-byte edit to a 1 MB body = injection under 1% of body size.
   Buyer pain: CDN/bandwidth spend, version distribution, edge sync.
   Proof command: `python3 -m unittest test_germline.py`

2. **MIRROR ORGAN — twin-state sync proof.**
   N copies manufactured by paste; one injection stream settles every twin to the same byte-exact state; drifted twins are named and fail closed.
   Buyer pain: replica/cache/config drift across a fleet, auditability.
   Proof command: `python3 -m unittest test_mirror_organ.py`

3. **WINNER FOLD — inverted return bandwidth.**
   Fan out to N lanes; only the winner rides home; losing lanes store zero. Return bytes are constant in lane count.
   Buyer pain: telemetry/search/auction fan-out return costs.
   Proof command: `python3 -m unittest test_winner_fold.py`

Full battery: `python3 -m unittest test_germline.py test_mirror_organ.py test_winner_fold.py` — 21/21 green at land time.

## How to sell it

- Fits the existing motion: **$199 one-day diagnostic** (run the buyer's own file pairs through GERMLINE and hand them the measured wire-ratio receipt) → **$2,500 bounded proof** (one real workflow on their data) → paired build.
- These products are the *paired build* behind procurement offers that name bandwidth, sync, or distribution failures (e.g. any lead whose workflow ships bodies that could ship injections).
- No new Stripe link is invented in this insert. When Master of Accounts gets a YES, use the existing verified rails or agency invoice/PO path.
- Customer-facing rule stands: never send a prospect to Commons/GitHub. This insert is internal; the offer carries exact product/outcome/scope/price/delivery in-message.

## What this does NOT claim

- Not a live `.mno` pulse, not a device actuation, not address 337, not a Titan walk.
- Not a filed patent — the provisional corpus is the working source; "not a filing receipt" is printed inside it.
- No buyers, cash, sends, or Stripe charges are claimed by this insert.
