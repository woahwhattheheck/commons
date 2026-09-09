# Checkout rails placeholder

status: NOT_MINTED
provider: none-until-owner-pastes
instance: sidewalk-signal-web-desk-20260902-01
tier_usd: 200

Owner pastes live Payment Link.

Do not invent a `buy.stripe.com` or `donate.stripe.com` URL.
TYPE owns minting. A pasted link is intent, not authorization, settlement, payout, or cash.
Collected cash remains USD 0 until a dated receipt says otherwise.

This instance's checkout is its own. Do not reuse another customer's Payment Link as identical inventory.
If Stripe later fails closed, keep `mailto:tokenjunkielabs@gmail.com`.
Read and post stay free either way.

After-payment redirect → `packs/thanks.html?value=200` (owner sets this on the Payment Link). Pixel ID slot is owner-paste in `ground/BUSINESS_PACK_THANKS.json`; empty means no third-party script loads. Agents do not mint a pixel ID or spend ads.

When the owner pastes the link: put the URL on the `checkout.url` field in `manifest.json`, set `checkout.status` to the value the keep-sell ledger uses once it is proven chargeable, replace the mailto line in `index.html` with the link, and re-run `host/business_pack_desk_instance.py --write` so the checkout token in the fingerprint follows the real rail.

Refund policy on the door: owner decision, not written here. The terms-of-service percentage and partial-ownership slots Bryce asked for on 2026-09-02 live in `terms.md` (both `OWNER_UNSET`, `HOLD_COUNSEL`); under `ground/TJLABS_PACK_TERMS.md` the pack is not saleable until the owner pastes them and counsel clears, so a pasted Payment Link alone does not make this instance live.
