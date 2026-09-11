# SPDX-License-Identifier: Apache-2.0
"""V4 F2: pre-buy WHEAT only when it unlocks shipped V217 starvation rescue.

V217 already owns the feeding decision. This helper does not route a worker or
feed an animal itself. At hour 15 it asks a narrower counterfactual question:
would V217 be unable to schedule a step-16 pickup/feed rescue with the current
shed, but able to schedule one if one or two WHEAT were already in the shed?

The market order is emitted one callback before V217's earliest active hour
because farm actions execute before market orders in a turn. The lane ships
off as ``r04_feed_prebuy``.
"""
from __future__ import annotations

import copy

_PRODUCT_BY_ANIMAL = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
_MAX_PREBUY = 2
_CASH_RESERVE = 1000
_PRICE_PAD = 10

REPORT = {"probes": 0, "armed": 0, "units_requested": 0,
          "baseline_rescue": 0, "no_proxy_rescue": 0}


def _plain_nonnegative_int(value):
    return type(value) is int and value >= 0


def _config_ok(configuration, r04):
    if configuration is None:
        return True
    if not isinstance(configuration, dict):
        return False
    market_params = configuration.get("marketParams")
    if market_params not in (None, {}):
        return False
    cap = configuration.get("maxMarketOrdersPerTurn", r04.MAX_ORDERS)
    return type(cap) is int and cap >= 1


def _all_pass(action):
    if not isinstance(action, dict):
        return False
    farmer = action.get("farmer") or ["PASS"]
    hands = action.get("hands") or []
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return False
    return farmer == ["PASS"] and all(command == ["PASS"] for command in hands)


def _proxy_view(observation, quantity, r04):
    proxy = copy.deepcopy(observation)
    private = proxy.get("private")
    if not isinstance(private, dict):
        return None
    shed = private.get("shed")
    if not isinstance(shed, dict):
        return None
    wheat = shed.get("WHEAT", 0)
    if not _plain_nonnegative_int(wheat):
        return None
    shed["WHEAT"] = wheat + quantity
    try:
        return r04.FarmView(proxy)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return None


def _next_v217_task(observation, action, quantity, r04):
    """Return V217's next-step task under an exact WHEAT shed increment."""
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int:
        return None
    if step % 24 != 15 or step + 1 > r04.LAST_STEP:
        return None

    policy = getattr(r04, "_POLICY", None)
    players = getattr(policy, "players", None)
    tapes = getattr(policy, "tapes", None)
    if not isinstance(players, dict) or not isinstance(tapes, list):
        return None
    state = players.get(player)
    if state is None or getattr(state, "last_step", None) != step:
        return None
    if getattr(state, "queues", None) is None:
        return None
    if any(state.queues.values()) or getattr(state, "v217_task", None):
        return None

    st = vars(state)
    if st.get("v217_used", 0) >= 2:
        return None
    plan = st.get("plan")
    if type(plan) is not int or not 0 <= plan < len(tapes):
        return None
    tape = tapes[plan]
    next_step = step + 1
    if not isinstance(tape, list) or next_step >= len(tape):
        return None
    planned = tape[next_step]
    if not isinstance(planned, dict):
        return None
    next_action = {
        "farmer": list(planned.get("farmer") or ["PASS"]),
        "hands": copy.deepcopy(planned.get("hands") or []),
        "market": copy.deepcopy(planned.get("market") or []),
    }
    if next_action["farmer"] != ["PASS"]:
        return None

    pending = [cmd for queue in state.queues.values() for cmd in queue]
    if pending:
        return None

    if quantity:
        view = _proxy_view(observation, quantity, r04)
    else:
        try:
            view = r04.FarmView(observation)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
            return None
    if view is None:
        return None
    return r04._v217_plan(view, st, next_step, next_action, pending)


def _purchase_quantity(observation, action, configuration, r04):
    if not _config_ok(configuration, r04) or not _all_pass(action):
        return None
    market = action.get("market")
    if not isinstance(market, list) or market:
        return None

    private = observation.get("private")
    shed = private.get("shed") if isinstance(private, dict) else None
    if not isinstance(shed, dict):
        return None
    if any(not _plain_nonnegative_int(quantity) for quantity in shed.values()):
        return None
    used = sum(shed.values())
    if used >= r04.SHED_CAPACITY:
        return None

    baseline = _next_v217_task(observation, action, 0, r04)
    if baseline is not None:
        REPORT["baseline_rescue"] += 1
        return None

    task = None
    quantity = None
    for candidate in range(1, _MAX_PREBUY + 1):
        if used + candidate > r04.SHED_CAPACITY:
            break
        task = _next_v217_task(observation, action, candidate, r04)
        if task is not None:
            quantity = candidate
            break
    if task is None or quantity is None:
        REPORT["no_proxy_rescue"] += 1
        return None

    market_state = observation.get("market")
    prices = market_state.get("prices") if isinstance(market_state, dict) else None
    farms = observation.get("farms")
    player = observation.get("player")
    if not isinstance(prices, dict) or not isinstance(farms, list):
        return None
    if type(player) is not int or not 0 <= player < len(farms):
        return None
    wheat_price = prices.get("WHEAT")
    if type(wheat_price) is not int or wheat_price <= 0:
        return None

    target = task.get("target")
    try:
        x, y = target
        tile = farms[player]["tiles"][y][x]
    except (TypeError, ValueError, KeyError, IndexError):
        return None
    if not isinstance(tile, dict):
        return None
    product = _PRODUCT_BY_ANIMAL.get(tile.get("animal"))
    output_price = prices.get(product) if product else None
    if type(output_price) is not int:
        return None
    if output_price < wheat_price + 20 or output_price * 2 < wheat_price * 3:
        return None

    farm = farms[player]
    money = farm.get("money") if isinstance(farm, dict) else None
    if type(money) is not int or money < 0:
        return None
    conservative_cost = quantity * (wheat_price + _PRICE_PAD)
    if money < conservative_cost + _CASH_RESERVE:
        return None
    return quantity


def apply_feed_prebuy(observation, action, configuration=None, enabled=False):
    if not enabled:
        return action
    if not isinstance(observation, dict) or type(observation.get("step")) is not int:
        return action
    if observation["step"] % 24 != 15:
        return action

    import r04_full_router as r04

    REPORT["probes"] += 1
    try:
        quantity = _purchase_quantity(observation, action, configuration, r04)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
    if quantity is None:
        return action

    out = dict(action)
    out["market"] = [["BUY_PRODUCT", "WHEAT", quantity]]
    REPORT["armed"] += 1
    REPORT["units_requested"] += quantity
    return out
