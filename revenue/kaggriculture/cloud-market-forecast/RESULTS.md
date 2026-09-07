# Focused actual-state results

13 focused tests pass: 10 contract cases plus 3 direct comparisons with pinned engine
pricing, town consumption and no-future-work crop transitions. Zero full games and
zero replay transition reruns. FLORA owns integration and simulation ablation.

| Current observation | Current tomato / strawberry | Quote horizon | Tomato scenario range | Strawberry scenario range |
|---|---|---:|---|---|
| leader-day9 / step224 | 68 / 166 | 224 | 68–68 | 166–166 |
| leader-day9 / step224 | 68 / 166 | 409 | 88–88 | 139–197 |
| leader-day9 / step224 | 68 / 166 | 457 | 106–106 | 3–204 |
| leader-day17 / step430 | 94 / 176 | 430 | 94–94 | 176–176 |
| leader-day17 / step430 | 94 / 176 | 601 | 179–245 | 1–233 |
| leader-day17 / step430 | 94 / 176 | 649 | 188–319 | 1–244 |

Only the current-observation column is an observed historical price. All later
columns are counterfactual scenarios under current shop copies and existing crops.
They are not the actual later replay prices and are not target labels used as input.
The two future horizons per case assume planting today, first tomato/strawberry
availability after 8/10 days, then a one-action DROP/SELL delay at an available depot.
No new crop is inserted into predicted supply: FLORA must add its proposed planting
cohort explicitly if comparing investments.

At step224 no already-visible tomato cohort contributes projected tomato sales at
the selected horizons; this does not license reading later tomato planting actions.
Duplicate current pizza shops and the farmers market contribute tomato demand.
Strawberry ranges widen when uncertain care/harvest permits large existing cohorts
to enter the market. Animal output, private stocks, future purchases, future planting
and future shop draws remain omitted rather than misrepresented as known.

Per-case measured cloud Python 3.12 wall time: leader-day9 0.030782s, leader-day17 0.040973s.
These are single measured calls, not a runtime percentile or hosted-runtime guarantee.
Full per-tile contributions/contracts are in results/actual-state-cases.json.gz;
results/summary.json keeps the complete aggregate scenarios and assumptions.

Behavior checks cover copy counts/configured intervals, exact market phase boundaries,
fertilizer coverage on the preceding care day, capacity clipping, delayed harvest
versus prompt harvest, both farms, one-time WATER growth, last-action unreachable
maintenance, last actionable sale, hidden-input invariance and nonmutation.
The three engine comparisons use its exact loaded primitives, not a second game
simulator or a regeneration of accepted herd/plan studies.
