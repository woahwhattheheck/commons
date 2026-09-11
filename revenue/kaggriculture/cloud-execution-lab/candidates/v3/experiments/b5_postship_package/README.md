# B5 CARROT post-#12494 package preview

This directory is an **additive, evaluation-only packaging preview** for B5 on the exact merged V3.1 tree `a6120d0ea1bdb75eb0da2239220efce551f624a6` (#12494: H4 strawberry top-up + rival-gated L3). It does not edit the live overlay, `apply_v3.py`, deterministic manifest/FILES receipts, package defaults, submission archive, provider state, or Kaggle state in the repository.

## Source authority

The gameplay predicate comes from source-green B5 #12499 exact head `15e8367e4d3fff41e7e6eb2d088327f558764454`, candidate Git blob `4e4f9d490332f075cf50df595cb7a067d6236066`, independently reviewed at `5177244500` as closing the malformed-input/whole-action source blockers. The preview helper keeps that atomic predicate and adds one production theorem: B5 is allowed only when `turnsPerDay` is the exact integer `24`; missing, nonstandard, or type-ambiguous timing fails closed to exact parent action identity.

Existing predecessor economics are motivation only: frozen Arlene was 16/16 positive at +89.125 mean paired margin and the direct exact-pre-#12494 V3.1 panel was 16/16 positive at +66.375. Those numbers are **not** rebound to H4 + rival-gated L3 by this preview.

## Preview integration theorem

`materialize.py` refuses any source tree whose live `apply_v3.py` or merged package receipt differs from #12494. In a detached copy only, it:

- installs the reviewed helper as `overlay/b5_carrot_fertilizer.py`;
- adds `b5_carrot_fertilizer = false` as a deterministic package key/Features field;
- applies B5 only after the fully composed R04 delegate returns, matching the evaluated “parent R04 first, B5 second” order;
- deliberately does **not** add B5 to `_v3_active`, so B5 cannot activate the R04 route by itself;
- records default-false seam metadata in the detached manifest.

The normal `build_v3.py` then regenerates `FILES.json`, overlay hashes, archive digest, and package contents inside that detached tree. No manifest hash is hand-authored as an authority claim.

## CI artifacts and next gate

The dedicated workflow emits generated package receipts plus two deterministic score-facing archives from the same materialized file map:

1. `control-a612.tar.gz`: current #12494 score-facing tuple, B5 off;
2. `candidate-b5-on-a612.tar.gz`: identical bytes except `TITAN-CONFIG.json` has `b5_carrot_fertilizer=true`.

The workflow proves that H4 (`r04_strawberry_topup=true`), rival-gated L3 (`r04_no_late_sale_advance=true`), sale horizon 8, sale-fertilizer, and every other current #12494 package member remain inherited. The archive pair is **evaluation input, not promotion authority**.

Next useful spend after exact-head CI/review is a paired current-stack D3 screen on pinned opponent bytes and the same seeds/seats, reporting B5 activation counts plus `Δown`, `Δrival`, and `Δmargin`. Any loss of the predecessor sign under the shipped H4/L3 stack or a materially different opponent is a HOLD/reject for default-on promotion. A landing PR, if justified later, must be a fresh direct child of the then-current `titan/v3.1-20260911` head and regenerate committed deterministic receipts normally.
