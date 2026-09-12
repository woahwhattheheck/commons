# TITAN V5 animal cadence candidate

Status: **default OFF / evaluation only**. This package is additive to canonical V5 and does not change `main.py`, `titan_runtime.py`, `TITAN-CONFIG.json`, the release archive, or Kaggle submission bytes.

## Pinned engine theorem

The preserved engine is `reference/engine/kaggriculture.py` at source blob `3c202c7ee921da239356789e266b694635103fc4`.

The source-real behavior is:

- an animal survives one unfed end-of-day and escapes only when `consecutive_unfed >= 2`;
- scheduled base animal production is awarded even on that first unfed day;
- feeding gates consumption of a pending CARE bonus, so CARE value must not be discarded;
- every surviving animal sets `fertilizer_available = True` at every end-of-day, not every third day;
- `FERTILIZE` consumes one fertilizer and extends `fertilized_until_day`; it does **not** directly increment `yield_units`.

The last point is an explicit negative predecessor for the rejected “infinite fertilizer yield” hypothesis.

## Candidate

`alternate_feed.py::apply_alternate_feed(observation, selected)` is a pure selected-action transform. It replaces a selected `FEED` with `PASS` only when the actor actually carries WHEAT, the animal is on the exact zero-strike leg (`consecutive_unfed == 0`), no current or pending CARE value can be lost, and no same-tile selected CARE exists. Once the public state reports one unfed day, the next FEED is retained.

The transform preserves market rows, other unit actions, action-slot topology, and both inputs. It emits a deterministic report including exact edited actors and the number of WHEAT units avoided.

## Focused checks

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python -B candidates/v5/animal-cadence/test_alternate_feed.py
python -O -B candidates/v5/animal-cadence/test_alternate_feed.py
```

The test module calls the preserved evaluator/engine for the survival, production, fertilizer-refresh, and FERTILIZE-negative predecessors; candidate tests are separate and do not substitute an engine implementation.

## Evaluation handoff

For matched simulation, wrap the unchanged current-V5 selected action with `apply_alternate_feed` and compare against the same current-V5 baseline on identical opponent/seed/seat cells. Record candidate identity, engagement count (`report.changed`), WHEAT saved, paired own-score and margin deltas, loss flips/new losses, and any CARE-bonus divergence. Promotion requires matched current-line evidence; this package itself makes no activation claim.
