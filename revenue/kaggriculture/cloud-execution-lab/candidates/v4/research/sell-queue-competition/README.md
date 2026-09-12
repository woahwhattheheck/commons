# SELL queue competition oracle (research only)

This package isolates the market-execution effect surfaced by fresh hosted TITAN mirror losses. It does **not** activate a controller, alter defaults, or assume access to a rival's current action. It answers one conditional question: if the rival submits the same unique-product leading SELL block as our incumbent queue, which permutation of those same rows maximizes our one-callback revenue edge under the official engine?

## Source-real mechanism

The official engine processes market rows by raw queue index. For a SELL at a shared index it quotes both players against the same pre-commit inventory for each unit, then commits both sales. Equal same-product rows at the same index therefore tie. If one copy of that row appears earlier, it sells before the mirrored dump has depressed the public quote; if it appears later, it pays the symmetric displacement cost.

That exact displacement is the **cumulative first-seller revenue minus second-seller revenue** for the fillable units. It is not the existing ROWSHED endpoint proxy `(P(I)-P(I+fill))*fill`.

A pinned-curve witness at public `MELON=10025`, `WOOL=10025` with fillable `MELON 60`, `WOOL 30` shows the distinction:

| product | ROWSHED endpoint proxy | exact mirror displacement |
| --- | ---: | ---: |
| MELON 60 | 3,960 | **6,083** |
| WOOL 30 | **4,200** | 3,071 |

So the proxy keeps the mirror baseline `[WOOL30, MELON60]` and earns no edge. The exact mirror optimizer chooses `[MELON60, WOOL30]`; the direct lockstep simulator produces candidate revenue 13,124 vs opponent 10,112, a **+$3,012** one-callback edge.

The deterministic bounded scan in `scan_proxy_inversions()` checks 19,008 source-real two-product cells and finds 466 proxy/exact ranking inversions; the witness above is the largest missed pair edge in that grid.

## Why this is an assignment problem

It is not sufficient to sort rows by descending displacement cost. Moving one row earlier necessarily moves another later. For synthetic costs `[1, 5, 10]`, descending `[10,5,1]` yields mirror edge `+9`, while original-index permutation `[1,2,0]` yields `+14`: two valuable rows advance and the cheap row pays the delay. `optimal_indices()` solves the exact assignment with bitmask DP in `O(n*2^n)` for the engine's at-most-10 executable market slots.

## Admission boundary

The theorem is deliberately narrow and fail-closed. The optimized block must be the leading executable SELL block, each product may appear at most once, quantities and public inventory / own shed counts must be literal integers, and only fillable own stock is valued. A non-SELL / falsey row ends the block; rows beyond `maxMarketOrdersPerTurn` are inert. Negative public inventory is accepted because town consumption can make it a valid engine state. Duplicate-product SELL blocks are rejected rather than given an unproven decomposition.

The package does **not** claim rival current-action observability, universal mirror behavior, or general dominance versus arbitrary queues. Hosted/replay evidence must independently establish when the mirror hypothesis is a useful candidate gate. No `runtime`, `default`, `config`, `COMPOSITION`, `INTEGRATION`, archive, or Kaggle activation is made here.

## Validation

From this directory:

```bash
python -B -m unittest -v test_sell_queue_competition.py
python -O -B -m unittest -v test_sell_queue_competition.py
python -B -m py_compile sell_queue_competition.py test_sell_queue_competition.py
python -B sell_queue_competition.py --output /tmp/sell-queue-competition.json
```

The final command authenticates and executes the exact `cloud-execution-lab/mechanics.py` Git blob pinned in `sell_queue_competition.py`, then emits the witness, bounded proxy inversion scan, optimizer contract, and nonclaims as strict JSON evidence.
