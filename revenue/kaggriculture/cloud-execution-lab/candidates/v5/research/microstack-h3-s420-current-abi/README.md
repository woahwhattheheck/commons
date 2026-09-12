# TITAN V5 — current-ABI MICROSTACK H3/S420 re-gate

This directory revives one explicitly unfinished successor from the recovered
MOSAIC sale-timing work: re-test the historical H3/S420 hypothesis on the
**current** TITAN seller without resurrecting legacy R04 feature keys or a
second policy tree.

## Historical motivation, not promotion evidence

The recovered V3.1-era stack `{sale_horizon=3,
no_late_sale_advance_step=420}` had a historical controlled receipt of roughly
`+$441` mean margin (`SE $25`, `16/16` positive). PR #12835 preserved the
source packet and explicitly required a fresh current-ABI re-gate rather than
adding `r04_sale_horizon` or `r04_no_late_sale_advance_step` to production.

## Current-ABI interpretation

`current_sale_timing.py` patches only an **isolated experiment process** using
the current `frozen_selected` module:

* **control** — current seller unchanged;
* **H3** — the inherited scheduler baseline `HORIZON` is narrowed from `8` to
  `3`; current public service/unit event extensions, production route,
  feasibility, funding and materialization remain unchanged;
* **H3+S420** — H3 plus a step `>=420` veto only when the current optimizer
  proposes an equal-total temporal advance relative to its own reference
  schedule. Forced-feasibility bypasses the veto. Malformed/non-comparable
  plans fail open to the current seller.

A blocked optional advance returns the exact reference schedule and sets
`accepted=False`, so the existing `seller_choice_rank` path cannot select a
no-op as a winning alternative.

This is deliberately **not** equivalent to EXEC-PACE: EXEC-PACE requires a
25-observation rising-price signal. It is also not the close-game ranker,
which only reorders already-issued same-turn SELL rows.

## Source custody

`SOURCE-PINS.json` binds the exact current `frozen_selected.py`,
`selected_sell_core.py`, and `scheduler.py` blobs used to define this re-gate.
`test_source_pins.py` fails closed if those source authorities move. Rebase and
review semantics; do not silently update pins.

## Focused checks

From this directory:

```bash
python -B -m unittest -v test_current_sale_timing.py test_source_pins.py
python -O -B -m unittest -v test_current_sale_timing.py test_source_pins.py
python -m py_compile current_sale_timing.py test_current_sale_timing.py test_source_pins.py
```

The initial pure adapter suite was also exercised before publication in normal
and `-O` mode: 8/8 tests passed in each mode.

## Evaluation contract

The next gate is matched current-V5 official-engine evidence using the same
source/package identity for all arms. Run control vs H3 vs H3+S420 on both
seats against the strongest available adaptive opponents, recording per-cell
own/rival/margin, first changed returned-action step, seller diagnostics,
engagement counts, failures and timing. Historical `+$441` is motivation only;
it cannot authorize a production/default change.

## Hard boundaries

No production `Features` key, `TITAN-CONFIG.json` edit, release archive/pointer
mutation, legacy R04 router/materializer, second seller/controller, or Kaggle
submission belongs in this directory. Any promotion must converge through the
single current V5 runtime after fresh economics and moving-main review.
