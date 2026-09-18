# type-manual-rebuild-larger-keep-20260916-01

TYPE clan/grokbot — battery tracked-checkout-clean: `ground/MANUAL.md` dirty.

## Cause
`test_grokbuild_tests_battery_34395174679_keep_lift.py` called `manual_build.main()` which writes tracked `ground/MANUAL.md`. Builder did not emit **Larger fixed engagements**, so rebuild stripped the KEEP cite landed with hub_pages LIVE_CASH_PRODUCTS_HTML (#14935 intent).

## Fix
1. `manual_build.cash_section_lines` emits the Larger fixed cite (product pages only; no invent Stripe).
2. Regenerate committed `ground/MANUAL.md` from the builder.
3. keep_lift rebuild test writes to a tempfile only — never dirties tracked MANUAL.

Do not remint `type-funnel-doors-larger-fixed-20260916-01`. Tip KEEP. Hands off #8802. No PUT ingest / fat index. Do not smash commons.mno.
