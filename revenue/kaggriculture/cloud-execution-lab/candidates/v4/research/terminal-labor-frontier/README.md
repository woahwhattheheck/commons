# TITAN V4 terminal labor frontier

Wide lane: convert the final-day HIRE-cost reset into a measured marginal labor decision that feeds the existing native terminal router. This is **not** a fixed `HIRE x16` policy and it does not create a second V4/controller.

## Engine facts bound before building

Pinned official interpreter blob: `3c202c7ee921da239356789e266b694635103fc4` (`reference/engine/kaggriculture.py`). Pinned current terminal planner blob: `5010fc03966f31a9b7139d25996d3f713080bf25` (`reference/titan-current/terminal.py`).

- HIRE cost is `farmHandCostMult * fib(hires_today)` with `fib(0..)=1,1,2,3,5,...`.
- 16 hires from a fresh day cost **2583**, correcting the `~1583` Slack estimate. Ten cost **143**.
- The engine executes at most 10 market rows per turn by default; fixed `HIRE x16` therefore requires multiple callbacks, not one row batch.
- HIRE is processed after current unit actions and creates a hand for the next callback.
- `hands`, per-hand inventories and `hires_today` reset at EOD. The preserved terminal contract has final executable decision 718; there is no later decision after a final-day reset.
- Current `terminal.overlay` starts at final-day hour 2 (step 698 under defaults) and automatically consumes every observed hand. Therefore final-day hour 1 (step 697) is the clean single-callback composition seam: new hands exist exactly when the current terminal planner starts.

## Source contract

`terminal_labor_frontier.py`:

1. Runs only at the hour-1 seam (`697` under default `720/24`).
2. Simulates current own unit rows first with the injected official mechanics, including the engine's atomic oversubscribed-seed veto.
3. Accepts only an all-HIRE incumbent market prefix. It deliberately refuses SELL/BUY/LAND rows instead of treating requested receipts/costs as realized funding.
4. Replays incumbent HIREs with exact `_hire_cost`/`_do_hire` before measuring additions.
5. Calls the existing `terminal.assign_routes` for the unchanged baseline and for each additional funded hand up to the real raw-market capacity.
6. Reports gross current-quote route gain, cumulative exact hire cost and net current-quote gain for every reachable count.
7. `propose_terminal_hires(..., enabled=False)` is exact-parent identity. When enabled, it appends only the hire count with the largest qualified marginal net; it never assumes a fixed mass-hire count.

This is source/evidence infrastructure only. Current quotes are not future rival prices and a positive synthetic frontier is not field EV. Promotion requires actual native both-seat games with engagement logs, realized fills/cash, terminal sold inventory and the current gauntlet/holdout process. No production/default/archive/Kaggle change is made here.

## Focused validation

Run from this directory:

```bash
python -B -m unittest -v test_terminal_labor_frontier.py
python -B -O -m unittest -v test_terminal_labor_frontier.py
```

Both modes: 11/11 PASS. Controls cover disabled identity, seam-only activation, exact first-10 cost 143, continuation from prior daily hires, market-cap truncation, non-HIRE refusal, current-unit cash effects, no-job no-op, marginal count selection, surplus thresholding and incumbent-unfunded fail-closed behavior.
