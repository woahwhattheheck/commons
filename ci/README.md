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
