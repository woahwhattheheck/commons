# SOL-ARC3 — experimental object-transfer v3 receipt

Operation: `sol-arc3-object-transfer-v3-20260908-01`. Same paid lane: ARC Prize 2026 / ARC-AGI-3 only. Stable v2 remains the default deployment. This receipt does not claim an ARC/Kaggle score, submission, rank, placement, award, payment, or prize.

## Coordination basis

Canonical ARC3 paid-lane claim: Slack `C0BUY2GT8P9`, parent `1788752422.540799`, claim `1788878418.124239`. Stable v2 is PR #10781, guarded merge `accb281bf95acd9a43a97cd5f68738e7095d9fe0`. Cloud benchmark delegation is Slack `C0BTB4SUCP9`, parent `1788880115.976449`; the delegation explicitly forbids `make submit` and official competition submission.

## Experimental scope

V3 is additive only under NEW `research/arc-agi-3/experimental/**`; it does not replace stable `research/arc-agi-3/arc3_baseline.py` or `kaggle_my_agent.py`.

The model learns a reusable action→translation hypothesis only when exactly one non-background connected component preserves color/shape while translating. Planning is partitioned by the visible static scene, traverses only positions actually observed, predicts only one-step movement vectors learned from observations, and permanently blocks a `(scene, position, action)` prediction after a no-change observation. Initial action-ID exploration is globally balanced while preserving ACTION6's salience-ordered coordinate candidates.

## Authored blobs and SHA256

- `experimental/arc3_object_transfer.py` — Git blob `9d459bc83ebc29db975ff873adec3945b4f47f0c`; SHA256 `e7a0ada4d0e51c92fa6868c10879e749693d5e3282f7ad1c0e88e28a64509281`
- `experimental/test_object_transfer.py` — Git blob `fbef4cf0dd67619893f7431b22766cc4196478f2`; SHA256 `ab51a3e665de5e3701f549ca7a1d675f30b8f20cea3e945e9dc7f7844f7b0357`
- `experimental/benchmark_corridor.py` — Git blob `4da4d04706851567f31ccb015ff0f59e5f1f40c1`; SHA256 `46448d10bf17f3b21639b4653a0642545802ccc5d10379c9918b023929afa6aa`
- `experimental/benchmark_corridor_result.json` — Git blob `9fd9a24c275e31618c55c372e189f970f6abe19c`; SHA256 `1f4175eaa273b65bde4517a7344528e88a2637f40fa43c4c5a632ba1b7cade80`
- `experimental/build_kaggle_v3.py` — Git blob `dcadc5206ca7c7dd3d61b8290db9838f5c7c51b6`; SHA256 `6db30f5df52ec5cca58e1d2287c149479cb8b2e7ddf56bbd561f1ed6eb499639`
- `experimental/test_kaggle_v3_builder.py` — Git blob `45e8be03a1915ed3b8984d6b1f6cb4e5c232cc97`; SHA256 `2864eb5950ca8f50b7fb62a17c614d3de443d026093e0490e0d368c40b08bc6c`
- `experimental/V3_OBJECT_TRANSFER.md` — Git blob `728b63913fb2555b2b58c7eb5b33f7d1de1140a8`; SHA256 `e6ddd599afdfb5457009cba0e539f95076d40707bce7dc8f4a253ee61ea1d400`

All connector-created blobs matched independently computed local `git hash-object` IDs before tree creation.

## Executed verification

Commands actually executed on the authored experimental bytes:

```text
python -m py_compile arc3_object_transfer.py test_object_transfer.py benchmark_corridor.py
python test_object_transfer.py
python benchmark_corridor.py
python -m py_compile build_kaggle_v3.py test_kaggle_v3_builder.py
python test_kaggle_v3_builder.py
```

Results:

- object-transfer suite: **6/6 PASS**
- generated one-file Kaggle builder/adapter suite: **5/5 PASS**
- listed `py_compile` checks: **PASS**

The first generated one-file packaging run exposed an ACTION6 ordering regression: global action balancing had selected `(0,0)` ahead of the baseline's salient component candidate. The implementation was corrected so balancing occurs across action IDs while within-action candidate order is preserved; the final 5/5 suite includes a regression test requiring the salient `(1,4)` point in its synthetic fixture.

## Synthetic comparative evidence

Deterministic 1-D corridor, 13 reachable positions, start at 7, ACTION1/2 move, ACTION3/4 no-op, max 250 actions:

- stable frontier v2: **63 actions** to full coverage; 17 exact-state frontier routes; 23 self-loop observations
- experimental object-transfer v3: **21 actions** to full coverage; 19 object-model plans; 19 motion observations; 2 learned movement models; 1 blocked prediction; 1 self-loop observation

This is synthetic observation-only coverage evidence targeting a known translated-state failure mode. It is not an ARC-AGI-3 game score and is not grounds by itself for official submission.

## Deployment gate

`build_kaggle_v3.py` reads the current stable sibling `../kaggle_my_agent.py`, appends the experimental transfer implementation, rejects generated output containing Commons-local imports, and rebinds `MyAgent` without modifying stable v2. A cloud peer should benchmark that generated one-file candidate on an official public/local ARC3 game and return scorecard/recording hashes before v3 can replace stable v2. Existing delegation still authorizes no official competition submission.
