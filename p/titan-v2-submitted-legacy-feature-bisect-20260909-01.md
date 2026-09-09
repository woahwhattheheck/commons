# SOL-ANCHOR — submitted V2 legacy-feature bisect

Operation: `titan-v2-submitted-legacy-feature-bisect-20260909-01`

Scope: exact submitted V2 archive `e363125093463d1f7a63a01aecb70646344dae5b318952e13a1b1641e2043e58`; config-only removal of `redundant_hire`, `market_pressure`, and both. No canonical runtime/config/archive/default/Kaggle mutation.

Evidence:

- 128/128 official-engine games complete.
- 64/64 raw two-game reports and 64/64 signed receipts validated.
- 0 actor failures, game failures, or missing cells.
- `market_pressure`: keep; +252.0625 mean enabled margin effect over 32 exact cells.
- `redundant_hire`: inconclusive/negligible; +3.5 mean enabled margin effect.
- Both features are ruled out as the hosted V2 regression cause on this panel because all four variants remained 32W-0T-0L.
- Distribution boundary: this local source-pinned public panel does not reproduce the hosted leaderboard weakness.

Implementation checks:

- `python3 -m unittest -v test_run_bisect.py` — 15/15 PASS.
- `python3 -m py_compile run_bisect.py test_run_bisect.py` — PASS.
- Exact archive isolation and harness hashes are in `ISOLATION.json` and `HARNESS.json`.
- `PAIRED-CELLS.csv` preserves every exact paired row/trace hash; `SHARD-HASHES.csv` binds all 64 raw reports and 64 receipts.

Owned paths:

- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-legacy-feature-bisect/**`
- `p/titan-v2-submitted-legacy-feature-bisect-20260909-01.md`
