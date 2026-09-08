# ARC-AGI-2 / 2026 deterministic baseline

A dependency-free symbolic baseline for the 2026 ARC-AGI-2 paid competition lane. It learns one task-local hypothesis from the supplied training pairs and applies it to each test input.

## What it does

- validates ARC grids (rectangular, 1–30 cells per side, colors 0–9);
- tries a fixed deterministic library of dihedral transforms plus crop/upscale/repeat/tile primitives;
- infers one global color remapping that must be consistent across every training pair;
- emits two distinct predictions when available and deterministic fallbacks otherwise;
- writes the required Kaggle `submission.json` shape: every task ID, every test output in order, and both `attempt_1` + `attempt_2`.

The current transform library is intentionally small. This is a measured baseline and packaging scaffold, not a claim of competitive ARC-AGI-2 performance.

## Run

```bash
python research/arc-agi-2-2026/arc2_baseline.py \
  /kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json \
  --output submission.json
```

Focused tests:

```bash
cd research/arc-agi-2-2026
python -m unittest -v test_arc2_baseline.py
python arc2_baseline.py synthetic_challenges.json --output /tmp/arc2-submission.json
```

## Competition contract pinned 2026-09-08

The Kaggle competition page requires `submission.json`; every task ID from the challenges file must be present; each test output has exactly two predictions named `attempt_1` and `attempt_2`; multiple test outputs stay in input order. Evaluation notebooks run without internet and must stay within the competition runtime limit. See the official ARC Prize 2026 ARC-AGI-2 competition page for current binding details.

## Next high-value solver work

1. add object/component extraction and relation-aware transforms;
2. add repeated-pattern, symmetry-completion, counting and separator hypotheses;
3. score hypotheses by training simplicity and ambiguity rather than fixed order;
4. evaluate against the public training/evaluation sets inside an allowed local/Kaggle environment and record actual pass@2 before making any score claim;
5. only then add heavier search/model components if they justify their runtime.
