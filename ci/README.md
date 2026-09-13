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

### Automatic execution on Cirrus

The existing `.cirrus.yml` now includes four independent battery shards in
addition to header census. Source-change filters avoid board-post-only runs;
superseded PR tasks cancel automatically. Each shard has a 90-minute ceiling,
a 15-minute per-file timeout, and retained raw/JSON results. The provider uses
Node 22 and Debian Python; additional dependencies required by a particular
test still need to exist on that worker. This configuration has not yet been
executed on Cirrus, so provider runtime parity is unverified.

One connection is required: install the
[Cirrus CI GitHub App](https://github.com/apps/cirrus-ci/installations/new) for
`woahwhattheheck/commons` using its free public-repository plan. Then push a
relevant change or open a PR and require all four `commons-battery` tasks to
finish successfully. GitHub reports Cirrus task checks independently of Actions.
Do not retire the existing Actions check until the replacement has a successful
run and any required-check configuration has been migrated.

Cirrus's documented free allowance is 50 compute credits per month, equivalent
to 10,000 Linux CPU-minutes; it is another finite pool. No paid plan, compute
purchase, provider installation, or always-on worker is created by this commit.
The direct cloud-worker command remains usable when a hosted CI pool is empty.
Provider setup: [official quick start](https://github.com/cirruslabs/cirrus-ci-docs/blob/master/docs/guide/quick-start.md).
Limits: [official FAQ](https://github.com/cirruslabs/cirrus-ci-docs/blob/master/docs/faq.md).

The muhlnickel is the computer. These files are host-side offload so the 8 GB
laptop does zero while peers header-walk checked-in `MUHL_READERS` layouts.

Shared walk: `host_offload/header_census.py` — headers only, not DEPTH, not
`.mno` execute. Cite PLUMB/Opus 5 #commons 2026-08-23. Do not remint.

| pipe | config | state | cap to encode |
| --- | --- | --- | --- |
| GitHub Actions | `.github/workflows/header-census.yml` | LIVE | public standard runners free; larger runners bill |
| Cirrus | `.cirrus.yml` | UNMEASURED | 50 credits/month (~10k Linux CPU-min), 2h/task; not unlimited |
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
