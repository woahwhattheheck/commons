# After-payment thanks door (X Pixel slot)

Cite SCOUT demand `scout-demand-pack-door-thanks-pixel-20260902-01`. Do not remint it.
Cite [business-pack-template-20260902](./business-pack-template-20260902.md) §5 / §5c. Do not remint the factory template id.

Shared door: `packs/thanks.html`
Pages: `https://woahwhattheheck.github.io/commons/packs/thanks.html?value=TIER`

- Checkout stays `OWNER_PASTE_REQUIRED`. No invented Stripe URLs.
- Pixel ID slot is owner-filled (`<meta name="x-pixel-id" content="">`). Empty = zero third-party scripts.
- `Purchase` value is the tier from `?value=` (`20` / `50` / `100` / `200` / `1000` / `10000` only).
- Do not mint a pixel ID, ads account, or spend from this leftover.
- Marketing stays Bryce.

Owner Stripe step: Payment Link → after-payment redirect → the Pages thanks URL with this instance's tier.
