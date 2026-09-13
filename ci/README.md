# Host-offload CI pipes

## Run the test battery without Actions

`host/ci_battery.py` runs the existing Commons Python/Node tests directly on an
available Linux cloud worker. It needs Python 3.10+, Node, Git, and a clean
checkout with the history required by the tests. It does not dispatch an Actions
job or require a Docker daemon. Use the existing cloud workspace, not the owner
laptop.

```sh
python3 host/ci_battery.py --output-dir /tmp/commons-ci
```

The runner discovers root `test_*.py`, recursive `infra/test_*.py`, and root
`test_*.js`, runs every file even after failures, and exits nonzero for a failed,
interrupted, empty, or dirty battery. `report.json` uses the existing battery
report schema and records the starting commit, source blobs, actual per-file
SHA-256, starting worktree state, exits, and execution scope. It contains no
test stdout or environment dump.

A dirty checkout fails closed before any test process starts, because executing
working-tree bytes while citing the clean `HEAD` commit is not authoritative
evidence. Commit, stash, or remove local changes before running the battery. The
starting-state check happens before output files are created, so a previously
absent output directory may live inside the checkout without falsely making its
own run dirty. A later run must remove or ignore that output first.

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

### Retired provider: Cirrus CI

Cirrus Labs announced on April 7, 2026 that Cirrus CI would shut down effective
June 1, 2026. That date is past: Cirrus is not an installable or executable CI
road for this repository. The stale `.cirrus.yml` configuration was removed,
and the provider inventory marks the road `DEAD/EXCLUDED`.

Do not install or re-enable the old Cirrus GitHub App, claim a Cirrus run, or use
archived Cirrus documentation as evidence of current capacity. The official
shutdown announcement is https://cirruslabs.org/. The direct cloud-worker
command above and the existing GitHub Actions workflow remain the supported
battery paths.

The muhlnickel is the computer. These files are host-side offload so the 8 GB
laptop does zero while peers header-walk checked-in `MUHL_READERS` layouts.

Shared walk: `host_offload/header_census.py` — headers only, not DEPTH, not
`.mno` execute. Cite PLUMB/Opus 5 #commons 2026-08-23. Do not remint.

| pipe | config | state | cap to encode |
| --- | --- | --- | --- |
| GitHub Actions | `.github/workflows/header-census.yml` | LIVE | public standard runners free; larger runners bill |
| Cirrus CI | — | DEAD/EXCLUDED | service shut down effective 2026-06-01; no capacity |
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
