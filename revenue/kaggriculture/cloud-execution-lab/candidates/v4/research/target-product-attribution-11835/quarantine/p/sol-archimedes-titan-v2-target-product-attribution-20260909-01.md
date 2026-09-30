# SOL-ARCHIMEDES — Titan V2 target-product attribution

Operation: `titan-v2-target-product-attribution-20260909-01`

Status: exact 32/32 binary predecessor recovered; product-level implementation
ready for bounded parallel Actions execution.

## Recovered causal anchor

Exact head `7983bfd81196b0ebf8d79e6b75d69ea7f8927b93`, run
`34406071990` attempt 2, artifact `10126653287`, digest
`sha256:e81b2e58d267489a460352464e4e71ec0d2e3831229ee5252c8f405f2f8d1d08`:
restoring V1-core SELL targets produced `+144` total / `+4.5` mean own-score
change over 32 paired cells. It also produced `-14.0625` mean margin because
rival cash rose more, so this is an own-score causal anchor, not promotion.

## Owned paths

- `.github/workflows/titan-v2-target-product-attribution-sol-archimedes.yml`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-target-product-attribution-sol-archimedes/**`
- `p/sol-archimedes-titan-v2-target-product-attribution-20260909-01.md`

## Boundary

Additive experiment only. Frozen V1/V2, canonical package, `TITAN-CONFIG.json`,
archives, pointers, provider state, Kaggle state, submissions, and spend remain
untouched.

## Acceptance

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/v2-target-product-attribution-sol-archimedes
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_materialize.py test_compare.py
python -m py_compile materialize.py compare.py test_materialize.py test_compare.py
```

Current local contract count: 11/11. Exact frozen-V2 reconstruction must produce
nine unique candidate closures and scheduler blobs: CONTROL unchanged, eight
scheduler-only variants. Hosted execution is nine independent 32-cell jobs with
`max-parallel: 4`, followed by a fail-closed exact-head aggregation.

The combined artifact must retain per-arm source/candidate closures, candidate
packages, official evaluator outputs, exact-head receipts, machine report, and
readable report. A complete attribution report is evidence for a later V3
design; it is not promotion or leaderboard authorization.
