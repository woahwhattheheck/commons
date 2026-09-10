# TITAN V3 all-shed priority — current canonical port

This lane tests one already-admitted frozen-V2 scheduler mechanism against the
**exact current canonical TITAN archive** rather than assuming that the old
result survives current composition.

## Factor

The target domain and target quantities are unchanged:

- every positive non-operating `PRODUCTS` item in the post-unit shed;
- the full post-unit shed quantity for each item.

Only the first-wins traversal order changes from canonical `PRODUCTS` order to:

1. existing pending scheduler intent;
2. inherited baseline `SELL` first-seen order;
3. remaining canonical `PRODUCTS` order.

The patch is one replacement in `scheduler.py`. `main.py`, `TITAN-CONFIG.json`,
all runtime helpers, and all opponent/evaluator sources remain byte-identical.

## Source and execution custody

`materialize.py` verifies and safely expands the exact
`exports/titan-current.tar.gz` archive, including its Git blob, SHA-256, byte
count, `SOURCE.json`, every declared member digest, canonical `main.py`, and the
current scheduler blob. It emits distinct control/candidate closure receipts.

`bind_execution.py` generates two different closure-checking wrappers around
the canonical `main.py::agent` entrypoint. Every worker recomputes its complete
closure before import and rejects ambient runtime-module collisions or module
origins outside its materialized root.

`materialize_evaluator.py` makes the previously reviewed three-site evaluator
patch that records the candidate's returned action after both agents return and
before the interpreter mutates state.

`screen.py` independently recomputes every on-disk identity and every paired
score delta. The panel is the exact 8-seed × 2-opponent × 2-seat grid for both
arms (64 complete games total) against Arlene and frozen V1.

## Admission

A result is admitted only when all of these hold:

- at least one pre-interpreter candidate action changes;
- mean own cash is positive and median own cash is nonnegative;
- positive own-cash cells are not outnumbered by negative cells;
- mean margin is positive;
- no new loss is introduced;
- every opponent × seat stratum has nonnegative mean and median own cash,
  nonnegative cell balance, nonnegative mean margin, and zero new losses.

This is an offline causal screen only. It does not authorize a hosted Kaggle
submission, canonical archive mutation, merge, or promotion.
