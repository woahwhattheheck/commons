# Titan V2 SELL target-domain product attribution

Operation: `titan-v2-target-product-attribution-20260909-sol-archimedes-01`

## Why this exists

Frozen V2 widened its SELL scheduler from inherited/pending intent to **every
positive product in the shed**. The exact all-shed→V1-core ablation established
that the policy expansion changes behavior and can move own cash, but the binary
screen cannot say which product is useful or harmful. Choosing either whole
policy is too blunt for Titan V3.

This lane decomposes the expansion into seven product marginals:

`CARROT`, `TOMATO`, `STRAWBERRY`, `MELON`, `EGG`, `MILK`, and `WOOL`.

`WHEAT` and `FERTILIZER` remain in the inherited core because the scheduler
explicitly treats them as operating stock and the baseline controller already
owns their SELL intent.

## Exact arms

- `CONTROL`: frozen V2, all positive shed products.
- `CORE`: frozen V2 with only inherited baseline SELL plus pending scheduler
  intent, matching the prior V1-domain arm.
- One arm per product: `CORE` plus that product widened to all positive shed
  stock.

`materialize.py` fails closed unless the source scheduler blob is exactly
`7c068b7078c3d7c09bb3836590ad42b0af934cdf`. Every candidate is a byte-for-byte
copy of frozen V2 except `scheduler.py`; source and candidate closure hashes and
unified diffs are retained independently for every arm.

## Panel and interpretation

Every arm receives the same official interpreter, evaluator, loader, eight
seeds, two seats, frozen V1 opponent, public Arlene opponent, timeout limits,
and agent RNG seed. The comparator rejects partial cells, failures, duplicate
keys, provenance drift, closure reuse, and equal CONTROL/CORE traces.

Each product is classified relative to `CORE`:

- `MARGINAL_UPSIDE`: changed trace, positive mean own cash, nonnegative median,
  positives at least negatives, and nonnegative own-cash mean in both opponent
  strata.
- `MARGINAL_DOWNSIDE`: the sign-reversed conservative screen.
- `MIXED`: changed behavior without a broad directional result.
- `NO_EFFECT`: no action-trace change on the panel.

The report ranks all products, retains changed-cell evidence, and reports the
non-additivity residual between the complete all-shed policy and the sum of
one-product marginals. It does **not** assume independent effects.

This is causal attribution only. It cannot mutate canonical/runtime/config
bytes, promote a candidate, authorize spend, or authorize a leaderboard
submission.
