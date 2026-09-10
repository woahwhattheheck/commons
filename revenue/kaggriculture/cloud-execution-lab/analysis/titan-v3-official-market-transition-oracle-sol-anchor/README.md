# TITAN V3 official market-transition oracle

Operation: `TITAN-V3-OFFICIAL-MARKET-TRANSITION-ORACLE-20260910-01`

This is an evidence-only differential oracle for one exact Kaggriculture
`_process_market()` → `_town_consume()` transition. It exists because the active
SELL, funding, executable-prefix, pressure, HIRE, and acquisition repairs each
model a different slice of the same official transition. A collection of local
predicates can look individually correct and still compose into a false theorem.
This carrier gives those lanes one common executable truth boundary before T08
consumes their conjunction.

It changes no TITAN policy, feature flag, route, scheduler, canonical runtime,
archive, package pointer, seed bank, game result, provider state, Kaggle state,
or promotion state.

## Exact source boundary

Every command fails closed unless these three preserved engine members are
regular, non-symlink files with the exact Git blob identities below:

| Member | Required Git blob |
|---|---|
| `kaggriculture.py` | `3c202c7ee921da239356789e266b694635103fc4` |
| `kaggriculture.json` | `b354d06b742fe48402513792253f1a5c29366b20` |
| `utils.py` | `91c8822ee6201ba4a5a8416c7dbe34f95dd61c87` |

The implementation then runs two paths from the same deep-copied scenario:

1. the pinned official `_process_market()` followed by official
   `_town_consume()`; and
2. an independent source-derived transition with a per-row, per-quote,
   per-unit, atomic-order, shop, and town-center ledger.

No comparison result is exposed unless the complete official and reference
poststates are identical.

## Semantics covered

The reference path mirrors the exact raw prefix
`q[:max(1, maxMarketOrdersPerTurn)]`, market-row alignment, atomic `HIRE` and
`BUY_LAND` handling, simultaneous pre-commit quotes, player-order unit commits,
partial fill/failure stopping, dynamic prices, the `$1` SELL supply exception,
seed/product/animal purchases, shed capacity, land unlocks, hand spawning,
duplicate shop instances, shop-before-center chronology, and final price
refresh.

The retained self-check spans **2,160 differential cells**:

- all nine products;
- five inventory offsets around the product equilibrium;
- four quantity pairs;
- three cash pairs; and
- four two-player SELL/BUY_PRODUCT operation patterns.

The fixed compact row receipt is
`ca8975a96e144a29555c19d7b32d85575ce6b5d6ad440e25c3b771c9e138d3d4`.
Eighteen adversarial contracts separately cover source mutation, executable
suffixes, atomic HIRE/LAND, partial fills, simultaneous quotes, floor-price
sales, custom price curves, malformed queues, duplicate shops, deterministic
receipts, nonmutation, rival-action custody, and amount coercion.

## Predecessor killed

The source-bound same-product prefix fixture starts WHEAT inventory at `10066`
and uses this common rival queue:

```text
row 0: PASS
row 1: SELL WHEAT 100
row 2: PASS
```

The tested player changes only:

```text
baseline:  SELL WHEAT 78 ; SELL WHEAT 1 ; SELL MILK 1
candidate: SELL WHEAT 78 ; SELL MILK 1  ; SELL WHEAT 1
```

The official result is:

| Arm | tested money | rival money |
|---|---:|---:|
| baseline | 1828 | 2075 |
| candidate | 1827 | 2076 |

So the apparently harmless reordering loses tested cash `1`, gives the rival
`1`, and loses margin `2`. The first realized poststate divergence is after
market row 1. This is exactly the kind of own-prefix/rival-pressure interaction
that a raw inventory-only certificate misses.

## Python API

```python
from pathlib import Path
from official_market_transition_oracle import (
    compare_variants,
    load_official_engine,
)

engine, manifest = load_official_engine(
    Path("revenue/kaggriculture/cloud-execution-lab/reference/engine")
)

receipt = compare_variants(
    engine,
    manifest,
    scenario,                 # common farms/privates/market/town/config/step
    baseline_actions,         # exactly two literal player actions
    candidate_actions,        # same rival action as baseline
    tested_player=0,
    protected_paths=(
        "/farms/0/money",
        "/farms/1/money",
        "/privates/0/seeds",
        "/market/inventory",
    ),
)
```

`compare_variants()` emits:

- exact common-prestate and common-rival-action digests;
- complete source-bound parity receipts for both arms;
- active queues after the literal engine cap;
- first tested-action and first cumulative-poststate divergence;
- full changed JSON-pointer paths;
- tested, rival, and margin deltas;
- per-literal-order committed quantity, unit prices, failure state, and total;
- semantic changes to every unchanged literal active order; and
- complete baseline/candidate event and checkpoint ledgers.

The comparison verdict is `PRESERVES_DECLARED_STATE` only when all declared
JSON pointers and all unchanged literal active-order outcomes are preserved.
Otherwise it is `DIFFERENT_PROTECTED_STATE`. That verdict is a transition fact,
not a strength or promotion decision.

## Command line

```bash
CASE=revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-official-market-transition-oracle-sol-anchor
ENGINE=revenue/kaggriculture/cloud-execution-lab/reference/engine

python -B "$CASE/official_market_transition_oracle.py" \
  verify-engine --engine-dir "$ENGINE" --output /tmp/engine.json

python -B "$CASE/official_market_transition_oracle.py" \
  self-check --engine-dir "$ENGINE" --output /tmp/self-check.json

python -B "$CASE/official_market_transition_oracle.py" \
  run --engine-dir "$ENGINE" --scenario scenario.json --output /tmp/run.json

python -B "$CASE/official_market_transition_oracle.py" \
  compare --engine-dir "$ENGINE" \
  --scenario scenario.json \
  --baseline-actions baseline-actions.json \
  --candidate-actions candidate-actions.json \
  --tested-player 0 \
  --protect /farms/0/money \
  --protect /farms/1/money \
  --output /tmp/comparison.json
```

Inputs use strict JSON: duplicate keys and non-finite numbers are rejected.
Outputs are sorted deterministic JSON written atomically.

## One-tree consumption contract

A repair lane should submit one common source-bound prestate plus literal
baseline/candidate actions. Before treating a local certificate as composable,
it must establish all of the following:

1. both arms pass official/reference poststate parity;
2. the rival action is exactly identical;
3. the candidate's intended tested action actually differs inside the active
   raw prefix;
4. every claimed protected fill, receipt, acquisition, private balance, and
   public market field is preserved through town consumption; and
5. any claimed economic change is tied to the first realized checkpoint
   divergence rather than a detached proxy score.

Identical active prefixes with arbitrary authored suffixes must produce the same
poststate. A protected unchanged literal order that moves rows must preserve its
committed quantity, unit prices, failure status, and total receipt/cost—not just
the terminal aggregate.

## Explicit limits

This boundary does not model farmer/hand tile actions, plant decay, end-of-day
production, controller state, schedule checkpoint state, or a full episode. It
cannot establish that a tactic improves TITAN, that a local panel predicts the
hosted ladder, or that a candidate is safe to promote. Any engine-blob change
requires a separately reviewed oracle version; this version refuses drift.
