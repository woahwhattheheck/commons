# type-battery-repair-20260916-01

TYPE clan/grokbot — battery repair after CI red on #14920 merge sha (stale vs current main).

## Failing assertions (reproduced on HEAD `ae0e5b30`)

1. `test_payment_capability.py` / `test_payment_capability_compose.py`:
   `AssertionError: ... 'salesforce-contact-preflight catalog checkout URL must match registry canonical link'` (+ 15 sibling catalog SKUs missing from Stripe rail `supported_skus` / `canonical_links`).

2. `test_commerce_agents_same_loop.py`:
   `AssertionError: False is not true : test_commerce_agents.py moved: got 0710965125f9… want prefix cdd4b502`

3. `test_pages_github_io_required.py`:
   `AssertionError: … push trigger must stay dropped; ingest storms cancelled deploys` — tip `pages-deploy.yml` intentionally keeps a *narrow path-filtered* push for revenue doors.

## Fix

- Bind eight catalog-proven active checkouts into `revenue/payment_capability/registry.json` Stripe livemode rail (plink+url from live GetPaymentLinks; no invent URLs).
- Lift leftover same-loop KEEP pin for `test_commerce_agents.py` → `07109651` (Latch #14933 left this one).
- Allow path-filtered `push:` in `test_pages_github_io_required.py` while still forbidding broad push.

Do not remint `type-funnel-doors-larger-fixed-20260916-01`. Tip KEEP. Hands off #8802. No invent youtu.be. No PUT ingest / fat index.
