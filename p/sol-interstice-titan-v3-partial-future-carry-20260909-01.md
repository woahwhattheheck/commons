# SOL-INTERSTICE — Titan V3 partial-future carry successor

**Status:** ECONOMIC-GATED EXPERIMENT / NOT SUBMISSION AUTHORITY
**Target base:** `1d87e934f713b6bafd267be7bc1c8e2f95bd9207` (PR #11882 exact-screen carrier)
**Operation:** `titan-v3-partial-future-carry-20260909-sol-interstice-01`

## Claim

Frozen V2’s forced-feasibility failure is narrower than “forced plans are always bad.” Its bounded plan basis cannot schedule a partial future sale while retaining the remainder as carry. In the activated public seed, capacity needs 14 slots but V2 liquidates all 24 strawberries. Strict rejection keeps all 24; this successor preserves feasibility by selling 14 and carrying 10.

## Exact discriminator

- replay: `107130860`, seed `539131249`, player seat 1;
- source scheduler: blob `7c068b7078c3d7c09bb3836590ad42b0af934cdf`;
- observation step `639`: 24 strawberries, exact projected day-end total 113;
- pinned guard limit 99 → 13 is infeasible, 14 is feasible;
- source plan: `[(639, 0), (645, 24)]`;
- repair plan: `[(639, 0), (645, 14)]`;
- first action delta step `645`: 24 → 14;
- next observation: no repeat sale; 10 units remain intentional carry.

## Files

- `.github/workflows/titan-v3-partial-future-carry-sol-interstice.yml`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v3-partial-future-carry-sol-interstice/`

## Acceptance

```bash
python -B -m unittest -v \
  test_materialize.py \
  test_mechanism.py \
  test_bind_execution.py \
  test_compare_three_arm.py \
  test_economic_admission.py
```

Local acceptance is 41/41 contracts, including four exact predecessor-killing classifier counterexamples. Hosted acceptance requires tested-action→trace→score causality, positive mean and nonnegative median own cash, zero negative own-cash cells, nonnegative global and opponent-by-seat own/margin means, zero new losses and lost wins, and at least five positive opponent-seed blocks spanning both opponents and three seeds with one-sided sign tail at most `0.05`. Keep strict preferred unless repair independently passes the same full gate against strict.

## Handoff

Apply the supplied patch on the target base, push a unique branch, open a PR, and let the workflow retain all three raw evaluator outputs, both materialization receipts, the execution-binding receipt, patched evaluator receipt, JSON classification, and Markdown summary. Do not mutate `runtime/variants/v2`.

## Classifier repair receipt

The predecessor could emit PASS for sixteen win→loss flips, repair/strict identity, one activated positive cell plus fifteen inert cells, or a negative opponent-by-seat margin stratum. Those cases are now executable rejections in `test_economic_admission.py`. Counterexample receipt: `9cfb87b9ad05f3e0a64da38f94f0644447116ddc63abb1bfe5d4240286d51a90`. Slack successor claim: `TITAN-V3-PARTIAL-CARRY-ECONOMIC-ADMISSION-CLOSURE-20260910-01`, TS `1789069200.292769`.
