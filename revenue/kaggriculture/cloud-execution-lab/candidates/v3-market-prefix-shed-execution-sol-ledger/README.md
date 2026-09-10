# TITAN V3 market-prefix shed-execution custody

## Disposition

**Additive, default-off source and integration carrier.** This packet proves a
current-production scheduler defect and supplies a fail-closed repair contract.
It does not modify the canonical agent, package, archive, configuration,
provider state, Kaggle state, or submission state. It makes no playing-strength
claim. Promotion requires a current-control paired official-engine panel with
returned-action activation, positive own-cash evidence, nonnegative
opponent-by-seat strata, and zero new losses.

Operation: `TITAN-V3-MARKET-PREFIX-SHED-EXECUTION-20260910-01`

Slack claim: `#titan-kaggriculture`, timestamp `1789069002.983189`.

## Exact source

The work was authored against fresh reconciled `main` commit
`2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb`.

| Role | Repository path | Git blob |
|---|---|---|
| production scheduler | `revenue/kaggriculture/cloud-execution-lab/scheduler.py` | `a483b24dd72b580d7d8811636b54d2d44f391575` |
| active one-tree consumer | `revenue/kaggriculture/cloud-execution-lab/frozen_selected.py` | `fc7baf5c179818a55037f6a61d92984d81d1a21c` |
| pinned official engine | `revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py` | `3c202c7ee921da239356789e266b694635103fc4` |

The hosted verifier fails unless all three exact blobs are present. The branch was merged forward onto current main `21011846096daad1dd487df0efedf209303c1cb5`; these execution blobs remained byte-identical.

## Defect

The active one-tree path is `FrozenSelected.transform()`, which inherits
`SellScheduler.receipt_profile()` and then emits the selected queue through
`materialize_sales()`. The callback models each turn with one `before` shed total
and one `after` total. Between those checkpoints it adds every inherited
`BUY_PRODUCT`/`BUY_ANIMAL`, subtracts inherited non-target SELLs, and only then
subtracts the candidate target sale.

The engine does something materially different:

1. it truncates the **raw** market list to `q[:maxMarketOrdersPerTurn]`;
2. it processes literal market indices in order;
3. each purchase unit commits only while the shed has room; and
4. a later SELL cannot revive a purchase that already stopped at a full shed.

Therefore a candidate can pass the aggregate callback while silently changing
an inherited operating purchase. That invalidates the scheduler's stated
premise that operating-resource trades remain unchanged.

## Exact predecessor witness

Configuration: shed capacity 3, market limit 10. Initial shed:
`CARROT=1, EGG=1, MILK=1`.

Control market:

```json
[
  ["SELL", "CARROT", 1],
  ["BUY_PRODUCT", "WHEAT", 1],
  ["SELL", "EGG", 1],
  ["SELL", "MILK", 1]
]
```

Candidate market:

```json
[
  [],
  ["BUY_PRODUCT", "WHEAT", 1],
  ["SELL", "EGG", 1],
  ["SELL", "MILK", 1]
]
```

The production callback's whole-row shape reports the candidate feasible:
initial occupancy is 3, its aggregate inherited post-row occupancy is 2, and
zero candidate CARROT units are subtracted. The literal engine path differs:

| Arm | index 0 | index 1 | inherited WHEAT committed |
|---|---|---|---:|
| control | CARROT SELL opens one slot | purchase sees occupancy 2 | 1 |
| candidate | blank; shed remains full | purchase sees occupancy 3 | 0 |

The later EGG/MILK sales occur after index 1 and cannot rescue that failed
purchase. `WITNESS.json` is a deterministic machine-readable copy of the case.
The hosted tests execute the pinned production callback, the exact active
`FrozenSelected.materialize_sales()` consumer, and the pinned official engine,
rather than relying only on the local audit model. The active consumer produces
the witness queue exactly when `current={CARROT:0, EGG:1, MILK:1}`.

## Repair theorem

A scheduler candidate is admitted only when both conditions hold:

1. **SELL-only mutation boundary.** Every inherited non-SELL row remains at the
   same raw index and is value-identical. An inherited valid SELL may only be
   suppressed or retain its item with another positive quantity. New rows may
   only be appended valid SELLs.
2. **Inherited-purchase prefix custody.** Every raw row through the final valid
   inherited `BUY_PRODUCT` or `BUY_ANIMAL` inside the engine's executable prefix
   is value-identical to control.

Under equal pre-state, configuration, and rival action, condition 2 makes the
interpreter input identical through every inherited shed-occupying purchase.
Consequently each guarded purchase has the same quote path, affordability,
capacity admission, committed quantity, and side effects. Rows after the final
purchase remain available to SELL scheduling.

This is intentionally stronger than trying to predict occupancy alone. The
strong prefix theorem also closes paired-rival price effects, cash dependence,
partial multi-unit orders, malformed rows, and raw-prefix blank semantics.

## Files

- `market_prefix_guard.py`: total parser, capacity audit trace, SELL-only delta
  proof, inherited-purchase prefix proof, combined contract, and default-off
  atomic wrapper.
- `test_market_prefix_guard.py`: 24 local predecessor, totality, raw-cap,
  mutation-boundary, and fallback contracts.
- `test_pinned_predecessor.py`: three checkout-bound tests. They prove that the
  exact pinned `receipt_profile()` accepts the witness, the exact active
  `FrozenSelected.materialize_sales()` emits that queue, and the exact pinned
  engine changes the inherited WHEAT purchase from 1 → 0.
- `build_witness.py` / `WITNESS.json`: deterministic evidence builder and
  checked receipt.
- `SOURCE.json` / `RECEIPT.json`: immutable source and validation metadata.

## Integration contract

Do **not** merely call the wrapper after mutating `SellScheduler.planned`.
The scheduler is stateful. Integrators should use
`preserves_scheduler_contract(base_market, tentative_market, configuration)` as
a veto before committing future-plan state.

A safe current-tree integration sequence is:

```python
planned_before = copy.deepcopy(self.planned)
pending_before = copy.deepcopy(self.pending)

# Render a tentative action without committing chosen-plan state.
tentative = render_candidate(...)
safe, custody = preserves_scheduler_contract(
    base["market"], tentative["market"], config
)
if not safe:
    self.planned = planned_before
    self.pending = pending_before
    self.diagnostics["purchase_prefix_veto"] = custody
    out = copy.deepcopy(base)
else:
    commit_chosen_plan_state(...)
    out = tentative
```

An even narrower implementation can lock every inherited raw row through the
last executable shed purchase and constrain each optimizer's current-turn
minimum to the actual locked prefix sales. Either implementation must add an
end-to-end returned-action contract; planner-level feasibility alone is not
sufficient.

## Validation

Local publication check:

```text
python -m py_compile *.py
python build_witness.py --check
python -m unittest discover -s . -p 'test_*.py' -v

Outside the repository, unittest reports 26 methods: 24 portable PASS and two
checkout-bound methods skipped; the official-engine class skips before its one
method is counted. Hosted CI requires all 27 methods to execute with zero skips.
```

The hosted workflow requires those checkout-bound tests to execute and also
runs `build_integrated.py --check` to prove this additive packet leaves the
canonical package clean.
