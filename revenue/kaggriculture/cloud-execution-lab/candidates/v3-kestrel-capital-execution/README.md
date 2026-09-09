# KESTREL — execution-preserving early capital

This is an isolated Titan V3 gameplay candidate for the already-enabled
`early_capital` callsite. It is not a new evaluator, selector, or release gate.

## Why this lane exists

The canonical `v2-order-only` transform ranks every market row and sorts the
entire list. The official engine does something materially different:

1. it truncates each queue to `maxMarketOrdersPerTurn`;
2. it executes rows by index;
3. cash, shed capacity, daily hire cost, and public product inventory change
   between indices; and
4. both players receive same-precommit quotes and commit in per-unit lockstep.

Therefore preserving only the queue's multiset does not preserve behavior. The
exact predecessor can:

- pull an inactive row beyond index 9 into the live ten-row prefix;
- move `SELL` ahead of the `BUY_PRODUCT` that supplied its stock;
- make a previously executable product purchase fail so that land can execute;
- perturb same-item quotes even when both quantities still execute; and
- reconstruct PLANT actions sequentially even though the official interpreter
  atomically blocks every same-crop request when aggregate demand exceeds seed
  stock.

This matters at the final canonical callsite because FrozenSelected already has
a conservative `fund_same_turn_acquisition` mechanism. A later unconditional
rank sort can undo that producer-owned safety.

## Candidate contract

`kestrel_early_capital.py` remains the original active-prefix proposal and
own-state execution certificate. `lockstep_early_capital.py` is the runtime
successor and admits a changed queue only after a second, rival-independent
certificate.

The predecessor proposal still requires:

- active-prefix membership is byte-for-byte invariant;
- every originally executed non-capital row executes the same quantity;
- no preserved sale earns less;
- no preserved purchase costs more;
- no already-successful admitted capital row regresses; and
- at least one admitted `BUY_LAND` or `BUY_ANIMAL` unit newly executes.

The lockstep successor then requires:

- no active-prefix `BUY_PRODUCT`, whose quote may change after rival units;
- no WHEAT or FERTILIZER sale, because those are the two products a rival may
  buy from the market;
- every sale-only product order is moved no later than before;
- the complete active order multiset and inactive tail are unchanged; and
- the pinned public price curve is nonincreasing across the complete two-shed
  supply bound.

For those products a rival can only add supply. Moving an own sale earlier thus
cannot reduce its receipt, while all remaining own costs are fixed. This keeps
the useful CARROT/TOMATO/STRAWBERRY/MELON/EGG/MILK/WOOL-funded capital cases
without pretending an own-only simulator proves arbitrary rival interaction.
Anything outside that theorem returns the original action unchanged.

When no captured FrozenSelected post-unit pair exists, the wrapper reconstructs
the unit stage with the official aggregate PLANT-demand prepass before applying
farmer and hand actions. The prior sequential fallback is never used by the
candidate runtime.

This is still a semantic candidate, not a score claim. Paired official games
remain mandatory before promotion.

## Files

- `kestrel_early_capital.py` — original active-prefix proposal and own-state
  execution certificate.
- `lockstep_early_capital.py` — atomic unit replay plus rival-lockstep admission
  certificate used by the candidate runtime.
- `candidate_runtime.py` — one-method subclass of canonical `TitanAgent`.
- `candidate_main.py` — source-tree entrypoint for official games.
- `test_kestrel_early_capital.py` — original adversarial semantic contracts.
- `test_runtime_binding.py` — exact selected-snapshot/fallback binding contracts.
- `test_kestrel_lockstep_repair.py` — exact official rival-price witness,
  atomic-PLANT predecessor discriminator, and positive sale-only case.
- `reproduce_predecessor.py` — replay against the pinned canonical predecessor.
- `PREDECESSOR-RESULTS.json` — checked four-case receipt.
- `PANEL-HANDOFF.md` — frozen gameplay evaluation instructions.
- `PROVENANCE.json` and `TEST-RESULTS.json` — original source/test evidence.

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

The candidate game entrypoint is:

```text
candidates/v3-kestrel-capital-execution/candidate_main.py::agent
```

## Promotion boundary

Do not copy these bytes into canonical `early_capital.py` by themselves.
Canonical source, `exports/titan-current.tar.gz`, `CURRENT-SOURCE.json`, and
`CURRENT-ARCHIVE.json` are one build-coupled publication. First run the frozen
current-vs-candidate panel in `PANEL-HANDOFF.md`; only a complete winning result
may enter a fresh-main release build.

No Kaggle upload is authorized by this candidate.
