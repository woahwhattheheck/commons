# SPDX-License-Identifier: Apache-2.0
"""V4 D4: repaired midgame STRAWBERRY sale timing, default-off.

This is the source-safe mechanism from repaired V3.1 D4 (#12469), adapted to
V4's shared key layer.  It never invents liquidation: it may advance only
STRAWBERRY quantity that is already in projected shed stock and already authored
to SELL later in the same day, beyond E184's current sale horizon and strictly
before the next incumbent EVENING_FLUSH callback.  The matching E184 debt is
recorded atomically so the future authored row is reduced by the same quantity.

Disabled, malformed, ambiguous, or no-op paths return the exact parent action
object and do not mutate the policy state.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any

import r04_full_router as base

ITEM = "STRAWBERRY"
START_DAY = 12
END_DAY = 18
DEFAULT_MIN_PRICE = 180
_MISSING = object()
telemetry = Counter()


def _strict_nonnegative_int(value):
    return value if type(value) is int and value >= 0 else None


def _standard_configuration(configuration):
    if configuration is None:
        return True
    if not isinstance(configuration, dict):
        return False
    for key, expected in (("turnsPerDay", 24), ("shedCapacity", 100),
                          ("maxMarketOrdersPerTurn", 10)):
        if key in configuration:
            value = configuration[key]
            if type(value) is not int or value != expected:
                return False
    params = configuration.get("marketParams")
    return params is None or params == {}


def _valid_debt_map(debts):
    """Validate the full inherited E184 debt ledger before D4 can mutate it."""
    if not isinstance(debts, dict):
        return False
    for due_step, ledger in debts.items():
        if type(due_step) is not int or not (0 <= due_step <= base.LAST_STEP):
            return False
        if not isinstance(ledger, dict):
            return False
        for item, quantity in ledger.items():
            if item not in base.PRODUCTS or _strict_nonnegative_int(quantity) is None:
                return False
    return True


def _next_incumbent_flush(step):
    """Return the next same-day live EVENING_FLUSH callback owning STRAWBERRY."""
    if not base.EVENING_FLUSH or ITEM not in base.FLUSH_ITEMS:
        return None
    day_start = (step // 24) * 24
    for hour in base.FLUSH_HOURS:
        flush_step = day_start + hour
        # The outer flush executes later in _v3_stack on this callback, so an
        # equal step already owns all residual eligible STRAWBERRY stock.
        if flush_step >= step:
            return flush_step
    return None


def advance_midgame_strawberry(action: Any, view: Any, state: Any, tape: Any, step: Any,
                                 *, min_price=DEFAULT_MIN_PRICE):
    """Return ``(action, added_qty, reservations)`` for the repaired D4 arm."""
    if not isinstance(action, dict):
        return action, 0, ()
    if type(min_price) is not int or min_price < 2:
        return action, 0, ()
    if type(step) is not int or step < START_DAY * 24 or step >= (END_DAY + 1) * 24:
        return action, 0, ()
    if step >= base.LAST_STEP:
        return action, 0, ()

    prices = getattr(view, "prices", None)
    if not isinstance(prices, dict):
        return action, 0, ()
    price = prices.get(ITEM)
    if type(price) is not int or price < min_price:
        return action, 0, ()

    market = action.get("market")
    farmer = action.get("farmer")
    hands = action.get("hands")
    if (not isinstance(market, list) or len(market) >= base.MAX_ORDERS
            or not isinstance(farmer, list) or not isinstance(hands, list)):
        return action, 0, ()

    # H4 owns current-row top-ups. D4 acts only when there is no current
    # STRAWBERRY trade at all.
    for order in market:
        if not isinstance(order, list) or not order:
            return action, 0, ()
        if len(order) > 1 and order[1] == ITEM and order[0] in ("SELL", "BUY_PRODUCT"):
            return action, 0, ()

    commands = [farmer, *hands]
    if any(not isinstance(command, list) or not command for command in commands):
        return action, 0, ()
    if any(len(command) > 1 and command[:2] == ["PICKUP", ITEM] for command in commands):
        return action, 0, ()

    queues = getattr(state, "queues", _MISSING)
    if not isinstance(queues, dict):
        return action, 0, ()
    for queue in queues.values():
        if not isinstance(queue, (list, tuple)) and not hasattr(queue, "__iter__"):
            return action, 0, ()
        if any(isinstance(command, list) and len(command) > 1
               and command[:2] == ["PICKUP", ITEM] for command in queue):
            return action, 0, ()

    # Match E184's animal-PLACE uncertainty guard; projected_shed deliberately
    # does not model a failed animal placement falling back into shed inventory.
    try:
        if any(len(command) > 1 and command[0] == "PLACE" and command[1] in base.ANIMALS
               and view.inventory(actor).get(command[1], 0) > 0
               for actor, command in enumerate(commands)):
            return action, 0, ()
        stock = base.projected_shed(action, view)
    except Exception:
        return action, 0, ()
    if not isinstance(stock, dict):
        return action, 0, ()
    available = _strict_nonnegative_int(stock.get(ITEM, 0))
    if not available:
        return action, 0, ()

    horizon = _strict_nonnegative_int(base.SALE_HORIZON)
    if horizon is None:
        return action, 0, ()

    start = step + horizon + 1
    end = min(base.LAST_STEP, (step // 24 + 1) * 24 - 1, (END_DAY + 1) * 24 - 1)
    next_flush = _next_incumbent_flush(step)
    if next_flush is not None:
        end = min(end, next_flush - 1)
    if start > end:
        return action, 0, ()

    debts_ref = getattr(state, "sale_window_debts", _MISSING)
    if debts_ref is _MISSING or not _valid_debt_map(debts_ref):
        return action, 0, ()
    if not isinstance(tape, (list, tuple)) or end >= len(tape):
        return action, 0, ()

    reservations = []
    remaining_stock = available
    for due_step in range(start, end + 1):
        future = tape[due_step]
        if not isinstance(future, dict):
            return action, 0, ()
        future_farmer = future.get("farmer") or ["PASS"]
        future_hands = future.get("hands") or []
        if not isinstance(future_farmer, list) or not isinstance(future_hands, list):
            return action, 0, ()
        work = [future_farmer, *future_hands]
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

        due_map = debts_ref.get(due_step, {})
        already = due_map.get(ITEM, 0)
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

    debts = {due: dict(items) for due, items in debts_ref.items()}
    for due_step, amount in reservations:
        due = debts.setdefault(due_step, {})
        due[ITEM] = due.get(ITEM, 0) + amount
    state.sale_window_debts = debts
    return result, added, tuple(reservations)


def apply_d4(action: Any, observation: Any, configuration: Any = None, *, enabled=False,
             min_price=DEFAULT_MIN_PRICE):
    """Apply D4 against the current R04 policy state/tape; fail closed on ambiguity."""
    if not enabled:
        return action
    if type(min_price) is not int or min_price < 2 or not _standard_configuration(configuration):
        return action
    if not isinstance(observation, dict):
        return action
    step = observation.get("step", _MISSING)
    player = observation.get("player", _MISSING)
    if type(step) is not int or type(player) is not int or player not in (0, 1):
        return action

    policy = getattr(base, "_POLICY", None)
    if policy is None:
        return action
    try:
        state = policy.players.get(player)
        if state is None:
            return action
        plan = state.plan
        if type(plan) is not int or plan < 0 or plan >= len(policy.tapes):
            return action
        tape = policy.tapes[plan]
        view = base.FarmView(observation)
    except Exception:
        telemetry["malformed_state_block"] += 1
        return action

    result, added, reservations = advance_midgame_strawberry(
        action, view, state, tape, step, min_price=min_price)
    if added:
        telemetry["activations"] += 1
        telemetry["units_advanced"] += added
        telemetry["reservation_rows"] += len(reservations)
        telemetry["price_x_units"] += int(view.prices[ITEM]) * added
    return result
