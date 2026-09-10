# Threat model

## Defended

- **Pointer-only promotion:** changing `CURRENT-ARCHIVE.json` without a matching
  champion transaction is blocked.
- **Ledger-only promotion:** changing the champion declaration while leaving the
  selected bytes alone is blocked.
- **Archive aliasing or replacement:** active and historical archives are hashed;
  the historical filename is derived from the digest.
- **Source drift:** the selected source manifest is hash-checked and bound into
  every measured champion after bootstrap.
- **Partial-panel survivorship:** the gate report must cover the exact declared
  Cartesian grid, both seats, and the minimum 192 baseline/candidate cells.
- **Report fabrication by omission:** all required checks must exist exactly once
  and pass; every evidence input is rehashed, byte-counted, and required to carry
  the hardened single-open private-snapshot binding.
- **Candidate-side gate weakening:** the promotion report is replayed using the
  paired-game gate from the trusted base checkout.
- **Policy ratchet reversal:** grid floors and required checks may be strengthened
  but not weakened; policy changes cannot accompany a pointer transition.
- **Parser/path ambiguity:** duplicate JSON keys, NaN/Infinity, traversal,
  backslashes, symlinks, oversize inputs, and unknown schema keys fail closed.
- **Unsafe installation:** the first ledger commit may not change the active
  pointer and must match the exact bootstrap champion frozen in policy.

## Residual controls

A required branch-protection status is still needed to make this workflow
unskippable at repository policy level. Repository administrators can always
replace workflows or bypass branch rules. The guard therefore emits an auditable
machine verdict but does not claim to be stronger than repository governance.

The paired-game gate proves only the declared panel under its frozen policy. It
does not eliminate opponent leakage, multiple-hypothesis bias, invalid gameplay
semantics, or leaderboard distribution shift. Distinct development and holdout
panels plus official-engine transition oracles remain necessary.
