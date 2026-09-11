# V3.1 H3/L3 no-late-sale-advance — Arlene factor gate

Evidence child for `riot/v3.1-lanes@dc1779ed79cd7fdd091187df1e8f0c4e5f185555` L3. This report does **not** claim an exact build of that branch. It tests the exact L3 call-site factor against the retained ready-to-submit V3.1 R04 package: `reserve_sales(...)` is unchanged before step 648 and is skipped at step >=648. That is the branch source seam reviewed at the E184 wrapper.

## Custody

- V3.1 ready-to-submit archive SHA-256: `e4e5a3acfe4984c89c22c7aa841b4ddd6efe4f4cd71e507d1dabecbb6e865849`
- official evaluator SHA-256: `e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c`
- loader SHA-256: `cd113a94ae99b03492502e425bdcf09c3db17a2aa2a8fd866f0d78caec9e311e`
- official engine members: `kaggriculture.py bc8a5487…`, `kaggriculture.json a82c89c1…`, `utils.py 537b627b…`
- Arlene SHA-256: `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`
- control wrapper SHA-256: `2f3ed65894e2c41398dccaf42738c6604e7e0c5ebf0d705bc4db1a16e258137e`
- candidate wrapper SHA-256: `0802b0d4f827c9b427a3a8431264035d9ff2b0eb47b3c4b7372b9ac1f3ef2867`
- seeds: `2611151001..2611151008`, both seats, 16 paired cells
- control wrapper was separately checked against the exact V3.1 `main.py` on seed 2027 versus Arlene and official starter; terminal scores matched exactly in both seats.

## Result

All 16 paired cells completed with no candidate/opponent failures. Every cell improved competitive margin:

- mean Δown: **+205.00**
- mean Δrival: **+0.25**
- mean Δmargin = Δown − Δrival: **+204.75**
- median Δmargin: **+183**
- range: **+110 .. +339**
- positive / tie / negative cells: **16 / 0 / 0**
- control wins / candidate wins: **16 / 16**
- lost wins / new losses: **0 / 0**

The exact per-cell scores are in `H3-ARLENE-GATE-20260911.json`.

## Source review finding

The L3 seam itself is appropriate: gating `reserve_sales()` at the E184 call site avoids creating new `sale_window_debts`, while `subtract_advanced_sales()` remains in the parent path so existing debt continues to settle. Native late tape SELL rows are not suppressed.

One evidence issue remains: `r04_no_late_sale_advance.REPORT["suppressed_steps"]` increments on every enabled callback at/after the threshold, even when `reserve_sales()` would have added zero quantity. Treat that counter as *gate opportunities*, not causal activation. Before an integration claim based on activation count, instrument avoided reserved quantity/rows (or paired returned-action drift) instead.

## Disposition

This is strong factor-level economics evidence for H3/L3 and supports spending the next gate budget on an **exact packaged branch build** and composition. It does not authorize default enablement, merge to the submitted package, or a Kaggle submission. Required next checks: exact branch-package gate; H4/H6 composition; causal activation/avoided-quantity trace; canonical manifest/provenance closure.
