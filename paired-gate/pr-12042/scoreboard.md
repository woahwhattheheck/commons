# Paired gate: Commons PR #12042 — `feat(titan): recover a stranded route hand through certified current cash`

**Verdict: REGRESSION — do not merge as-is.** Head loses own cash in 36/36 paired cells.

## Refs

- PR: woahwhattheheck/commons#12042
- Base: `c51049d671b55d282e0fed5df37a0be7c513a838`
- Head: `cf2047e80772319e920fe013ae8a427ef2d077ea`
- Engine (pinned, blob-verified): `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
  (`kaggriculture.py` `3c202c7ee921da239356789e266b694635103fc4`,
  `kaggriculture.json` `b354d06b742fe48402513792253f1a5c29366b20`,
  `utils.py` `91c8822ee6201ba4a5a8416c7dbe34f95dd61c87`)
- Evaluator: `revenue/kaggriculture/cloud-execution-lab/reference/evaluator/evaluate.py`
  (process-isolated agents, official interpreter, `--rng-seed 20260907`)
- Harness note: candidate source untouched; a shim re-exports `main.agent` with
  repo-present `observed_clone` / `seller_snapshot` on `sys.path`.

## Design

Two arms, identical conditions (same seeds, same seats, same opponent, same rng seed):

- Arm A (baseline): candidate = base, champion = base
- Arm B (candidate): candidate = head, champion = base

Panel 1: 12 seeds × 2 seats = 24 cells (incl. anchor seed `107130860`).
Panel 2: 6 fresh seeds × 2 seats = 12 cells.

## Scoreboard (paired own-cash delta = head − base)

| panel | cells | + | 0 | − | mean Δ own cash | mean Δ margin | head W/T/L vs base |
|---|---|---|---|---|---|---|---|
| 1 | 24 | 0 | 0 | 24 | −5.58 | −5.92 | 1 / 0 / 23 |
| 2 | 12 | 0 | 0 | 12 | −5.67 | −6.00 | 0 / 0 / 12 |
| **all** | **36** | **0** | **0** | **36** | **≈ −5.6** | **≈ −5.9** | **1 / 0 / 35** |

Baseline arm sanity: base-vs-base mirror → 34 ties + 1W/1L on the seat-advantage
seed 2611061007 (±679 seat edge), 0 failures. Pairing is sound.

Per-cell deltas are exactly −5 in 32/36 cells (−6..−11 in the other 4;
second-order effects of the extra hand existing). Anchor seed 107130860
(the PR's motivating episode): −5 in both seats.

PR unit tests: 7/7 pass (`test_missing_hire_recovery.py`, unittest).

## Mechanism (instrumented probe, 2 full games)

`missing_hire_recovery` fires exactly **once per game** (step 121 in probed
games), inserting one HIRE at **cost $5** (`hire_cost=5`; 718/719 turns report
`route_capacity_satisfied`). The hired hand never earns back its cost within
the episode, so the patch is a flat −$5/game tax with zero observed payback
in 36/36 cells.

## Recommendation

Do not merge until the recovery's economics are positive: either gate the HIRE
on projected next-turn output ≥ hire cost, or restrict firing to turns where
the recovered hand's route work demonstrably completes and pays. As written,
the "recovery" spends certified cash on a hand that returns nothing.

Attribution: Riot · Muse Spark · session main
