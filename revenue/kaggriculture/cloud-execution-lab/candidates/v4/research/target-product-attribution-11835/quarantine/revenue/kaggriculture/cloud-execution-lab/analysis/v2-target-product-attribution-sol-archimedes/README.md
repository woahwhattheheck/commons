# Titan V2 SELL target-domain product attribution

Operation: `titan-v2-target-product-attribution-20260909-sol-archimedes-01`

## Why this exists

Frozen V2 widened its SELL scheduler from inherited/pending intent to **every
positive product in the shed**. The exact all-shed→V1-core ablation completed
32/32 paired cells and measured `+144` total / `+4.5` mean Titan own-score
recovery from restoring the core domain. The binary result is real, but it
cannot identify which product is useful or harmful. Choosing either whole
policy is too blunt for Titan V3.

This lane decomposes the expansion into seven product marginals:

`CARROT`, `TOMATO`, `STRAWBERRY`, `MELON`, `EGG`, `MILK`, and `WOOL`.

`WHEAT` and `FERTILIZER` remain in the inherited core because the scheduler
explicitly treats them as operating stock and the baseline controller already
owns their SELL intent.

## Exact arms

- `CONTROL`: byte-exact frozen V2, retaining all-positive-shed SELL targets.
- `CORE`: frozen V2 with only inherited baseline SELL plus pending scheduler
  intent, matching the prior V1-domain arm.
- One arm per product: `CORE` plus that product widened to all positive shed
  stock.

`materialize.py` fails closed unless the source scheduler blob is exactly
`7c068b7078c3d7c09bb3836590ad42b0af934cdf`. Every arm is copied from the same
frozen V2 closure. `CONTROL` must have zero changed files and the source closure;
every other arm must change only `scheduler.py`. Source/candidate closure hashes,
scheduler blob hashes, expression cardinalities, and unified diffs are retained.

## Panel and interpretation

Each arm runs as an independent 32-cell official-interpreter job over the same
eight seeds, both seats, frozen V1 opponent, and public Arlene opponent. The
workflow permits at most four simultaneous arms, then aggregates only after all
nine exact-head artifacts exist. This keeps the 288-game screen inside bounded
per-job runtime instead of serializing all games under one timeout.

The comparator rejects duplicate/noncanonical JSON, non-finite values, partial
or failed cells, bad step coverage, missing terminal bank checkpoints, score
changes without trace/bank changes, evaluator or candidate-entry drift,
duplicate cells, head drift, closure reuse, and equal CONTROL/CORE traces.

Each product is classified relative to `CORE`:

- `MARGINAL_UPSIDE`: changed trace, positive mean own score, nonnegative median,
  positives at least negatives, and nonnegative own-score mean in both opponent
  and both seat strata.
- `MARGINAL_DOWNSIDE`: the sign-reversed conservative screen.
- `MIXED`: changed behavior without a broad directional result.
- `NO_EFFECT`: no action-trace change on the panel.

The report ranks all products, retains changed-cell and first-bank-divergence
evidence, and reports the non-additivity residual between the complete all-shed
policy and the sum of one-product marginals. It does **not** assume independent
effects.

This is causal attribution only. It cannot mutate canonical/runtime/config
bytes, promote a candidate, authorize spend, or authorize a leaderboard
submission.
