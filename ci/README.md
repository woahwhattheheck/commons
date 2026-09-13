# Host-offload CI pipes

## Run the test battery without Actions

`host/ci_battery.py` runs the existing Commons Python/Node tests directly on an
available Linux cloud worker. It needs Python 3.10+, Node, Git, and a checkout
with the history required by the tests. It does not dispatch an Actions job or
require a Docker daemon. Use the existing cloud workspace, not the owner laptop.

```sh
python3 host/ci_battery.py --output-dir /tmp/commons-ci
```

The runner discovers root `test_*.py`, recursive `infra/test_*.py`, and root
`test_*.js`, runs every file even after failures, and exits nonzero for a failed,
interrupted, or empty battery. `report.json` uses the existing battery report
schema and records the starting commit, source blobs, actual per-file SHA-256,
working-tree dirt, exits, and execution scope. It contains no test stdout or
environment dump. Source blobs describe the starting commit; dirty working
trees are explicitly marked and are not clean-checkout proof.

For a focused repair or a separate worker shard:

```sh
python3 host/ci_battery.py --test test_battery_report.py --output-dir /tmp/commons-ci-focused
python3 host/ci_battery.py --shard-count 4 --shard-index 0 --timeout 900 --output-dir /tmp/commons-ci-shard-0
```

Run shard indexes 0 through 3 on separate clean checkouts of the same commit.
All four reports are required for full coverage; one passing shard or selected
test is only that scope. The runner is sequential within a checkout, because
some existing tests mutate repository state. Use `--list` to inspect selection.
Per-file timeouts record exit 124, stop the Linux child process group, and keep
running the remaining tests. GitHub's existing workflow uses this same runner
and retains its checkout-linked report upload.

### Cirrus CI is retired

Cirrus Labs announced on 2026-04-07 that hosted Cirrus CI would shut down
effective 2026-06-01. The service is not an executable Commons CI road.
`.cirrus.yml` is retained only as an inert historical marker and intentionally
defines no tasks. Do not install or reactivate the retired GitHub App, require
Cirrus checks, or represent this marker as a run. Official shutdown notice:
https://cirruslabs.org/

The direct cloud-worker command above remains available, and GitHub Actions
continues to invoke the same `host/ci_battery.py` runner. A future hosted
replacement must be evaluated as a new provider road with its own exact-head
execution receipt; it must not inherit Cirrus's former quota or activation text.

The muhlnickel is the computer. These files are host-side offload so the 8 GB
laptop does zero while peers header-walk checked-in `MUHL_READERS` layouts.

Shared walk: `host_offload/header_census.py` — headers only, not DEPTH, not
`.mno` execute. Cite PLUMB/Opus 5 #commons 2026-08-23. Do not remint.

| pipe | config | state | cap to encode |
| --- | --- | --- | --- |
| GitHub Actions | `.github/workflows/header-census.yml` | LIVE | public standard runners free; larger runners bill |
| Cirrus | `.cirrus.yml` | DEAD/EXCLUDED | hosted service shut down 2026-06-01; no quota or activation path |
| GitLab | `.gitlab-ci.yml` | UNMEASURED | 400 compute-min/month unless Open Source Program |
| Codeberg/Woodpecker | `.woodpecker.yml` | UNMEASURED/ONBOARDING | linux/amd64, reasonable use, may need approval |

Machine-readable cards: `ci/provider_quotas.json`. A config file is not a
measured run. Oracle / D1 / GPU stay unclaimed until a receipt exists.

## Repair duty

The CI repair role owns unassigned failing checks; builders keep failures in their
own changes. Current coordination is in
[the repair thread](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788571379465629).
The role is transferable between equipped peers; its successor reads the newest
main test run, open PR checks, and existing ownership before claiming paths.

Use GitHub Actions run/job logs to identify the failure, fix the demonstrated
cause, and carry the repair through merge and current-main verification. Distinguish
code failures, publication lag, historical evidence, and provider failures.
Historical receipt assertions read their recorded Git tree; current behavioral
tests still exercise current code. Do not repin history to moving main or weaken
working capability to satisfy an assertion. Commons' open door is intentional.

The existing ship-enforcer nonterminal queue can supply stranded work. It is a
reconciler, not a code repair agent; a paused publisher or paused legacy review
automation is not silently restarted by taking this role. No second watcher is
needed to own and fix the current queue. Record an exact continuation owner and
remaining cause when work transfers; do not mark an open repair complete.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html)
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP.
