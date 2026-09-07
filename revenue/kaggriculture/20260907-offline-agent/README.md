# Kaggriculture offline farm agent

A standalone Python entry for the [Kaggriculture competition](https://www.kaggle.com/competitions/kaggriculture).
Submit `main.py` only: it exports `agent(observation, configuration=None)`, uses
the standard library, and makes no network calls or external-model requests.

The farm manager coordinates workers, animal installation, feed pickup and
delivery, animal care, fertilizer collection, crop watering and harvesting.
It estimates the effect of production and town demand on future prices,
budgets Fibonacci-priced hiring, expands land only with sufficient runway,
and liquidates carried goods before the actual terminal action.

## Run and inspect

```sh
python -m unittest -v test_agent.py
python evaluate.py --output evaluation.json --seeds 1,17,101
```

The evaluator downloads three public source files from Kaggle's official
repository into an automatically removed temporary directory. No package
installation, Kaggle registration, competition data, credentials or third-party
model service is needed. The engine is pinned to
[`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`](https://github.com/Kaggle/kaggle-environments/tree/28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c/kaggle_environments/envs/kaggriculture).
Its interpreter and JSON specification are unmodified; its seed helper is
extracted from the matching upstream source. The explicit driver provides
configuration, per-player observations and the framework's terminal step.

Results include source hashes, seeds, both player positions, bank balances,
daily traces, action counts and measured call times. The opponent suite includes
the official starter and three policy ablations. These are local-interpreter
measurements, **not** Kaggle-hosted validation, leaderboard placement or a prize.
Independent opponent strategies and hosted replay results remain useful inputs.
Do not change the source pin silently when comparing runs.

## Entry and coordination

- Entry/team merge: September 23, 2026, 23:59 UTC.
- Final submission: September 30, 2026, 23:59 UTC.
- Ten prizes of US$5,000; final tournament play continues into approximately mid-October.
- Maximum five team members, five submissions/day, only the two latest agents
  active for final evaluation. Submission limit 100 MiB.
- Runtime: 1.6 vCPU, 6.5 GiB RAM, 8 GiB disk, no ingress or egress during games.
- Winner submission license: CC-BY 4.0; method and reproducible-code publication
  required. Follow current [official rules](https://www.kaggle.com/competitions/kaggriculture/rules),
  including data and team-sharing requirements.
- Competition entry/submission is coordinated by the main account session.
  This package does not register, accept terms, submit or contact the sponsor.

[Original work thread](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788752325435209).
The GitHub Actions workflow produces the exact standalone agent and full
evaluation report as downloadable artifacts. Existing owner-disk work is
untouched; tests run in ephemeral cloud compute.

License for this package: CC-BY 4.0. Attribution: TokenJunkieLabs / Bryce Muhlnickel.
Upstream Kaggle engine source retains its own Apache-2.0 terms and is fetched,
not republished in this package.
