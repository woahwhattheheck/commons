# SPDX-License-Identifier: Apache-2.0
"""V4 M1: pre-buy a bounded, already-authored WHEAT pickup under public scarcity.

This lane does not create feed work, animals, hands, land, seeds, or sales. V226
already owns the one-turn WHEAT shortage case. M1 only considers a literal
same-day pickup in the frozen route tape two to six steps ahead, and only while
public market inventory is moving down. The key ships off; economics are gated
separately under docs/V4.md.
"""
from __future__ import annotations

import copy
import math

MAX_ORDERS = 10
SHED_CAPACITY = 100
LOOKAHEAD_MIN = 2
LOOKAHEAD_MAX = 6
MAX_BUY = 4
MAX_DAILY_BUY = 8
CASH_RESERVE = 1000
_PURCHASE_OPS = {"HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_ANIMAL", "BUY_SEED"}
_SHED_INFLOW_OPS = {"DROP", "PLACE"}
_MOVES = {"EAST": (1, 0), "WEST": (-1, 0), "NORTH": (0, -1), "SOUTH": (0, 1)}
_SHED_ACCESS = frozenset(((4, 4), (4, 5), (5, 4), (5, 5)))
_STANDARD_CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}
_MISSING = object()

_STATE = {}
REPORT = {
    "calls": 0,
    "scarcity_steps": 0,
    "future_pickups": 0,
    "buy_orders": 0,
    "buy_units": 0,
    "funding_vetoes": 0,
    "capacity_vetoes": 0,
    "schedule_vetoes": 0,
}


def reset_for_tests():
    _STATE.clear()
    for key in REPORT:
        REPORT[key] = 0


def _plain_nonnegative_int(value):
    return type(value) is int and value >= 0


def _plain_nonnegative_money(value):
    """Engine money is float; reject bool/non-numeric/non-finite poison."""
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _cfg(configuration, name):
    if configuration is None:
        return _MISSING
    try:
        if isinstance(configuration, dict):
            return configuration.get(name, _MISSING)
        return getattr(configuration, name, _MISSING)
    except Exception:
        return _MISSING


def _standard_configuration(configuration):
    for name, expected in _STANDARD_CONFIG.items():
        actual = _cfg(configuration, name)
        if actual is _MISSING or type(actual) is not int or actual != expected:
            return False
    market_params = _cfg(configuration, "marketParams")
    return (market_params is _MISSING or market_params is None
            or (isinstance(market_params, dict) and not market_params))


def _commands(planned):
    if not isinstance(planned, dict):
        return None
    farmer = planned.get("farmer", _MISSING)
    hands = planned.get("hands", _MISSING)
    if (not isinstance(farmer, list) or not farmer
            or not isinstance(hands, list)
            or any(not isinstance(command, list) or not command for command in hands)):
        return None
    return [farmer, *hands]


def _market_rows(planned):
    if not isinstance(planned, dict):
        return None
    rows = planned.get("market", _MISSING)
    if not isinstance(rows, list) or any(row and not isinstance(row, list) for row in rows):
        return None
    return rows


def _parent_requests_wheat_buy(rows):
    """Whether the parent's executable raw prefix can lower public WHEAT stock.

    Quantity/fill exactness is deliberately not needed here. Any authored
    BUY_PRODUCT WHEAT in the official ten-row prefix makes the following public
    inventory transition causally ambiguous, so M1 suppresses that transition
    rather than letting another shipped controller self-certify scarcity.
    """
    if not isinstance(rows, list):
        return False
    return any(
        len(row) >= 2 and row[0] == "BUY_PRODUCT" and row[1] == "WHEAT"
        for row in rows[:MAX_ORDERS]
        if isinstance(row, list) and row
    )


def _actor_position(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or type(value[0]) is not int or type(value[1]) is not int
            or not 0 <= value[0] < 10 or not 0 <= value[1] < 10):
        return None
    return (value[0], value[1])


def _advance(position, operation):
    delta = _MOVES.get(operation)
    if delta is None:
        return position
    nx = position[0] + delta[0]
    ny = position[1] + delta[1]
    if 0 <= nx < 10 and 0 <= ny < 10:
        return (nx, ny)
    return position


