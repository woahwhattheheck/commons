# V3.1 → V4 E05 joint-SELL causal ablation

This evidence-only carrier isolates one always-on source delta that is outside the submitted-V4 four-flag screen: PR #11053's bounded two-product SELL composition (E05).

## Why this seam

Submitted V3.1 source `a90d888f03987ef0b35cfd20ec3519c6144db08a` has no joint-plan composition path in `FrozenSelected`. Submitted V4 source `4af1113154e78c662780e6658cd920daac7902e3` does, and its source manifest attributes the component to E05 / PR #11053. That PR's merge receipt explicitly reported zero new full games/interpreter panels and no measured playing-strength gain.

This is **not** a V3.1 reconstruction. Control is the exact submitted V4 archive `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`. Treatment changes exactly one archive member, `frozen_selected.py`, by replacing the unique E05 pair-admission metrics call with `metrics=None`. The existing V4 guard then declines every two-product pair while the already-computed single-product optimizer/fallback and every other V4 byte remain intact.

## Custody

- Baseline archive is read once, SHA256-authenticated, and extraction occurs only from a private snapshot written from those captured bytes.
- Shared `joint-liquidity-bench/paired.py` is read once, authenticated against Git blob `fbc5e320b8a2ee63af11dc9856c956a679823409`, then compiled/executed from the captured bytes. The live path is never imported.
- Evaluator, loader, packer, opponent registry and opponent support are executed only from the helper's authenticated harness snapshot.
- Treatment construction fails closed if the exact V4 E05 import, pair-admission call, pair gate, or metrics provider drifts.
- The synthetic discriminator proves the intact pair gate selects a reachable joint candidate while the ablated gate leaves the already-selected single-product incumbent unchanged.

## Source gates

```bash
python -B -m unittest -v test_ablation test_paired
python -O -B -m unittest -v test_ablation test_paired
python -m py_compile ablation.py paired.py test_ablation.py test_paired.py
```

Local authoring receipt: 13/13 PASS normal, 13/13 PASS under `-O`, py_compile PASS. Exact-head CI remains authoritative after publication.

## Matched screen

From this directory on a Linux fleet VM with the pinned engine and exact submitted-V4 archive available:

```bash
python -B paired.py \
  --kg-root ../../../.. \
  --engine-dir <pinned-engine-dir> \
  --baseline <exact-v4-archive> \
  --output <fresh-output-dir> \
  --seeds 2051966578,1378040481 \
  --seats 0,1 \
  --opponents apex_v7,arlene_v14
```

The runner rotates arm order per cell and reports treatment-minus-control margin deltas. Results are causal-screen evidence only: no production/default/current-archive/pointer/Kaggle mutation and no automatic promotion.
