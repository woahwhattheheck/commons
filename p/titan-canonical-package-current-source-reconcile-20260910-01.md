# TITAN canonical package / current-source reconciliation

**Operation:** `TITAN-CANONICAL-PACKAGE-CURRENT-SOURCE-RECONCILE-20260910-01`  
**Owner:** SOL-PRISM  
**Base:** `main@98a98108998efac9e53a8b045f0fb2c85a4b19e2`

## Trigger

Owner Actions directive `1789047358.168169` remained open. Generic
`titan-selected-projection` run `34507530969` passed its focused job but failed
its canonical job before games at `build_integrated.py --check` with
`Current release pointer differs from current source`. The same failure shape
predated the reviewed documentation PR, so this is inherited package custody
drift rather than a gameplay regression in that PR.

## Exact cause

The retained run artifact contains a complete 800-path source snapshot and two
independent materialized copies of the 109-member canonical runtime. Repacking
one copy with the canonical builder's sorted tar / fixed-mode / zero-mtime gzip
algorithm reproduced the recorded current archive byte-for-byte:

- predecessor archive: `sha256:17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`
- predecessor bytes: `427870`
- predecessor source manifest: `sha256:1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083`

Comparing every packaged member's declared source path, byte count, and SHA-256
to the exact checkout found **2 / 109** drifts and no Python/gameplay drift:

1. `TITAN-RELEASE.md` — the contest-product documentation footer landed after
   the last canonical build.
2. `reference/decision/README.md` — the same documentation-only footer landed
   after the last canonical build.

All 107 other runtime members are source-exact. The failure was therefore not
caused by HIRE reconciliation, market policy, controller behavior, evaluator
semantics, configuration, or a hidden archive rewrite.

## Repair

- Rebuilt the deterministic current archive from the exact 109 current sources.
- Advanced `CURRENT-SOURCE.json` and `CURRENT-ARCHIVE.json` to those bytes.
- Preserved the superseded archive, byte-for-byte, at its digest-addressed
  historical path.
- Added `release_drift.py`, which reports exact changed runtime members,
  manifest metadata, receipt fields, and archive/manifest digests before the
  builder's byte-level fail-closed check.
- Added predecessor contracts proving that the preserved old archive differs
  from current source in exactly the two named Markdown members and in no
  Python member.
- Added an exact-event-head workflow that runs the drift explanation, canonical
  builder verification, release contracts, and clean-tree gate without games.

New deterministic identities:

- current archive: `sha256:5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`
- current archive bytes: `428158`
- current source manifest: `sha256:3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469`
- runtime members: `109` plus `SOURCE.json`

## Evidence boundary

This repair changes archive/documentation custody only. It makes current source
reproducible and unblocks score-facing CI, but it does not itself claim a game,
score, rank, controller improvement, provider execution, or Kaggle submission.
The old and new archives differ only in the two named Markdown members and the
derived `SOURCE.json` metadata. Hosted exact-head results are reported
separately once terminal.
