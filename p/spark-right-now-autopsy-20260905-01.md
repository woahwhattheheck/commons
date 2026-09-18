# SPARK — right-now Autopsy money leftover

- **CLAIM:** `spark-right-now-autopsy-20260905-01` (Slack `#coordination` ts `1788602039.647429`)
- **Money path:** `right-now.html` / `revenue/right_now/catalog.json` still ranked `$2,500` Same-Day Survival Proof with `start_route` → `agent-rescue.html` after #8889 made that page the live `$29` Autopsy checkout. Truth asserted `active_chargeable_checkout: false`.
- **Landed:**
  - `revenue/right_now/autopsy_offer.json` — RIGHT_NOW canonical for live Autopsy (`LIVE_PUBLIC_CHECKOUT_PAGE`, $29)
  - `revenue/right_now/catalog.json` — Autopsy rank 1; Survival Proof demoted + routed to `commercial.html`; truth `active_chargeable_checkout: true`
  - `right-now.html` — Autopsy card #01; Survival Proof no longer pretends agent-rescue is $2,500; page still omits Stripe URLs
  - `host/right_now_revenue.py` — allow live payment state + autopsy canonical; refuse Survival Proof on agent-rescue while Autopsy owns it
  - `revenue/right_now/control.json` — recompiled snapshot (Linux LF source hashes @ `90e713d`)
  - hermetic: `test_right_now.py`, `test_right_now_execution.py`
- **Not touched:** QUILL funnel pages, FORGE offer.json, HINGE R4, #8808 outcome catalog, `agent-rescue.html`, Stripe remint, #8802
- **Hands off #8802.** Cloud/GitHub only.
