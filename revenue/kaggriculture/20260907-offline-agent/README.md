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

## Licensing

Owner-authored code, tests and documentation in this package are available
under **MIT OR CC-BY-4.0**, at the recipient's choice. Both grants are offered;
the MIT option does not withdraw or alter the existing CC-BY 4.0 grant.

- [MIT license](LICENSE-MIT.txt): an [OSI-approved software license](https://opensource.org/license/mit)
  permitting commercial use, modification and redistribution under its terms.
- [CC-BY 4.0 license](LICENSE-CC-BY-4.0.txt): retained for the competition's
  specified winning-license requirement. Creative Commons permits
  [alternative dual licensing](https://creativecommons.org/faq/#can-i-enter-into-separate-or-supplemental-agreements-with-users-of-my-work).
- [Scope and attribution](LICENSE): Bryce Xavier Muhlnickel / TokenJunkieLabs.
  Third-party material is excluded from these owner-issued grants.

This addresses the distinction between the public-code-sharing requirement
for an OSI-approved license and the separately stated CC-BY 4.0 winning license.
It does not represent CC-BY 4.0 itself as an OSI-approved software license.
Under the current [competition rules](https://www.kaggle.com/competitions/kaggriculture/rules),
public code must also be shared on the competition forum or a Kaggle notebook.
The account session handles that publication; a GitHub merge alone is not
a Kaggle publication or submission receipt.

Upstream Kaggle engine source, specification and seed helper retain their own
[Apache-2.0 license](https://github.com/Kaggle/kaggle-environments/blob/28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c/LICENSE).
They are fetched for evaluation, not republished or relicensed by this package.
Preserve upstream notices when using or redistributing upstream material.
No competition data or other third-party code is relicensed by this grant.

## Recorded evaluation

[Cloud run 34081544288](https://github.com/woahwhattheheck/commons/actions/runs/34081544288)
tested source commit `9e90e9b819f495684a38272534d89837969437c9`:
eight contract tests passed, 24/24 wins on seeds 1, 17 and 101 in both player
positions against the official starter and the three policy ablations.
The slowest measured agent call was below 4 ms on that runner.
This establishes the recorded local-interpreter comparison only; it is not an
independent-opponent tournament or hosted acceptance result. The workflow also
tests new seeds 37, 211 and 997 after landing, reads fresh main, compares package
bytes, and runs the repository's terminal audit.

## Current policy improvement

`main.py` now limits the marginal herd to28 animals and10 daily hands. The
previous45/48 incumbent remains byte-identical and runnable in
`incumbent_20260907.py`. On separately reserved seeds23,83,449,2027,65537,
both seats, the selected policy beat that incumbent10/10 (mean+6,454.1coins).
It did not dominate compact22:4/10 wins, mean-61.9coins. See
[ECONOMICS.md](ECONOMICS.md) for all candidates, rejected regressions, original
loss diagnostics, exact cloud runs and limitations. This remains a local
official-interpreter result, not hosted placement.

`compare.py` reproduces experiments against the frozen incumbent:
`python compare.py --variants compact_capacity --seeds 23,83,449,2027,65537 --output comparison.json`.
Experimental `candidate.py` is not the submission file. Submit `main.py` only.
