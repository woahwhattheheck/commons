# TITAN V3 canonical closure diagnostics — SOL-CLOSURE

## Scope

This lane closes the stale single-current package that made otherwise bounded TITAN work fail at `python build_integrated.py --check`. It changes release diagnostics and republishes the existing canonical source tree; it does **not** change gameplay policy, feature configuration, Kaggle state, provider state, or spending.

The predecessor publication is pinned by SHA-256:

`17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`

`build_integrated.py --diagnose` is non-mutating. It compares the freshly rendered release with all three committed publication points and reports exact added, removed, changed, and unchanged runtime members. Existing verification error prefixes remain intact, with bounded member names appended for incident diagnosis.

## One-shot closure

The branch-only workflow performs this sequence from a fresh main parent:

```text
apply exact/idempotent diagnostics patch
focused unit contracts
non-mutating drift report (before)
deterministic canonical build
canonical --check
non-mutating drift report (after)
extract archive into a clean temporary directory
verify every SOURCE.json member hash and byte count
compile every packaged Python source
load main.py::agent from the extracted archive
preserve and hash-check the predecessor archive
commit only the enumerated closure paths
```

The workflow refuses an unknown `build_integrated.py` shape, an unexpected changed path, a dirty post-build diagnostic, a missing predecessor archive, a non-deterministic package, an unsafe tar member, or a non-callable extracted entrypoint.

## Truth boundary

A green closure proves package/source/pointer identity and extracted-archive structural execution. It does not claim a game result, a leaderboard score, a V3 promotion, or superiority over V1/V2. Score-facing HIRE-reserve, SELL-order, and broad playable-candidate lanes remain independently owned and must consume the closed artifact rather than inheriting historical game claims.
