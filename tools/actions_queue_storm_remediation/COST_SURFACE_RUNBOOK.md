# Workflow cost-surface runbook

Prepared: 2026-09-17/18 UTC  
Builder: Z-Sol / GPT-5.6 Sol

## Why this exists

The 2026-09-14 queue-storm package already repairs one proven cause of duplicate
GitHub Actions work: unrestricted feature-branch `push` plus `pull_request`
CI. The current private-repository fleet is large enough that trigger repair
alone is not sufficient. We need a repeatable inventory of launch pressure
before adding more workflows or waiting for hosted capacity to return.

A connected-GitHub directory census on 2026-09-17/18 measured **541 workflow
files across nine private repositories**:

| Repository | Workflow files |
| --- | ---: |
| `smb-showcase-inventory` | 357 |
| `motel-ops-suite` | 83 |
| `aquatrace-lims` | 30 |
| `pack-market` | 26 |
| `LocalDeviceAgent` | 14 |
| `webmcp-pad` | 12 |
| `deathstar` | 11 |
| `charttrace` | 7 |
| `commons-ship-enforcer` | 1 |
| **Total** | **541** |

This is workflow-file count, not billed minutes, queued jobs, or dollar cost.

## Run

Use an ephemeral cloud checkout, not Bryce's owner-device disk:

```bash
python tools/actions_queue_storm_remediation/workflow_cost_surface.py \
  /work/smb-showcase-inventory \
  /work/motel-ops-suite \
  /work/aquatrace-lims \
  /work/pack-market \
  /work/LocalDeviceAgent \
  /work/webmcp-pad \
  /work/deathstar \
  /work/charttrace \
  /work/commons-ship-enforcer \
  --output /work/workflow-cost-surface.json
```

The scanner is local and read-only. It reads only top-level workflow files,
rejects symlinked workflow inputs, caps each workflow at 1 MiB, hashes exact
bytes, and emits JSON.

## Signals

The report distinguishes:

- unrestricted `push` + `pull_request` launch duplication;
- broad push/PR path surfaces;
- run-triggered workflows with no top-level concurrency;
- concurrency declarations that do not visibly cancel older runs;
- scheduled workflow and cron-entry counts;
- runner jobs without `timeout-minutes`;
- matrix jobs and conservative static matrix expansion when the axes are simple;
- direct runner jobs explicitly labelled self-hosted versus hosted-or-dynamic
  exposure;
- reusable-workflow jobs.

The scanner deliberately does **not** estimate dollars. A dynamic runner label is
not proof of GitHub-hosted billing, and a static matrix count is not runtime.
Use provider-authenticated billing evidence for dollar claims.

## Reduction order

1. Run this inventory and preserve the JSON receipt.
2. Run `github_workflow_fleet_audit.py` / `actions_queue_storm_fix.py` for the
   already-proven unrestricted push+PR repair.
3. Work largest fanout first: `smb-showcase-inventory`, then
   `motel-ops-suite`, then the 30/26-workflow repos.
4. Add cancellation only where newest-head supersession is semantically safe.
5. Add bounded job timeouts where missing.
6. Review matrices and schedules before adding more hosted launch surfaces.
7. Prefer path-scoped reusable checks over hundreds of product-specific copies
   when behavior is actually shared; do not weaken required validation.
8. Re-audit after every infrastructure batch and compare exact receipts.

## Proof scope

The implementation was developed in an ephemeral runtime and its full local
fixture suite passed 10/10 under normal Python and 10/10 under `python -O`.
The branch carries a compact six-case repository regression subset covering the
core launch-pressure, cancellation, timeout, matrix, reusable-job, exact-byte,
and symlink contracts.

No workflow files, provider plans, billing settings, queued runs, or customer
surfaces are changed by this scanner.
