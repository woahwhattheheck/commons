# SPDX-License-Identifier: Apache-2.0
"""TITAN V3.1 D4 experiment: advance high-price midgame STRAWBERRY sales.

This module is evidence-only and default-off. It does not invent liquidation.
It only advances STRAWBERRY quantity that is already scheduled by the selected
R04 tape later in the *same day*, is beyond the parent E184 sale horizon, and is
already present in the projected shed now. The corresponding E184-style debt is
recorded on the authored due step so the future row is reduced by exactly the
quantity advanced here.

The narrow purpose is to test the private-field D4 hypothesis (midgame
STRAWBERRY timing) without changing workers, route selection, other market rows,
or the parent sale horizon. H4 remains owner of topping-up an existing current
STRAWBERRY row; D4 requires no current STRAWBERRY SELL and therefore covers a
distinct temporal gap.
"""

from __future__ import annotations

import copy

import r04_full_router as base

KEY = "d4_strawberry_midgame"
ITEM = "STRAWBERRY"
START_DAY = 12
END_DAY = 18
D4_MIN_PRICE = None  # None is exact identity / disabled.


def _strict_nonnegative_int(value):
    return value if type(value) is int and value >= 0 else None


def advance_midgame_strawberry(action, view, state, tape, step, *, min_price=None):
    """Return ``(action, added_qty, reservations)`` for the D4 timing arm.

    ``reservations`` is a tuple of ``(due_step, qty)`` pairs. On every no-op the
    exact input ``action`` object is returned and state is untouched.
    """
    if min_price is None or type(min_price) is not int or min_price < 2:
        return action, 0, ()
    if type(step) is not int or step < START_DAY * 24 or step >= (END_DAY + 1) * 24:
        return action, 0, ()
    if step >= base.LAST_STEP:
        return action, 0, ()

    price = view.prices.get(ITEM)
    if type(price) is not int or price < min_price:
        return action, 0, ()

    market = action.get("market")
    if not isinstance(market, list) or len(market) >= base.MAX_ORDERS:
        return action, 0, ()

    # H4 owns current-row top-ups. D4 acts only when the parent emitted no
    # current STRAWBERRY trade at all.
    for order in market:
        if not isinstance(order, list) or not order:
            return action, 0, ()
        if len(order) > 1 and order[1] == ITEM and order[0] in ("SELL", "BUY_PRODUCT"):
            return action, 0, ()

    commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    if any(not isinstance(command, list) or not command for command in commands):
        return action, 0, ()
    if any(len(command) > 1 and command[:2] == ["PICKUP", ITEM] for command in commands):
        return action, 0, ()
    for queue in state.queues.values():
        if not isinstance(queue, (list, tuple)) and not hasattr(queue, "__iter__"):
            return action, 0, ()
        if any(isinstance(command, list) and len(command) > 1
               and command[:2] == ["PICKUP", ITEM] for command in queue):
            return action, 0, ()

    # Match E184's animal-PLACE uncertainty guard; projected_shed deliberately
    # does not model a failed animal placement falling back into shed inventory.
    if any(len(command) > 1 and command[0] == "PLACE" and command[1] in base.ANIMALS
           and view.inventory(actor).get(command[1], 0) > 0
           for actor, command in enumerate(commands)):
        return action, 0, ()

    stock = base.projected_shed(action, view)
    available = _strict_nonnegative_int(stock.get(ITEM, 0))
    if not available:
        return action, 0, ()

    horizon = _strict_nonnegative_int(base.SALE_HORIZON)
    if horizon is None:
        return action, 0, ()

    # The parent already owns step+1 .. step+horizon. D4 only examines the
    # remaining same-day window, so H13 can change the parent horizon without
    # double-booking D4.
    start = step + horizon + 1
    end = min(base.LAST_STEP, (step // 24 + 1) * 24 - 1, (END_DAY + 1) * 24 - 1)
    if start > end:
        return action, 0, ()

    original_debts = getattr(state, "sale_window_debts", {})
    if not isinstance(original_debts, dict):
        return action, 0, ()

    reservations = []
    remaining_stock = available
    for due_step in range(start, end + 1):
        future = tape[due_step]
        if not isinstance(future, dict):
            return action, 0, ()
        work = [future.get("farmer") or ["PASS"], *(future.get("hands") or [])]
        if any(not isinstance(command, list) or not command for command in work):
            return action, 0, ()
        if any(len(command) > 1 and command[:2] == ["PICKUP", ITEM] for command in work):
            break
        future_market = future.get("market") or []
        if not isinstance(future_market, list):
            return action, 0, ()
        if any(isinstance(order, list) and len(order) > 1
               and order[:2] == ["BUY_PRODUCT", ITEM] for order in future_market):
            break

        planned = 0
        for order in future_market:
            if not isinstance(order, list) or not order:
                return action, 0, ()
            if len(order) >= 2 and order[:2] == ["SELL", ITEM]:
                if len(order) < 3:
                    return action, 0, ()
                qty = _strict_nonnegative_int(order[2])
                if qty is None:
                    return action, 0, ()
                planned += qty

        due_map = original_debts.get(due_step, {})
        if not isinstance(due_map, dict):
            return action, 0, ()
        already = _strict_nonnegative_int(due_map.get(ITEM, 0))
        if already is None:
            return action, 0, ()
        remaining_due = max(0, planned - already)
        amount = min(remaining_stock, remaining_due)
        if amount:
            reservations.append((due_step, amount))
            remaining_stock -= amount
        if not remaining_stock:
            break

    added = sum(amount for _, amount in reservations)
    if not added:
        return action, 0, ()

    result = copy.deepcopy(action)
    result["market"].append(["SELL", ITEM, added])

    debts = {due: dict(items) for due, items in original_debts.items()}
    for due_step, amount in reservations:
        due = debts.setdefault(due_step, {})
        due[ITEM] = due.get(ITEM, 0) + amount
    state.sale_window_debts = debts
    return result, added, tuple(reservations)


def d4_agent(observation, configuration=None):
    """Live-R04 wrapper with D4 inserted before ROW_ORDER and EVENING_FLUSH."""
    action = base.POLICY_AGENT(observation, configuration)
    if D4_MIN_PRICE is not None and base._POLICY is not None:
        player = int(observation["player"])
        state = base._POLICY.players.get(player)
        if state is not None:
            view = base.FarmView(observation)
            tape = base._POLICY.tapes[state.plan]
            action, added, reservations = advance_midgame_strawberry(
                action, view, state, tape, int(observation["step"]), min_price=D4_MIN_PRICE
            )
            if added:
                state.d4_last = {
                    "step": int(observation["step"]),
                    "price": int(view.prices[ITEM]),
                    "quantity": added,
                    "reservations": reservations,
                }

    # Preserve the live V3.1 post-policy order exactly.
    if base.ROW_ORDER and not ((configuration or {}).get("marketParams") or {}):
        inventory = (observation.get("market") or {}).get("inventory") or {}
        market = [list(order) for order in action.get("market") or [] if order]
        ordered = base.order_sells(market, inventory)
        if ordered != market:
            action = dict(action)
            action["market"] = ordered
    if base.EVENING_FLUSH:
        action = base.evening_flush(observation, action)
    if (base.OPEN_ROUNDTRIP > 0 and int(observation["step"]) == 0
            and [list(order) for order in action.get("market") or []] == base.TAPE_OPENING):
        action = dict(action)
        action["market"] = [["BUY_PRODUCT", "WHEAT", 13],
                            ["BUY_PRODUCT", "WHEAT", base.OPEN_ROUNDTRIP],
                            ["SELL", "WHEAT", base.OPEN_ROUNDTRIP]]
    return action


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None, d4_min_price=None):
    """Configure parent R04 and this default-off D4 experiment."""
    global D4_MIN_PRICE
    base.install(host, horizon, opening, row_order, evening_flush,
                 sale_fertilizer, cattle_early)
    if d4_min_price is None:
        D4_MIN_PRICE = None
    elif type(d4_min_price) is not int or d4_min_price < 2:
        raise ValueError("d4_min_price must be an integer >= 2 or None")
    else:
        D4_MIN_PRICE = d4_min_price
    return d4_agent
