# Erdős 412: strict growth of the sum-of-divisors orbit

This is a bounded first-piece carrier for Conjectures.io Erdős problem 412. The current target asks whether for every `m,n ≥ 2`, the iterates of the sum-of-divisors map eventually meet. The sponsor page currently lists a $4,475 close bounty and zero published contributions for this problem.

## Reusable mathematical reduction

Let `σ(n)` be the sum of the positive divisors of `n`. If `n ≥ 2`, then `1` and `n` are distinct positive divisors. Hence

`σ(n) ≥ 1 + n > n`.

Therefore every `σ`-orbit started at `n ≥ 2` is strictly increasing. In particular, the iteration never falls out of the `≥ 2` domain and has no finite cycle or repeated value. Any proof of Erdős 412 may therefore reason about two strictly increasing divergent divisor-sum trajectories rather than arbitrary self-maps.

The included `script.lean` packages the one-step strict-growth lemma in the sponsor-allowed `Contribution.Erdos412SigmaGrowth` namespace. It deliberately contains no `sorry`, `axiom`, `native_decide`, unsafe declarations, or reserved `Bounty` namespace. **It has not been Lean-elaborated in this runtime**, because neither `lean` nor `lake` is installed here. It must be elaborated against the sponsor-pinned environment before promotion/signing/submission.

## Exact source identity

- Conjectures task slug: `erdos-412`
- Reward target: `fc-target:Erdos412.erdos_412`
- Current task-repo main observed: `d9a67b509c5a8b220ba262c1c7ce26f61f52763a`
- Reviewed pool parent linked by the generated sponsor index: `275ef4824c41d41f97ac4e9fff95ca471de9341d`
- Formal Conjectures source commit recorded in `source-metadata.json`: `8432eac998110a563e03df65a28c117e97c8c142`
- Source type SHA-256: `76232ceb7eac301b3c9a58bdf2e5f7fe16e3d9a81a9f299b0f56f2c493266557`
- Formalized task commitment shown by the public problem page: `b67be102b3ca663dffeb062aef9d303203a4a4474e6859e9237e6d31ebf8aa02`

## Deterministic regression

`python3 sigma_growth.py` independently computes divisor sums and emits `receipt.json`. The committed receipt checks:

- all 9,999 integers `2 ≤ n ≤ 10,000` satisfy `n < σ(n)`;
- 2,040 transitions covering seeds `2..256` and eight iterations each are strictly increasing;
- the canonical ordered transition stream has SHA-256 `1cfa64a2f0982817bb9a8839e0a70d3fc84d7c630cdee6a2ace6b394199fe269`.

The regression is evidence and a guard against transcription mistakes; the proof is the two-divisor argument above.

## Validation performed here

- `python3 -m unittest -v` — 4/4 PASS
- `python3 -O -m unittest -v` — 4/4 PASS
- `python3 -m py_compile sigma_growth.py test_sigma_growth.py` — PASS
- `receipt.json` SHA-256 — `e34de19807a1baa0a2960fb5ee9b2e0c57a894ff9cba5f32cd0cde26e631d374`

## Evidence ceiling / sponsor handoff

This is **not** a proof of Erdős 412, not a sponsor-accepted contribution, and not a payout claim. The sponsor workflow requires a self-contained Lean file to elaborate, then `contrib promote`, signing (including reward keys for reward eligibility), `contrib check`, and `contrib submit`. A worker with that exact environment should first run the included `script.lean`; if it elaborates, copy the Lean and `sources.md` into a fresh `contrib new erdos-412` draft, promote/sign, run the exact checks, and submit the resulting immutable contribution directory.
