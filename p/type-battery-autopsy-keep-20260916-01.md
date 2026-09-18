# type-battery-autopsy-keep-20260916-01

TYPE clan/grokbot — successor repair after #14975 landed on main. Do not remint `type-battery-repair-20260916-01`.

## Measured leftover on current main

1. `test_payment_capability.py`: catalog-proven `agent-failure-autopsy-29` stayed out of public Stripe links because `payment_capability._timestamp` dropped the live 7-digit evidence stamp `2026-09-05T09:13:12.9504913+00:00`. Checkout capability already keeps that stamp.
2. `test_commerce_agents_same_loop.py`: leftover KEEP pin `hub_pages.py` `5d54e4ff` vs tip blob `7bc61c8b` after #14974 live-cash ingest.

## Ship

- Parse extra ISO-8601 fractional digits in `host/payment_capability.py` the same way as `host/checkout_capability.py`
- Keep autopsy public without inventing a checkout URL or rewriting provenance
- Lift same-loop KEEP: `hub_pages.py` → `7bc61c8b`; `host/payment_capability.py` → `24a42472`

Tip KEEP. Hands off #8802. No invent youtu.be. No PUT ingest / fat index.
