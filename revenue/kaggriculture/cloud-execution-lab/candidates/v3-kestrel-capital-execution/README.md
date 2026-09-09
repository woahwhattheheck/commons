# KESTREL — rival-lockstep-safe early capital

This is an isolated Titan V3 candidate for the already-enabled `early_capital`
callsite. It is not a selector, canonical release, score claim, or upload gate.

## Why this successor exists

The official engine does more than execute one player's queue in isolation:

1. it truncates each queue to `maxMarketOrdersPerTurn`;
2. it resolves both players at each queue index;
3. same-index product units use one pre-commit market quote;
4. cash, shed capacity, hires, and public inventory change between indices; and
5. unit actions first atomically block every same-crop PLANT request when total
   demand exceeds the seed ledger.

The original KESTREL candidate correctly fixed active-prefix membership and
proved its proposal against exact own-side market primitives. Two gaps remained:
its standalone post-unit fallback replayed PLANT actions sequentially, and an
own-only market proof could not cover rival price movement.

The exact price counterexample is small. With own cash $900, one FERTILIZER,
FERTILIZER inventory 9870, WHEAT inventory 10000, and a rival buying two WHEAT
units at index zero, the predecessor accepts:

```text
BUY_PRODUCT WHEAT 1, BUY_LAND, SELL FERTILIZER 1
    -> SELL FERTILIZER 1, BUY_LAND, BUY_PRODUCT WHEAT 1
```

The original fills WHEAT and misses LAND. The proposal lands, leaves $26, then
misses WHEAT after the rival raises its quote to $27. That is an own execution
regression even though the isolated replay is green.

## Admission theorem

`kestrel_early_capital.py` remains the proposal and public-state own-replay gate.
`lockstep_early_capital.py` is the candidate runtime successor. A changed active
prefix is admitted only when all of the following are true:

- active-prefix membership and the inactive tail are unchanged;
- the queue contains exactly one `BUY_LAND` or `BUY_ANIMAL` order;
- every other effectful row is a `SELL` of a product rivals cannot buy;
- requested sale units for each product move no later at every prefix;
- the sole capital order is the last effectful candidate row; and
- the pinned public price curve is nonincreasing across the complete two-shed
  supply bound.

Counting sale rows is not enough: swapping a ten-unit sale with a one-unit sale
can move nine units later while preserving row counts. The successor checks
cumulative requested units per product.

For the admitted shape, each own sale unit sees no more preceding rival supply
than before. Rival actions cannot remove those products, and extra supply only
moves their checked price curves downward. Cash and freed shed capacity before
the single fixed-cost capital order therefore cannot be worse than the original
under the same hidden rival queue. No effectful own order follows capital, so an
extra capital execution cannot steal resources from work the original executed.

This proves **own-turn non-regression**, not universal capital gain. An exact
second witness freezes that boundary: three one-unit CARROT sales predict LAND
against the public market, but a rival's legal 100-CARROT sale can erase the
local gain. Both queues still miss LAND, and the earlier-sale candidate ends
with no less own cash. Paired official games remain the strength gate.

## Atomic post-unit binding

When FrozenSelected provides a captured completed post-unit pair, the candidate
uses it. Otherwise the wrapper:

- aggregates farmer and hand PLANT demand by crop;
- converts every over-demanded crop request to PASS; and
- only then applies the official extracted unit primitive in unit order.

One WHEAT seed plus two WHEAT requests consequently plants zero, matching the
official interpreter rather than the predecessor's sequential one-plant replay.

## Files

- `kestrel_early_capital.py` — unchanged predecessor proposal and own replay.
- `lockstep_early_capital.py` — atomic unit reconstruction and lockstep theorem.
- `candidate_runtime.py` — candidate-only Titan binding.
- `candidate_main.py` — source-tree game entrypoint.
- `test_kestrel_early_capital.py` — original adversarial contracts.
- `test_runtime_binding.py` — captured-snapshot and atomic-fallback binding.
- `test_kestrel_lockstep_repair.py` — pinned-engine rival witnesses, PLANT
  discriminator, sale-unit ordering guard, and positive single-capital case.
- `reproduce_predecessor.py` / `PREDECESSOR-RESULTS.json` — predecessor receipt.
- `PANEL-HANDOFF.md` — frozen gameplay instructions.

## Verification

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python -m unittest -v \
  candidates/v3-kestrel-capital-execution/test_kestrel_early_capital.py \
  candidates/v3-kestrel-capital-execution/test_runtime_binding.py \
  candidates/v3-kestrel-capital-execution/test_kestrel_lockstep_repair.py

python candidates/v3-kestrel-capital-execution/reproduce_predecessor.py \
  --check candidates/v3-kestrel-capital-execution/PREDECESSOR-RESULTS.json

python -m py_compile \
  candidates/v3-kestrel-capital-execution/*.py
```

Candidate entrypoint:

```text
candidates/v3-kestrel-capital-execution/candidate_main.py::agent
```

## Promotion boundary

Do not copy candidate bytes into canonical `early_capital.py` independently.
Canonical source, `exports/titan-current.tar.gz`, `CURRENT-SOURCE.json`, and
`CURRENT-ARCHIVE.json` are one build-coupled publication. Promotion requires a
fresh-main collision audit, exact tests, and a complete winning paired panel.

No Kaggle upload is authorized by this candidate.
