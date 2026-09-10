# E13 future-sale solvency closure

Operation: `TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CLOSURE-20260910-01`

Disposition: **`SOURCE_REAL_ACTION_UNMEASURED`**

Slack claim: `#titan-kaggriculture` TS `1789069704.186569`.

## Why this exists

Merged E13 (`#11117`) replaced the old all-or-nothing SELL funding floor with
`funded_minimum_now()`. That was directionally valuable: it searches for the
smallest current sale that preserves inherited fixed acquisitions. Its future
funding boundary is nevertheless binary:

```python
for t, _item, _units, cash in trace.get('executed_sales', ()):
    if t > now and cash > 0:
        return t - 1, t
```

The first future sale that earns even one dollar ends the acquisition
comparison. Fixed acquisitions on later turns are no longer protected, even
when that future receipt is far smaller than their cost.

This packet closes only that residual later-turn solvency hole. It does not
change the separately claimed SOL-ESCROW same-turn/order-index boundary.

## Exact predecessor killer

The source-bound witness is deliberately small:

| Stage | Market request | Exact economic effect |
|---|---|---|
| current | reduce an inherited `SELL MILK 10` | E13 predecessor permits `0` |
| next turn | `SELL WOOL 1` with WOOL already at its price floor | receipt is `$1` |
| following turn | `BUY_ANIMAL COW 1` | fixed cost is `$400` |

With no current MILK sale, the COW does not execute. Two current MILK units
produce `$318`; even with the `$1` future sale, the COW still does not execute.
Three current MILK units produce `$474`; with the future dollar, the COW
executes. The correct minimum is therefore `3`, not `0`.

A control proves the repair is not conservative liquidation: two future WOOL
units at the base inventory produce `$400`, so the correct current minimum
remains `0`.

The test suite runs those sequences through the repository's exact pinned
`reference/engine/kaggriculture.py::_process_market`, not only through the
projection helper.

## Repair boundary

`materialize.py` authenticates:

- active `frozen_selected.py` Git blob
  `fc7baf5c179818a55037f6a61d92984d81d1a21c`;
- pinned interpreter Git blob
  `3c202c7ee921da239356789e266b694635103fc4`.

It then replaces exactly one top-level function, `funded_minimum_now()`, in a
disconnected output under caller control. Canonical source, runtime, archive,
configuration, and release pointers are never written.

The candidate keeps E13's legacy obligations through the turn before the first
future positive-cash sale. It additionally protects only baseline-completed
fixed acquisitions whose turn is **strictly greater than** that sale's turn.
Candidate traces then run through the already bounded horizon, so the actual
future receipt amounts—not mere positivity—determine how much current working
capital can be released.

Acquisitions on the funding sale's own turn remain excluded. That is
intentional deconfliction with SOL-ESCROW TS `1788989953.650839`, whose earlier
claim owns exact same-turn market-order custody.

## Contracts

`test_future_sale_solvency.py` contains 16 focused contracts:

- predecessor `0` versus candidate `3` on the `$1 -> $400` killer;
- exact pinned-interpreter confirmation that `0` and `2` MILK units fail while
  `3` succeeds;
- sufficient future receipt preserving a zero minimum;
- multi-unit acquisition-fill preservation;
- zero-fill future SELL behavior;
- no-later-acquisition legacy parity;
- both same-turn SELL/acquisition orderings left unchanged for SOL-ESCROW;
- deterministic one-function materialization;
- source and interpreter drift rejection before any candidate write;
- canonical-path overwrite refusal;
- active-prefix, same-turn exclusion, and alias-safe route-census contracts.

The workflow also reruns the eight landed E13 regressions in
`test_funded_prefix.py`.

## Route exposure census

`scan_routes.py` authenticates the frozen Arlene Git blob
`bdb9cf58148a3c7961c085f4902759537decabf6`, decodes the exact retained route
bank, and counts only this structural sequence inside E13's eight-turn horizon:

1. a current non-operating product SELL;
2. the first later requested positive-quantity SELL;
3. a fixed HIRE, LAND, SEED, or ANIMAL acquisition on a strictly later turn.

It applies official `max(1, maxMarketOrdersPerTurn)` prefix custody and reports
named-route and route-body-deduplicated counts separately. This is a structural
source census only. It does not claim the future sale fills, the candidate
changes a returned action, or any score effect.

## Hosted execution

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python analysis/v3-e13-future-sale-solvency/test_future_sale_solvency.py

python analysis/v3-e13-future-sale-solvency/materialize.py \
  --output /tmp/titan-e13-solvency/frozen_selected.py \
  --receipt /tmp/titan-e13-solvency/RECEIPT.json

python analysis/v3-e13-future-sale-solvency/scan_routes.py \
  --output /tmp/titan-e13-solvency/ROUTE-CENSUS.json
```

The path-scoped GitHub workflow retains the candidate, receipt, frozen-route
census, exact checked-out provenance, logs, and SHA-256 manifest. It also proves
the canonical source set remains clean.

## Promotion boundary

This carrier is not a gameplay or release promotion. Integration first needs a
fresh-main one-tree composition that proves the generated function reaches a
returned action. Only then is a matched common-seed, both-seat current-control
panel informative. The minimum gameplay gate is positive mean own-cash delta,
nonnegative median, zero new losses, and no negative opponent-by-seat stratum.
No provider or Kaggle mutation is authorized here.

V1/V2 score comparisons remain outside this packet unless exact agent source,
engine identity, seat, and matched cells are bound. Filename prefixes and
unmatched public episodes are not attribution.
