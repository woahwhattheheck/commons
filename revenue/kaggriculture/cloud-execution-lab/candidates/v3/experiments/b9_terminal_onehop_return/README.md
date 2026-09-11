# B9 — terminal one-hop cargo return

Status: **default-off practice arm; no score, default, package, or promotion claim.**

## Source theorem

Frozen V3.1 R04 has a hard terminal boundary. On step 718 it ignores the authored route tape and
calls `liquidate(view)`. That terminal action:

1. issues `DROP` for every worker that is already beside the shed and carries inventory;
2. projects those drops into the shed up to capacity; and
3. requests a SELL for every projected-shed product in the same final turn.

A worker carrying saleable product one move away from a shed access tile at step 717 can therefore
convert an otherwise literal parent `PASS` into a deterministic one-step return. The next call is
unconditional liquidation, so this exact one-turn substitution cannot steal a later tape worker
obligation.

This is intentionally **not** a general last-seven-turn planner. Workers farther than one move
from home, workers with any non-product cargo, and non-PASS parent commands remain untouched.
Those cases require a separate future-obligation proof.

## Admission contract

B9 activates only when all of the following are true:

- exact step 717 (`LAST_STEP - 1`);
- standard type-strict runtime configuration: board 10, 24 turns/day, shed capacity 100, max market
  rows 10;
- well-formed player, farm positions, private inventories and shed quantities;
- a worker's **literal parent command is `['PASS']`**;
- the worker carries at least one product and every positive carried item is an official saleable
  product;
- its nearest shed access tile is exactly Manhattan distance one;
- every admitted worker can return together without exceeding shed capacity on the final DROP.

The capacity proof uses the incumbent `projected_shed(parent_action, FarmView(observation))` for
step 717, so same-turn nearby PICKUP/DROP/PLACE effects are included in worker order. It then adds
all B9-admitted cargo and requires the total to be `<= 100`. Current market SELLs are deliberately
ignored for room credit; they execute after worker actions and can only reduce shed occupancy
before step 718, so ignoring them is conservative.

Any malformed/type-loose state, capacity ambiguity, non-PASS command, distance other than one, or
positive non-product cargo preserves the exact parent action.

## What B9 does not prove

The source theorem proves a deterministic path to the terminal liquidation mechanism. It does not
prove that exact V3.1 games actually reach step 717 with eligible stranded cargo, nor that the
extra sale improves paired competitive margin after market externalities. Existing dynamic return
logic (for example late V219 WOOL/FERTILIZER service cargo) may make the lane mostly inert.

## Required gate

Before any promotion, run the exact frozen-package official interpreter with telemetry for:

- activation step/actor/product/quantity and pre-move position;
- step718 observed position and exact DROP command;
- projected vs actual shed deposit quantity and any discarded overflow;
- terminal SELL requested/fill/price/cash by product;
- control vs candidate terminal carried inventory;
- `Delta own`, `Delta rival`, and paired `Delta margin` across both seats and multiple opponent
  families.

Kill the lane on zero activation, any activation that does not realize a terminal deposit+sale,
any changed non-PASS worker command or market row, any overflow/discard increase, or negative
paired margin.
