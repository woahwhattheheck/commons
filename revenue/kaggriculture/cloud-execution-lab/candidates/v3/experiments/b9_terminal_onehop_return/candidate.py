#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""B9 practice arm: one safe terminal return step for stranded saleable cargo.

At step 718 frozen R04 ignores the authored tape and calls ``liquidate(view)``.  That function
issues DROP only for workers already beside the shed, then sells projected shed products in the
same final action.  Therefore a worker at step 717 with literal parent PASS, product-only cargo
and Manhattan distance exactly one from a shed access tile can use that otherwise-idle action
to move home.  There is no later productive tape obligation to steal: the only remaining call
is unconditional liquidation.

The experiment is deliberately limited to this one-turn theorem.  It does not attempt a general
seven-turn route search.  A conservative capacity proof requires all admitted cargo to fit in
shed space projected *before* the step-717 market sells; any current sale can only create more
room before step 718.
"""
from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
BOARD_SIZE = 10
TURNS_PER_DAY = 24
SHED_CAPACITY = 100
MAX_ORDERS = 10
B9_ENABLED = False
telemetry = Counter()


def _cfg(configuration, name, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _standard_config(configuration):
    expected = {
        "boardSize": BOARD_SIZE,
        "turnsPerDay": TURNS_PER_DAY,
        "shedCapacity": SHED_CAPACITY,
        "maxMarketOrdersPerTurn": MAX_ORDERS,
    }
    for name, value in expected.items():
        actual = _cfg(configuration, name, value)
        if type(actual) is not int or actual != value:
            return False
    return True


def _position(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or type(value[0]) is not int or type(value[1]) is not int):
        return None
    x, y = value
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        return None
    return x, y


def _move_one(pos, target):
    x, y = pos
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return None


def _nearest_home(pos):
    return min(ACCESS, key=lambda p: (abs(pos[0] - p[0]) + abs(pos[1] - p[1]), p))


def _inventory_shape(inv):
    """Return (saleable_total, product_only) or None for malformed inventory."""
    if not isinstance(inv, dict):
        return None
    saleable = 0
    product_only = True
    for item, quantity in inv.items():
        if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
            return None
        if not quantity:
            continue
        if item in base.PRODUCTS:
            saleable += quantity
        else:
            product_only = False
    return saleable, product_only


def _strict_observation_parts(observation):
    try:
        step = observation["step"]
        player = observation["player"]
        farm = observation["farms"][player]
        private = observation["private"]
        inventories = private["inventories"]
        shed = private["shed"]
    except (KeyError, IndexError, TypeError):
        return None
    if type(step) is not int or type(player) is not int or player < 0:
        return None
    if not isinstance(farm, dict) or not isinstance(private, dict):
        return None
    hands = farm.get("hands")
    if not isinstance(hands, list) or not isinstance(inventories, list):
        return None
    positions_raw = [farm.get("farmer"), *hands]
    if len(inventories) < len(positions_raw):
        return None
    positions = []
    for raw in positions_raw:
        pos = _position(raw)
        if pos is None:
            return None
        positions.append(pos)
    for inv in inventories:
        if _inventory_shape(inv) is None:
            return None
    if not isinstance(shed, dict):
        return None
    for item, quantity in shed.items():
        if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
            return None
    return step, positions, inventories, shed


def terminal_onehop_return(action, observation, configuration=None, enabled=False):
    """Move eligible PASS workers exactly one step home on step 717, else parent identity."""
    telemetry["calls"] += 1
    if not enabled:
        telemetry["disabled"] += 1
        return action
    if not isinstance(action, dict) or not _standard_config(configuration):
        telemetry["malformed"] += 1
        return action
    parts = _strict_observation_parts(observation)
    if parts is None:
        telemetry["malformed"] += 1
        return action
    step, positions, inventories, _shed = parts
    if step != base.LAST_STEP - 1:
        return action

    farmer = action.get("farmer")
    hands = action.get("hands")
    market = action.get("market")
    if not isinstance(farmer, list) or not isinstance(hands, list) or not isinstance(market, list):
        telemetry["malformed"] += 1
        return action
    commands = [farmer, *hands]
    if len(commands) != len(positions):
        telemetry["malformed"] += 1
        return action

    replacements = {}
    cargo_total = 0
    for actor, (command, pos, inv) in enumerate(zip(commands, positions, inventories)):
        shape = _inventory_shape(inv)
        if shape is None:
            telemetry["malformed"] += 1
            return action
        saleable, product_only = shape
        if command != ["PASS"] or not saleable or not product_only:
            continue
        home = _nearest_home(pos)
        distance = abs(pos[0] - home[0]) + abs(pos[1] - home[1])
        if distance != 1:
            continue
        move = _move_one(pos, home)
        if move is None:
            continue
        replacements[actor] = move
        cargo_total += saleable

    if not replacements:
        return action

    # Account conservatively for every same-turn nearby PICKUP/DROP/PLACE from the untouched
    # parent action.  Ignore current market SELLs: they execute after unit work and can only
    # lower the shed total before the terminal DROP next turn.
    try:
        projected = base.projected_shed(action, base.FarmView(observation))
    except (KeyError, IndexError, TypeError, ValueError):
        telemetry["malformed"] += 1
        return action
    if any(type(quantity) is not int or quantity < 0 for quantity in projected.values()):
        telemetry["malformed"] += 1
        return action
    projected_total = sum(projected.values())
    if projected_total + cargo_total > SHED_CAPACITY:
        telemetry["capacity_block"] += 1
        return action

    out = copy.deepcopy(action)
    out_commands = [out["farmer"], *out["hands"]]
    for actor, move in replacements.items():
        out_commands[actor] = move
    out["farmer"] = out_commands[0]
    out["hands"] = out_commands[1:]

    telemetry["activations"] += 1
    telemetry["workers_returned"] += len(replacements)
    telemetry["cargo_units_returned"] += cargo_total
    telemetry["projected_room_before_terminal"] += SHED_CAPACITY - projected_total
    return out


def b9_agent(observation, configuration=None):
    action = base.v3_agent(observation, configuration)
    return terminal_onehop_return(action, observation, configuration, enabled=B9_ENABLED)


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None, b9_enabled=None):
    global B9_ENABLED
    base.install(host, horizon, opening, row_order, evening_flush, sale_fertilizer, cattle_early)
    if b9_enabled is not None:
        B9_ENABLED = bool(b9_enabled)
    return b9_agent


agent = install(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    b9_enabled=True,
)

B9_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "b9_terminal_onehop_return": True,
    "official_interpreter_commit": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
}

agent.telemetry = telemetry
