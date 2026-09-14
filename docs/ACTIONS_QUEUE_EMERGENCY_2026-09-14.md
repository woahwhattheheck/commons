# GitHub Actions Queue Emergency — 2026-09-14

## Observed incident

A live API census during the incident found 1,826 queued workflow runs across
`commons`, `smb-showcase-inventory`, `motel-ops-suite`, and `pack-market`.
Sampled jobs remained queued for hours and then ended without executing a test
step. Hosted status was therefore unavailable/unknown rather than evidence of a
source failure.

## Shipped containment

`host/actions_queue_emergency.py` coordinates the existing
`host.actions_queue_cancel` safety boundary across the four repositories. It is
dry-run by default, uses explicit per-repository bounds, preserves one
create-exclusive receipt per repository and round, and stops on orchestration
errors or when no progress is possible. The underlying canceller still performs
all stale classification, branch/open-PR inventory refreshes, and the final
provider-state read.

Dry-run from a current Commons checkout:

```bash
python -m host.actions_queue_emergency --run-id dry-run-20260914-01
```

An authorized Actions-write operator may add `--execute`; the default remains
non-mutating. Review every per-repository receipt and the aggregate
`summary.json` before any later round. An accepted request is not proof of a
terminal workflow state.

## Queue-growth prevention

The accompanying `path-manifest` workflow change adds per-PR/ref concurrency.
Only a superseded run for the same lane is replaced; separate pull requests
retain independent validation.

## Truth boundaries

- Queue saturation or missing checks are not source PASS.
- A job that never reaches step 1 is not evidence that product tests failed.
- Local exact-byte proof remains local proof, not hosted green.
- Fail-closed HOLD outcomes are preserved and must be investigated rather than
  bypassed.
