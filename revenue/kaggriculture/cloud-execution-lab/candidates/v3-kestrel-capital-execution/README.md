# KESTREL — execution-preserving early capital

This is an isolated Titan V3 gameplay candidate for the already-enabled
`early_capital` callsite. It is not a new evaluator, selector, or release gate.

## Why this lane exists

The canonical `v2-order-only` transform ranks every market row and sorts the
entire list. The official engine does something materially different:

1. it truncates each queue to `maxMarketOrdersPerTurn`;
2. it executes rows by index;
3. cash, shed capacity, daily hire cost, and public product inventory change
   between indices.

Therefore preserving only the queue's multiset does not preserve behavior. The
exact predecessor can:

- pull an inactive row beyond index 9 into the live ten-row prefix;
- move `SELL` ahead of the `BUY_PRODUCT` that supplied its stock;
- make a previously executable product purchase fail so that land can execute;
- perturb same-item quotes even when both quantities still execute.

This matters at the final canonical callsite because FrozenSelected already has
a conservative `fund_same_turn_acquisition` mechanism. A later unconditional
rank sort can undo that producer-owned safety.

## Candidate contract

`kestrel_early_capital.py` still proposes the same stable priority order, but it
limits the proposal to the original active prefix and replays the official
own-side deterministic market semantics from the completed post-unit state.

A proposal is applied only when all of the following are true:

- active-prefix membership is byte-for-byte invariant;
- every originally executed non-capital row executes the same quantity;
- no preserved sale earns less;
- no preserved purchase costs more;
- no already-successful admitted capital row regresses; and
- at least one admitted `BUY_LAND` or `BUY_ANIMAL` unit newly executes.

Anything malformed or unavailable returns the original action unchanged. The
candidate never adds, drops, substitutes, or resizes an order and never inspects
or predicts a rival's hidden queue.

The replay is a **self-dependency proof**, not a score claim. Rival lockstep
interaction and future opportunity cost still require paired official games.

## Files

- `kestrel_early_capital.py` — active-prefix proposal and execution certificate.
- `candidate_runtime.py` — one-method subclass of canonical `TitanAgent`.
- `candidate_main.py` — source-tree entrypoint for official games.
- `test_kestrel_early_capital.py` — adversarial semantic contracts.
- `test_runtime_binding.py` — exact selected-snapshot/fallback binding contracts.
- `reproduce_predecessor.py` — replay against the pinned canonical predecessor.
- `PREDECESSOR-RESULTS.json` — checked four-case receipt.
- `PANEL-HANDOFF.md` — frozen gameplay evaluation instructions.
- `PROVENANCE.json` and `TEST-RESULTS.json` — source/test evidence.

## Verification

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python -m unittest -v \
  candidates/v3-kestrel-capital-execution/test_kestrel_early_capital.py \
  candidates/v3-kestrel-capital-execution/test_runtime_binding.py

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