def _future_literal_pickup(tape, step, actor_positions):
    """Return a funded same-day pickup executable by a current actor.

    The pickup candidate itself must remain two to six callbacks ahead. Before
    that pickup, only the official ten market rows are executable: HIRE/purchase
    rows there are funding vetoes, while dead raw-tail rows cannot suppress M1.
    DROP/PLACE and an earlier live WHEAT pickup make the shed path ambiguous.

    Current actor positions are replayed through literal bounded movement before
    the candidate callback. A counted pickup must belong to a live actor that is
    physically shed-adjacent when the engine would execute it. Once a candidate
    is found, keep its ``(due, demand)`` but continue scanning the selected tape
    through the rest of the same day: any executable-prefix HIRE/BUY row still
    owns future cash, so M1 may not spend against it now. Purchases on the next
    day do not block.
    """
    if not isinstance(actor_positions, (list, tuple)) or not actor_positions:
        return None, 0
    positions = []
    for value in actor_positions:
        position = _actor_position(value)
        if position is None:
            return None, 0
        positions.append(position)
    if not isinstance(tape, (list, tuple)) or len(tape) <= step + LOOKAHEAD_MIN:
        return None, 0

    day_end = min(len(tape) - 1, (step // 24 + 1) * 24 - 1)
    candidate_end = min(day_end, step + LOOKAHEAD_MAX)
    candidate_due = None
    candidate_demand = 0

    for due in range(step + 1, candidate_end + 1):
        planned = tape[due]
        if not isinstance(planned, dict):
            return None, 0
        rows = _market_rows(planned)
        commands = _commands(planned)
        if rows is None or commands is None:
            return None, 0
        # The engine executes only the official raw market prefix. A dead row
        # beyond MAX_ORDERS has no cash or inventory ownership and cannot veto.
        for row in rows[:MAX_ORDERS]:
            if not row:
                continue
            if not isinstance(row[0], str):
                return None, 0
            if row[0] in _PURCHASE_OPS:
                return None, 0
            if len(row) > 1 and row[1] == "WHEAT":
                return None, 0

        demand = 0
        saw_live_wheat_pickup = False
        for actor, command in enumerate(commands):
            if not isinstance(command[0], str):
                return None, 0
            if command[0] in _SHED_INFLOW_OPS:
                return None, 0
            is_wheat_pickup = len(command) >= 2 and command[:2] == ["PICKUP", "WHEAT"]
            if is_wheat_pickup:
                if actor >= len(positions):
                    # Extra tape hand rows do not imply a live hand. With HIRE
                    # vetoed before the pickup, this command cannot execute.
                    return None, 0
                quantity = command[2] if len(command) >= 3 else 1
                if not _plain_nonnegative_int(quantity):
                    return None, 0
                saw_live_wheat_pickup = True
                if due < step + LOOKAHEAD_MIN:
                    # An earlier executable pickup changes the exact shed stock
                    # path that the later shortage proof would use.
                    return None, 0
                if positions[actor] not in _SHED_ACCESS:
                    # Official PICKUP silently no-ops away from the shed; raw
                    # tape text is not enough to certify demand.
                    return None, 0
                demand += quantity

        if due >= step + LOOKAHEAD_MIN and saw_live_wheat_pickup and demand > 0:
            # An hour-23 pickup is immediately returned by EOD inventory drop;
            # prebuying solely for it cannot support later same-day work.
            if due % 24 == 23:
                return None, 0
            candidate_due = due
            candidate_demand = demand
            break

        # Unit actions at ``due`` determine positions for the next callback.
        # Extra non-live tape rows are engine no-ops and do not alter custody.
        for actor in range(min(len(commands), len(positions))):
            positions[actor] = _advance(positions[actor], commands[actor][0])

    if candidate_due is None:
        return None, 0

    # M1's market buy spends cash now. The certified pickup can occur before a
    # later same-day acquisition, so returning at the pickup would miss cash
    # ownership that baseline still has. Inspect only the official executable
    # market prefix after the pickup; next-day rows are outside this day's cash
    # contract and are intentionally not scanned.
    for due in range(candidate_due + 1, day_end + 1):
        planned = tape[due]
        if not isinstance(planned, dict):
            return None, 0
        rows = _market_rows(planned)
        if rows is None:
            return None, 0
        for row in rows[:MAX_ORDERS]:
            if not row:
                continue
            if not isinstance(row[0], str):
                return None, 0
            if row[0] in _PURCHASE_OPS:
                return None, 0

    return candidate_due, candidate_demand


def _observe_scarcity(player, step, day, wheat_inventory):
    previous = _STATE.get(player)
    if previous is None or step <= previous["last"]:
        previous = {"last": step, "inventory": wheat_inventory, "day": day,
                    "bought_today": 0, "last_buy": -1000}
        _STATE[player] = previous
        return previous, False
    if day != previous["day"]:
        previous["day"] = day
        previous["bought_today"] = 0
    contiguous = previous["last"] == step - 1
    self_induced = previous["last_buy"] == step - 1
    scarcity = contiguous and not self_induced and wheat_inventory < previous["inventory"]
    previous["last"] = step
    previous["inventory"] = wheat_inventory
    return previous, scarcity


def apply_m1_wheat_trade(observation, action, tape, route_state=None,
                         configuration=None, enabled=False):
    """Return ``action`` or a copy with one bounded BUY_PRODUCT WHEAT row appended."""
    if not enabled:
        return action
    REPORT["calls"] += 1
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action
    if not _standard_configuration(configuration):
        return action
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int or step < 24 or step >= 696:
        return action
    day = step // 24

    market_obs = observation.get("market")
    private = observation.get("private")
    farms = observation.get("farms")
    if not isinstance(market_obs, dict) or not isinstance(private, dict) or not isinstance(farms, list):
        return action
    if not (0 <= player < len(farms)) or not isinstance(farms[player], dict):
        return action
    inventory = market_obs.get("inventory")
    prices = market_obs.get("prices")
    shed = private.get("shed")
    farmer_position = farms[player].get("farmer")
    farm_hands = farms[player].get("hands")
    if (not isinstance(inventory, dict) or not isinstance(prices, dict)
            or not isinstance(shed, dict) or not isinstance(farm_hands, list)):
        return action
    actor_positions = [farmer_position, *farm_hands]
    if any(_actor_position(position) is None for position in actor_positions):
        return action
    wheat_market = inventory.get("WHEAT")
    wheat_price = prices.get("WHEAT")
    if not _plain_nonnegative_int(wheat_market) or type(wheat_price) is not int or wheat_price < 1:
        return action

    # Record parent-system WHEAT demand even on callbacks where M1 itself will
    # return early. Otherwise a V226/V234 buy at this step can lower public
    # inventory and falsely certify scarcity for M1 on the next callback.
    rows = _market_rows(action)
    if rows is None:
        return action
    parent_wheat_buy = _parent_requests_wheat_buy(rows)

    tracker, scarcity = _observe_scarcity(player, step, day, wheat_market)
    if parent_wheat_buy:
        tracker["last_buy"] = step
    if not scarcity:
        return action
    REPORT["scarcity_steps"] += 1

    if route_state is not None:
        try:
            if any(queue for queue in route_state.queues.values()) or vars(route_state).get("v217_task"):
                REPORT["schedule_vetoes"] += 1
                return action
        except Exception:
            return action

    commands = _commands(action)
    if (commands is None or len(rows) >= MAX_ORDERS
            or len(commands) != len(farm_hands) + 1):
        return action
    if any(command and command[0] in ("DROP", "PLACE", "PICKUP") for command in commands):
        return action
    for row in rows:
        if not row:
            continue
        if not isinstance(row[0], str):
            return action
        if row[0] in _PURCHASE_OPS or (len(row) > 1 and row[1] == "WHEAT"):
            REPORT["funding_vetoes"] += 1
            return action

    due, demand = _future_literal_pickup(tape, step, actor_positions)
    if due is None:
        return action
    REPORT["future_pickups"] += 1

    if any(not _plain_nonnegative_int(value) for value in shed.values()):
        return action
    wheat_stock = shed.get("WHEAT", 0)
    if not _plain_nonnegative_int(wheat_stock):
        return action
    total_stock = sum(shed.values())
    shortage = max(0, demand - wheat_stock)
    daily_room = MAX_DAILY_BUY - tracker["bought_today"]
    quantity = min(shortage, MAX_BUY, daily_room)
    if quantity <= 0 or wheat_market < quantity:
        return action
    if total_stock + quantity > SHED_CAPACITY:
        REPORT["capacity_vetoes"] += 1
        return action

    money = farms[player].get("money")
    if not _plain_nonnegative_money(money):
        return action
    conservative_cost = quantity * (wheat_price + 10)
    if money < CASH_RESERVE + conservative_cost:
        REPORT["funding_vetoes"] += 1
        return action

    out = copy.deepcopy(action)
    out["market"] = list(rows) + [["BUY_PRODUCT", "WHEAT", quantity]]
    tracker["bought_today"] += quantity
    tracker["last_buy"] = step
    REPORT["buy_orders"] += 1
    REPORT["buy_units"] += quantity
    return out
