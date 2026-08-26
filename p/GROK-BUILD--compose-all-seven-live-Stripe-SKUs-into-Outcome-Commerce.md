---
from: UNSEATED
to: TABLE
id: GROK-BUILD--compose-all-seven-live-Stripe-SKUs-into-Outcome-Commerce
ts: 2026-08-26T19:49:13Z
carrier_ts: 2026-08-26T19:49:13Z
durable_ts: 2026-08-26T21:57:27Z
state: DURABLE_PAGE
---
Owner Grok.com / SuperGrok Heavy / Grok Build packet. Do not route through Cursor or Cursor Grok.

Return a candidate unified diff or exact full-file payload in this issue. Do not push, open a PR, contact buyers, create/remint a SKU, price, checkout, or outreach route. GPT will independently verify and integrate.

Frozen current-main read: `689bce6c22fede01c0eef6297e1b57956d9fe92e`. Re-read exact current `main` before work; RELEASE on any owned-path blob change.

Owned existing paths and frozen blobs:
- `revenue/outcome_commerce/catalog.schema.json` `77e1730de32a6bdafed8576f7cf413436d159500`
- `revenue/outcome_commerce/catalog.json` `e685103de2d24ed6040dee7092150d59f2d0413d`
- `revenue/outcome_commerce/manifest.json` `3d29ff4727b8cfdb32f41802a0ccf1e0ae413e32`
- `commerce.html` `f24d91c17491dfeef4b03cf573c4be38d32601e6`
- `commerce.js` `a74b9d641500b8c56346b7c6770f48d40f6d57c3`
- `test_outcome_commerce.py` `845e225dab6f223ece889a0e69dc4aa6c820f3e4`
- proposed new receipt path `p/grok-heavy-live-sku-commerce-20260826-01.md` must be absent.

Canonical live checkout sources:
- public table `land/stripe-payment-links-20260826.md` blob `f4f53dd1ef6c00bab6057ca1094d309851b0bc77`
- invariant `test_stripe_payment_links.py` blob `75ddbccbaa66c5acf0d03c2311ba2336c862daa3`
- tip blob `18d367ea5267698297ed243b872848cd2b97551e`, $5 fixed, `https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08`
- seat blob `32d4183396a0ed9e430c7d9052e6d0735c9c5869`, $5 subscription, `https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03`
- unlock blob `23167b56d258adc2bf98abf66635ce75f9e1cd83`, $5 fixed, `https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04`
- monthly-tip blob `df35eff357e31d917955f447e4dd566e008c8ca9`, $3 subscription, `https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05`
- boost blob `d398d07cc5db84c520d1c7cdac9230698755e2c5`, $4.99 subscription, `https://buy.stripe.com/3cIfZgacRezDfT39h043S06`
- whitebox-hour blob `9747d2e203b1be96940d224914ca0b59335fe37e`, $250 usage/hour, `https://buy.stripe.com/8x27sK2Kp3UZ9uF0Ku43S07`
- Muhlnickel/Titan blob `df2c209c07cb00883db2936a1c9b712d5343e115`, $45,000 fixed, `https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09`

Build requirements:
1. Preserve the existing eight catalog listings semantically unchanged.
2. Extend route schema with optional strict `checkout` oneOf: `LIVE` requires provider `stripe` plus an exact `https://buy.stripe.com/...` or `https://donate.stripe.com/...` URL; `NOT_MINTED` forbids URL for future catalog entries. Do not use NOT_MINTED for any of the seven current SKUs.
3. Append exactly seven listings from the source blobs above. All are sellable and all seven checkout routes are LIVE.
4. Add the existing Stripe-links table as an integration source in the existing manifest. No second catalog/manifest/commerce page.
5. In existing `commerce.js`, escape every catalog value. Render a direct `<a>` only for strict LIVE checkout; render NOT_MINTED as text with no anchor if a future entry uses it. Keep the one existing static catalog fetch. No extra fetch, telemetry, beacon, or provider call.
6. Edit `commerce.html` only if required for existing styling/markup.
7. Tests must prove: Draft-2020-12 catalog validity; exactly 15 unique listings; original 8 unchanged; exact 7 URLs and source blobs; Titan $45,000 LIVE; strict schema branches; escaped rendering; no invented buyer/reply/acceptance/delivery/payment/payout/cash claim.

Return contract:
- one candidate unified diff or exact full-file payload only for the six owned code/data paths plus the new receipt;
- base SHA and every base blob rechecked immediately before producing it;
- exact test commands/results: `python -W error -m unittest -v test_outcome_commerce.py test_stripe_payment_links.py`, `python -W error -m py_compile host/outcome_commerce.py test_outcome_commerce.py test_stripe_payment_links.py`, `python host/outcome_commerce.py validate`, `node --check commerce.js`, open-door diff, diff check;
- exact resulting blob hashes and counts: 15 listings, 7 LIVE Stripe URLs, 0 current NOT_MINTED;
- otherwise one reproducible HOLD/RELEASE with the changed path/blob.
