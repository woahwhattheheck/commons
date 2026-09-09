# SOL-BULWARK — TITAN V3 reserve-release activation audit

- Operation: `titan-v3-reserve-activation-audit-20260909-01`
- Exact parent: `01108a7cfa366e71214640885d3b076f9a2b997c` (PR #11691)
- Parent workflow run: `34403285293`
- Parent result: `NO_SIGNAL`, 8/8 complete paired cells, 0 trace changes, 0 score deltas
- Canonical/runtime/config/archive mutation: **none**
- Provider/Kaggle action: **none**

## Why this exists

The parent candidate's focused contracts passed, but its hosted development
workflow was green because `NO_SIGNAL` exits zero. Across eight complete cells
(Arlene and V1, two seeds, both seats), candidate and control returned identical
trace digests and identical scores. That is valid negative evidence, not an
advancing score result.

This child adds a behavior-preserving terminal telemetry wrapper and an exact
paired activation census. It runs 32 deterministic seeds against public Arlene,
both seats, with control and candidate on the same pinned official interpreter.
The wrapper returns the candidate action unchanged and writes diagnostics only
at the terminal step under `/tmp`.

## Questions answered

1. Did `reserve_release_certificate` run in complete games?
2. Which fail-closed reason dominated?
3. Did any certificate become eligible?
4. Did any returned action trace change relative to control?
5. If actions changed, did paired margin improve without a negative cell?

## Gate

- `UNREACHED`: no eligible certificate and no trace change.
- `ELIGIBLE_NO_ACTION_SIGNAL`: a certificate opened, but returned actions stayed identical.
- `INVALID`: traces changed without an eligible certificate or evidence/provenance is incomplete.
- `HOLD_*`: traces changed but at least one cell regressed or mean margin was nonpositive.
- `ADVANCE`: at least one trace changed, mean paired margin is positive, and no cell regressed.

Only `ADVANCE` exits zero. Every other result remains visible in retained JSON,
Markdown, per-seed evaluator reports, and one telemetry record per candidate
seat/game.
