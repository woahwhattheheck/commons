# SOL-SCALPEL — TITAN V3 config causal bisection

Operation: `titan-v3-config-causal-bisect-20260909-sol-scalpel-01`

## Why this lane exists

The canonical V2.5 source manifest records `new_full_games: 0` for the changed
archive while `operating_stock`, `idle_fertilizer`, `crop_release`, and
`early_capital` are enabled. Bryce separately reported that V2 appears to have
regressed and that V1 remains roughly 1,000 leaderboard points from first. The
immediate missing evidence is causal: current aggregate results do not say
which enabled feature, or feature interaction, costs outcomes.

## Owned additive paths

- `revenue/kaggriculture/cloud-execution-lab/analysis/v3-feature-bisect/feature_bisect.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v3-feature-bisect/test_feature_bisect.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v3-feature-bisect/README.md`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v3-feature-bisect/LOCAL-EVIDENCE.json`
- `.github/workflows/titan-v3-feature-bisect.yml`
- this receipt

No existing controller, producer, seller, runtime, config, archive, pointer, or
submission path is owned or modified.

## Delivered mechanism

The tool safely extracts exact archive bytes, creates single and bounded pair
config ablations, proves every non-config member is unchanged, and runs each
candidate through the existing process-isolated official evaluator on identical
`(opponent, seed, candidate_seat)` cells. It binds archive/member/candidate,
evaluator/loader/engine/opponent, command, report, and resume identities.
Analysis fails closed on any partial or incomparable grid and preserves paired
own/rival/margin/outcome/trace deltas plus non-additive pair effects.

The conservative screen can emit `ESCALATE_FULL_PANEL`; it cannot emit a release
or submission authorization.

## Local evidence

- Python compile: PASS.
- Unit/integration contracts: 19/19 PASS.
- Full fake-evaluator matrix → resumable run → exact paired analysis: PASS.
- Deliberately malformed archive, wrong SHA, candidate mutation, report swap,
  engine drift, failed cell, duplicate cell, missing cell, and unpaired
  Simpson-style cell selection: all rejected.

Exact commands and byte hashes are in `LOCAL-EVIDENCE.json`.

## Hosted screen

The branch workflow verifies the canonical release, reruns all contracts, binds
the current archive pointer at checkout, optionally includes preserved submitted
V2 archive `e3631250…`, and evaluates the current policy plus four single
removals and three bounded pair removals against reacting Arlene on seeds
`261140014,261140015`, both seats. The retained artifact includes the complete
matrix, raw evaluator reports, receipts, paired JSON, and Markdown.

Truth boundary: no hosted result is claimed in this receipt until an exact-head
workflow artifact is read back. No Kaggle action, provider spend, owner-PC
compute, default mutation, or promotion has occurred.
