# B6 dead-stock sweep — practice arm

## Hypothesis

R04 can carry shed inventory for many turns even after the authored route has no remaining
farm action that will consume that product. Those units are operationally dead stock: they
still occupy shed capacity and wait for later market timing/terminal liquidation despite no
future production dependency.

B6 tests a fail-closed market-timing transform. From step 144 onward, sell current projected
shed units only when the product has **no remaining native or queued `PICKUP` consumer** in
the known route. This is not a claim that the units would otherwise be unsold: R04 still has
future planned sales and terminal liquidation. The economic hypothesis is that advancing
operationally dead inventory can free capacity and beat later adverse price pressure.

## Why the future-consumer proof is knowable

After R04's route selection at step 144, `DayState.plan` is fixed through step 647. At step
648, R04 deterministically forces plan 2 through the terminal turn. Therefore the candidate
can enumerate every remaining native tape command without predicting a rival or hidden
future observation. `repair_weeds()` can delay an already-authored command; its pending
commands live in `state.queues`, which B6 scans separately.

A single future/queued `PICKUP PRODUCT` vetoes *all* current stock of that product. That is
intentionally conservative.

Two dynamic outer layers create consumers that are not fully represented by the static active
tape, so B6 permanently reserves them:

- `WHEAT` — V233 sheep service and V217 rescue can buy/pick it up for feed;
- `FERTILIZER` — V219 tomato workers can buy/pick it up for fertilization.

## Exact baseline custody

The raw evaluator entrypoint pins the deterministic V3.1 R04 settings from `apply_v3.py` at
canonical base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`:

- sale horizon `8`
- opening round trip `0`
- row order ON
- evening flush ON
- fertilizer sale advancement ON (`SALE_EXCLUDED == ('WHEAT',)`)
- cattle-early ON

No `overlay/**`, `apply_v3.py`, manifest/config default, package input, evaluator, opponent,
or Kaggle artifact is modified by this experiment.

## Transform contract

`dead_stock_sweep()`:

1. is exact identity when disabled, before route selection, and on the terminal turn;
2. starts with `WHEAT/FERTILIZER` blocked;
3. blocks every product appearing in a pending weed-repair queue `PICKUP`;
4. scans the active tape through 647 and forced plan 2 from 648 onward, blocking every
   product with any remaining native `PICKUP`;
5. blocks a same-turn `BUY_PRODUCT` of the same product to avoid an accidental round trip;
6. uses R04's own `projected_shed()` so current worker `PICKUP/DROP/PLACE` effects use the
   same shed projection semantics as the shipped router;
7. subtracts quantity already sold by the parent action;
8. never removes, compacts, or reorders a parent market row (including defensive empty rows);
9. appends B6 rows only after every parent row, preserving every parent row's original
   cross-player execution index;
10. uses only free `MAX_ORDERS` slots and otherwise fails closed;
11. refuses a sale at displayed quote `< 2`.

When several safe B6 rows compete for limited trailing slots, selection uses the same
current displayed quote × quantity priority as shipped `EVENING_FLUSH`.

Telemetry records activations, rows/units advanced, displayed quote-value, order-cap declines,
and counts of native/queued/same-turn-buy vetoes. Displayed quote-value is **not** realized
proceeds.

## Kill / promotion criteria

A source blocker is any trace where B6 sells a unit later required by an authored or queued
farm consumer, mutates/removes/shifts a parent row, exceeds the market-order cap, or misses a
dynamic WHEAT/FERTILIZER dependency.

Passing focused tests only makes this a source-custody practice arm. Economics must beat the
exact V3.1 control on paired seats and multiple opponent types before any promotion. Under
the current SIM FIDELITY STANDARD, official 1:1 evidence additionally requires canonical
build/materialization + live submission config, the pinned official interpreter, the frozen
paired seed panel, and an exact opponent fingerprint.
