# Host-offload CI pipes

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
