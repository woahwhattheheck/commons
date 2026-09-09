# Local promotion production desk

This dependency-free command converts one reviewed brand file and offer list into a consistent local web/social/print package. Active offers receive matching copy, price, expiry, landing page and real QR SVG. Upcoming offers are held. Expired offers remain in the audit calendar but disappear from every publishable surface on the next atomic rebuild.

```bash
python3 promotion_desk.py --brand examples/brand.json --offers examples/offers.json --as-of 2026-09-08 --base-url https://offers.example.test --out out
python3 -m unittest -v test_promotion_desk.py
```

`out/` contains web landing pages, social/print SVGs, QR SVGs, `expiry-calendar.csv`, and a source-hash manifest explicitly marked `LOCAL_EXPORT_ONLY_UNSENT`. Keep source files outside `out/`; the generator replaces only its own output tree after a complete staged build.

The fixtures are fictional. No customer channel, provider, sale, payment, or deployment is represented.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

