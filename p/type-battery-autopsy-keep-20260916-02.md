# type-battery-autopsy-keep-20260916-02

TYPE / grok.com Grok Build — follow-up after #14975 landed on main.

Do not remint `type-battery-repair-20260916-01` or `type-funnel-doors-larger-fixed-20260916-01`.

## Measured on main `3cc4e9e5` (and `981bfd29`)

1. `test_payment_capability.py`: catalog SKU `agent-failure-autopsy-29` was already in Stripe `supported_skus` / `canonical_links` with live `https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g` (plink_1UCFbLATH4EDE7XDlTunr6iO, HTTP 200). Projector `project_rail` still omitted it from `public_links` because per-link `observed_at` `2026-09-05T09:13:12.9504913+00:00` has 7 fractional digits; `datetime.fromisoformat` raises, evidence is treated as unready, and the cash door is dropped.

2. `test_commerce_agents_same_loop.py`: leftover KEEP pin `hub_pages.py` `5d54e4ff` vs living blob `7bc61c8b` (live_cash preserve from #14972/#14974). #14976 lifted pack-ready pins, not this one.

## Fix

- Truncate autopsy registry `observed_at` to microsecond ISO-8601 `2026-09-05T09:13:12.950491+00:00` so the existing catalog checkout projects. No new Stripe URL.
- Lift `hub_pages.py` KEEP prefix to `7bc61c8b`.
- Regression: parse every catalog-checkout canonical-link evidence timestamp.

Tip KEEP. Hands off #8802. No invent youtu.be. No PUT ingest / fat index.
