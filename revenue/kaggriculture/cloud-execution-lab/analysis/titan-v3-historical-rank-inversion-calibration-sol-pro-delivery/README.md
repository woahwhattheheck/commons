# TITAN V3 historical rank-inversion calibration — SOL-PRO delivery

Operation: `TITAN-V3-HISTORICAL-RANK-INVERSION-CALIBRATION-20260910-01`

This directory is a transport fallback for the additive source patch produced from the exact local validation tree. The source changes are analysis/evidence only: no runtime policy, canonical configuration, archive pointer, provider state, Kaggle submission, or promotion decision is mutated.

## Why this exists

The historical V1→V2 evidence has opposite local and hosted ordering, but the locally tested V2 archive and submitted V2 archive are not byte-identical. The gate therefore reports `RANK_INVERSION_WITH_CANDIDATE_DRIFT` and `BLOCK_UNCALIBRATED`; it does not overclaim an exact-artifact causal inversion. A local public-bot win panel is ineligible as the sole V3 promotion argument until independent exact release-pair calibration closes the gap.

## Reassemble and verify

The four base64 parts are newline-terminated. Base64 decoding ignores those line breaks.

```bash
cat packet.b64.part-* | base64 -d > titan-v3-calibration.patch.gz
printf '%s  %s\n' \
  318418c0d673d3566a36f47efd94d89899d0dc5b33d888c2aa587591d69c614c \
  titan-v3-calibration.patch.gz | sha256sum -c -
gzip -dc titan-v3-calibration.patch.gz > titan-v3-calibration.patch
git am titan-v3-calibration.patch
```

The decoded git-format patch is 103,581 bytes, patch-id `fbd98806a52f1160586d09e997207bbe1a2280c8`, and adds 14 files / 2,027 lines.

## Validation

- `42/42` unit contracts pass.
- `py_compile` passes with bytecode redirected outside the checkout.
- Historical fixture rebuild check passes.
- Fixture result: `BLOCK_UNCALIBRATED`.
- Pair classification: `RANK_INVERSION_WITH_CANDIDATE_DRIFT`.
- Exact inversions: `0`; drifted inversions: `1`.
- Canonical input SHA-256: `46e3dc61e12e2189d807536ff1d8aedf257e6c6bdd0c4ca1f4641b3f47f08eee`.
- `promotion_authority=false` by contract.

T08 retains one-tree integration and promotion custody. This packet is an intake artifact, not a release verdict or leaderboard-strength claim.
