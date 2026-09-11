# E5 — pre-terminal floor-rule liquidation

Status: **default-OFF experiment / source theorem only / no economics or promotion claim**.

## Narrow engine theorem

This is deliberately **not** a generic "sell when price is low" policy.

Under the standard Kaggriculture configuration, the last actionable R04 step is 718. Town-shop consumption runs every 4 steps, so the last shop tick is step 716; town-center consumption runs every 24 steps, so its last tick is step 696. No default town-demand tick occurs on steps 717 or 718.

The official market loop also has an unusual hard-floor rule: a successful `SELL` at quoted price `$1` removes the unit from the player's shed and pays `$1`, but **does not add market supply**. Therefore, if no player can buy that product and no town tick remains, selling it at `$1` on step 717 cannot depress its terminal price and cannot give up a later price recovery.

The live R04 controller already liquidates all reachable shed inventory on step 718. The only reason to move a floor sale one turn earlier is capacity: a step-717 sale can free shed room before the existing step-718 `DROP`, allowing carried inventory to enter the shed instead of being blocked by the 100-unit capacity and then be sold by the unchanged terminal liquidator.

## Exact experiment scope

The transform may act **only** when all of these are true:

- step is exactly `717` (`LAST_STEP - 1`);
- configuration is exactly the standard integer tuple: 720 episode steps, 24 turns/day, 10 market orders/turn, shed capacity 100, shop interval 4, town-center interval 24;
- observed price is exactly integer `$1`;
- product is one of `CARROT, TOMATO, STRAWBERRY, MELON, EGG, MILK, WOOL`.

`WHEAT` and `FERTILIZER` are excluded because they are player-buyable and have farm-service value. The transform never edits or reorders a parent row. It appends residual floor SELL rows only into unused market slots after every parent row, so the extra cash cannot make an earlier parent purchase newly affordable. Existing same-item SELL quantity is subtracted from projected shed stock; malformed same-item SELL quantity fails closed.

The base entrypoint explicitly binds the current live V3.1 R04 tuple: horizon 8, opening roundtrip 0, row-order ON, evening-flush ON, fertilizer sale advancement ON, cattle-early ON. E5 is outermost and only sees the already-finalized parent action.

## Required economics gate

Source safety does not imply score value. The experiment is useful only when floor stock exists on step 717 and capacity would otherwise block terminal deposits. Before any package/default promotion, run exact materialized V3.1 control vs exact E5 on identical seeds/seats/opponents and report:

- E5 activations, rows and quantity sold at `$1`;
- shed occupancy before/after step 717;
- worker-held units before the terminal DROP and terminal units actually deposited/sold;
- own cash delta, rival cash delta, paired competitive ΔM, W/T/L transitions and every negative cell;
- exact engine, package/config, panel and opponent custody under the fleet fidelity standard.

Kill the lane if activations do not increase terminal monetized quantity, if any parent row changes, or if paired competitive margin regresses materially.

No file here is a deterministic V3 package input; no overlay/default/canonical/evaluator/Kaggle state is changed by this experiment.
