# SOL-ARCHIMEDES — Titan V2 target-product attribution

Operation: `titan-v2-target-product-attribution-20260909-01`

Status: implementation ready for exact Actions execution.

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

The workflow must retain exact head, per-arm source/candidate closure receipts,
all official evaluator outputs, machine report, and readable report. A complete
attribution report is evidence for a later V3 design; it is not a promotion or
leaderboard authorization.
