# Workflow cost-surface runbook

Prepared: 2026-09-17/18 UTC
Builder: Z-Sol / GPT-5.6 Sol

## Measured fleet shape

A connected-GitHub directory census measured 541 workflow files across nine
private operating repositories:

| Repository | Workflow files |
| --- | ---: |
| smb-showcase-inventory | 357 |
| motel-ops-suite | 83 |
| aquatrace-lims | 30 |
| pack-market | 26 |
| LocalDeviceAgent | 14 |
| webmcp-pad | 12 |
| deathstar | 11 |
| charttrace | 7 |
| commons-ship-enforcer | 1 |
| **Total** | **541** |

This is workflow-file count. It is not billed minutes, queued jobs, or dollar cost.

## Purpose

The existing queue-storm remediation already handles a proven source of
duplication: unrestricted feature-branch push plus pull-request CI. The companion
`workflow_cost_surface.py` measures the broader launch surface before more
workflows are added or hosted capacity returns.

It is local and read-only. It scans checked-out top-level workflow files,
skips symlinks, limits input size, hashes exact bytes, and emits JSON.

## Run

Use ephemeral cloud checkouts rather than Bryce's owner-device disk:

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

## Signals

The report exposes:

- unrestricted push + pull-request launch duplication;
- broad push/PR path surfaces;
- run-triggered workflows without top-level concurrency;
- concurrency declarations without literal cancellation;
- scheduled workflows and cron-entry counts;
- direct runner jobs without timeout-minutes;
- matrix jobs and conservative static matrix expansion for simple axes;
- explicit self-hosted labels versus hosted-or-dynamic runner exposure;
- reusable-workflow jobs.

Dynamic/interpolated runner labels are deliberately not classified as explicit
self-hosting. Complex matrices do not receive an invented multiplier.

## Reduction order

1. Preserve one baseline JSON receipt.
2. Work largest fanout first: smb-showcase-inventory, then motel-ops-suite,
   then the 30/26-workflow repositories.
3. Apply the existing queue-storm push+PR repair where mechanically valid.
4. Add cancellation only where newest-head supersession is semantically safe.
5. Add bounded job timeouts where absent.
6. Review schedules and matrices before adding more hosted launch surfaces.
7. Prefer shared/reusable checks over hundreds of copies only when behavior is
   genuinely shared; do not weaken validation.
8. Re-run the inventory after each infrastructure batch and compare exact bytes.

## Proof and authority

The v2 implementation was exercised in an ephemeral runtime with 7/7 focused
tests under normal Python, 7/7 under python -O, and py_compile PASS. The GitHub
connector blocked creation of the repository regression file, so this package
does not claim an on-branch test artifact for v2.

The tool does not mutate workflows, Actions state, provider plans, billing,
queued runs, credentials, or customer surfaces. It deliberately does not
estimate dollar cost; provider-authenticated evidence remains required for
billing claims.
