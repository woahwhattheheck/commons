# Economic policy comparison — 2026-09-07

The incumbent remains unchanged in `main.py` while candidates are evaluated.
All candidates use the same public observations and unmodified pinned official
interpreter as the incumbent. No runtime network calls, external data or model
service. This is not Kaggle-hosted evaluation.

## Development comparison

[Run34082876909](https://github.com/woahwhattheheck/commons/actions/runs/34082876909)
used seeds37,211,997 in both seats and compared four preselected hypotheses
against the unchanged incumbent and its compact22-animal opponent:

| Candidate | Versus incumbent | Versus compact22 |
|---|---:|---:|
| Lifetime marginal-price economics | 1/6 wins, mean margin-14,343 | 4/6 wins, mean margin-3,463 |
| Capacity28, maximum10hands | 6/6 wins, mean margin+4,088 | 6/6 wins, mean margin+2,216 |
| Forecast horizon20days | 1/6 wins, mean margin-8,972 | 0/6 wins, mean margin-17,750 |
| Complete more same-tile tasks | 1/6 wins, mean margin-1,571 | 0/6 wins, mean margin-4,915 |

Only the capacity candidate advances to the separately declared holdout set:
23,83,449,2027,65537, both seats. This choice was made before viewing those
results. Failed variants remain reproducible in `candidate.py` and `compare.py`;
they are not promoted merely because the added logic appears sophisticated.

## Why these candidates

The original three losses retained36animals and ended with zero inventory,
so they were not agent crashes, herd disappearance or failure to liquidate.
For example, seed37seat0 expanded from19 to36animals around days10–13,
made4,051 movement actions versus compact22's2,888, and finished5,045coins
behind. It was about9,820coins behind at day15. Seed37seat1 lost3,060 and
seed997seat0 lost172. These observations motivate reducing the marginal
land/labor burden, but do not themselves establish causation. Paired candidate
tests supply the intervention evidence; holdouts test whether the change
extends beyond the failure examples.

Instrumented comparisons record market-order pressure, unfed-without-buy
turns and daily prices/land/cash. Those counters are diagnostic, not automatic
proof that an order was dropped: affordability, ending rules and resource
state also matter.
