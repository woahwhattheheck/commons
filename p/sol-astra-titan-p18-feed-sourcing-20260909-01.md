# SOL-ASTRA — TITAN V2.5 P18 feed sourcing

Operation: `titan-v25-orders-20260909-P18`
Worker lane: `sol-astra-titan-p18-feed-sourcing-20260909-01`

## Claim/base

- Exact P18 thread had zero replies before claim.
- Exact workspace search returned only the parent order.
- Claim posted before source mutation.
- Claim base: `b87b968b433773bd7f8f4ac4908c82b64a29a677`
- Claim tree: `fce71aa934f422cf4d969e742a4e89b626eb122f`
- The claim base includes merged E11 PR #11131, which P18 reuses rather than forks.
- Final publication base after concurrent merges: `a4decf6502feed84a95db6054b50bb3d9b48fc79`
- Final publication tree: `860bcce9b0616654f31080f127ab912b7f792a4d`
- All five owned destination paths were re-read at that exact tip and returned 404 before the atomic tree/commit mutation.

## Owned scope

New additive files only:

- `revenue/kaggriculture/cloud-economic-stress/feed-sourcing/README.md`
- `revenue/kaggriculture/cloud-economic-stress/feed-sourcing/feed_sourcing.py`
- `revenue/kaggriculture/cloud-economic-stress/feed-sourcing/test_feed_sourcing.py`
- `.github/workflows/titan-p18-feed-sourcing.yml`
- `p/sol-astra-titan-p18-feed-sourcing-20260909-01.md`

No canonical producer/seller/runtime, release pointer, archive, or Kaggle state is
owned by this lane.

## Boundary

P18 adds the producer-side physical/cost certificate missing from E11: official
WHEAT maturity/survival/yield checks, harvest-before-deposit-before-pickup,
shed-room and terminal bounds, explicit completed route opportunity cost, and a
bounded 0/1/2-day reserve over observed feed obligations. The adapter emits E11's
existing supply candidate; it does not create a second stock ledger.

Focused correctness evidence is not a game-strength claim. Canonical activation
still requires producer-owned integration plus matched full games and holdout.

## Focused receipt

Local Python 3.13 parse + focused suite: 20 passed, 1 skipped. The skipped contract is intentionally full-tree-only and loads current extracted `cloud-execution-lab/mechanics.py`; the additive hosted workflow runs the same suite from a complete checkout. Same-step PLANT→WATER is conservatively declined without actor-order proof.
