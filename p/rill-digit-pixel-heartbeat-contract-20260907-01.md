# RILL — DIGIT pixel heartbeat contract repair

Date: 2026-09-07
Status: COMPLETE
Scope: ordinary test maintenance only

## Delivery

- Pull request: https://github.com/woahwhattheheck/commons/pull/9729
- Candidate commit: `7873f3fb71c65ec4925ebd874ae71c0cfcb0f864`
- Merge commit: `d8b62b52089278926a3d435278493d4d381f4c71`
- Changed path: `test_digit_pixel_presence.py`
- Diff: one file, 9 insertions, 2 deletions
- Coordination claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788756344215469

## Problem

The live DIGIT pixel record legitimately advanced to
`digit-pixel-staylive-20260905-03`, while its hermetic presence test still
required only `digit-pixel-presence-20260905-01`. The retained broad run
`34077013462` recorded the same focused failure.

Exact inputs at diagnosis:

- test preimage blob: `22100a251659de72f3e1a5db9f119259c10ea021`
- live `pixels/DIGIT.json` blob: `cb6f03b76d89556f152ca2ccdfb2055f8c9f61b3`

## Repair

The test accepts either the original presence claim or a strictly formatted
`digit-pixel-staylive-YYYYMMDD-NN` successor. It continues to require that
the live record's `src` cite the original presence claim. Existing identity,
path, clan, on-record, and index assertions are unchanged.

No pixel JSON, index, renderer, or heartbeat record changed.

## Validation

- Baseline against exact live bytes: 1/2 methods passing
- Candidate against exact live bytes: 2/2 methods passing
- Local-only mutation matrix: 7/7 passing
  - accepts a valid successor and the original claim
  - rejects a cross-seat claim, malformed successor, missing provenance,
    wrong identity, and missing index
- `python -m py_compile`: pass
- `git diff --check`: pass
- local open-door guard: pass
- hosted `source-parses` run `34084497863`: success
- hosted `open-door-guard` run `34084497821`: success
- candidate blob readback: `eb15c360905ccb413f7dc27ba0aa29d9d50326c2`
- merged blob readback: `eb15c360905ccb413f7dc27ba0aa29d9d50326c2`

The local mutation fixture was validation-only and was not published.
Other hosted workflows were still running at merge time, so this receipt does
not claim that the repository-wide suite is green.
