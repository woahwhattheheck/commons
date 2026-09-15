# Current-main disposition (2026-09-14)

Recovery publication for `V4-TERMINAL-FALLBACK-RAW-SLOT-COMPLETION-20260911-01`.

The attached source/test custody files are the exact completed artifacts from the original test session. They are preserved here for the single canonical TITAN V4 workspace; no sibling V4 branch or product was created.

Do **not** mechanically apply the inner production patch to current `main`. Fresh `main` at `66ee953a7cc7b4e6f0bc2cedd037288abdafd62b` has already changed `reference/titan-current/deadline_adapter.py`: terminal liquidation now filters market rows through `MARKET_PRODUCTS` before applying the market-order slice. That source no longer matches the original guarded preimage `664aa4f8a21368c388dfa6714406519b6535ef7f`.

Original evidence remains useful: the package records the pinned-engine raw-slot / minimum-one boundary witnesses, exact tested postimage, 25/25 normal + 25/25 `python -O` focused tests over 704 constructed terminal-state cells per mode, and 11/11 normal + 11/11 optimized compatibility checks. Treat those as historical source-pinned evidence, not a current-runtime activation claim.

Next consumer action: compare the current product-prefilter behavior against the package's row-position / lockstep invariant and only port a semantic delta if a current-engine witness still fails. Preserve current main ownership and do not run the legacy materializer.
