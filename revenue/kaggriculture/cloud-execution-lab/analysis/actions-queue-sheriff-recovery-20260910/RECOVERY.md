# TITAN Actions queue-sheriff — historical recovery

This directory recovers the previously local-only 2026-09-10 Actions queue-sheriff donor packet without activating it on current Commons `main`.

## Recovered artifacts

- `titan-v3-actions-queue-sheriff.patch` — 36,862 bytes — SHA-256 `06b51eee95e9dfddcd94af1195784457a4de89b185f3405d4dc276a9f9a23d9a`
- `LIVE-AUDIT.md` — 4,858 bytes — SHA-256 `323720a7883d853f51d2bbfb7644e3072f90812e1a0b8994c6d8958b50258a5a`
- `SHA256SUMS` — the original packet checksum manifest.

The original checksum manifest also binds the component script/test/workflow and the split patch variants.

## Historical evidence

The audit observed a growing Actions queue (1,406 → 1,421 → 1,433 queued runs), 14 open pull requests, 20 in-progress runs, stale PR-associated checks, and broad workflow amplification. The donor's local proof recorded 22/22 focused tests passing, Python compilation passing, workflow YAML parsing passing, synthetic `git apply --check` and application passing, and applied-tree validation passing.

These observations are historical evidence from 2026-09-10, not a claim about the current queue.

## Current authority boundary

This recovery publishes only inert provenance under this additive analysis directory. It does **not**:

- install `.github/scripts/queue_sheriff.py`;
- add or alter any active workflow;
- cancel or dispatch any GitHub Actions run;
- change TITAN runtime, gameplay, config, archive, release pointer, provider state, Kaggle state, or submission state.

Any operational consumer must first re-read current `.github` workflow/script paths, current Actions queue behavior, current permissions, and current branch/PR topology, then adapt and revalidate this donor against today's `main`. The historical patch must not be applied blindly.
