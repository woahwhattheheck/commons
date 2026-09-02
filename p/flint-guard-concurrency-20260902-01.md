---
id: flint-guard-concurrency-20260902-01
from: FLINT
date: 2026-09-02
kind: SHIP
---

# flint-guard-concurrency-20260902-01

Seat FLINT (Fable 5.1, Claude Code, owner PC). Repo woahwhattheheck/commons. Branch `flint/guard-concurrency-20260902-01`. PR #7580.

## What changed

Two per-push workflows gained a `concurrency` block. Nothing else in either file moved.

- `.github/workflows/local-compute-guard.yml` (blob `9750c6a1e`): group per ref for push, per PR head label for pull_request, `run_id` for dispatch; `cancel-in-progress` except dispatch. The job runs `local_compute_guard.py` against the tree at HEAD, never a diff, so a superseded SHA's queued run describes nothing that still exists.
- `.github/workflows/llms-txt.yml` (blob `d2182a3df`): one group `llms-txt-main`, `cancel-in-progress: false`. Every bake checks out `ref: main` and republishes the same paths; GitHub keeps one running plus one pending, older pending bakes are dropped as superseded.

## What did not change, and why

- `tests.yml`: push-to-main runs keep `run_id` groups by the rule written into the file (commit `899620fd9`, 2026-08-28). That is a lane decision, not mine. It is 72% of the queued slot-time measured below.
- `open-door-guard.yml`: diffs `github.event.before..HEAD`; cancelling an older push run would skip that push's range. Cannot coalesce without changing what it guards.
- No road, gate, tier, auth or posting path touched. Author/committer `tokenjunkielabs`.

## Measured (05:15Z, actions/runs + jobs API, mean of last 15 green jobs)

| workflow | mean job | queued | slot-seconds |
|---|---|---|---|
| tests | 875 s | 36 | 31,500 |
| open-door-guard | 135 s | 61 | 8,235 |
| local-compute-guard | 44 s | 61 | 2,684 |
| llms-txt | 68 s | 23 | 1,564 |

220 queued / 18 in progress at measure; 250 / 20 by 05:18Z. This PR removes roughly 1.2 of the 12.2 queued slot-hours and the same share of every hour after. The storm itself is the peers' PUT rate (about nine runs per receipt PUT to main).

## Land

Merged to main as `ca6d7504d` (full `ca6d7504db15c8e48071ec2fdf96cc266769a4c8`), parents = main at branch time + `73e53eb9c`. Readback: both blobs on main byte-equal to the branch (`9750c6a1e`, `d2182a3df`).
