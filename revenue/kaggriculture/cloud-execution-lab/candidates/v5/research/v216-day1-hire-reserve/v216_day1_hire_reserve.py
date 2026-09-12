# SPDX-License-Identifier: Apache-2.0
"""Current-ABI recovery of submitted V3.1 V216 day-one hiring reserve.

V216 is an observation-only wrapper already present inside the exact submitted
V3.1 POLICY_AGENT.  At public step 23 only, it may replace an empty selected
market with exactly one WHEAT sell when the authenticated authored row 24
commits 1..5 HIREs and that single sale fully funds the Fibonacci hire deficit
while leaving at least two projected WHEAT in the shed.

This module is a selected-action transform only.  It never calls a producer or
controller, chooses a route, edits runtime configuration, or reads legacy tape.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Mapping

DONOR_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_full_router.py"
DONOR_GIT_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"
ROUTE_WITNESS_GIT_BLOB = "b84768c7560e746f6c9144fea672554e0dad39f7"
ROUTE_WITNESS_SCHEMA = "titan-v5-current-route-window-v2"
ROUTE_WITNESS_SOURCE = "committed_producer_route.R[route_id]"
STEP = 23
AUTHORED_STEP = 24
SHED_CAPACITY = 100
ANIMALS = frozenset(("GOOSE", "COW", "SHEEP"))
HIRE_FIB = (1, 1, 2, 3, 5)


def _identity(action: Any) -> Any:
    return copy.deepcopy(action)


def _plain_number(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _plain_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _command(command: Any) -> list[Any] | None:
    if not isinstance(command, list) or not command or not isinstance(command[0], str):
        return None
    return command


def _selected_shape(action: Any) -> tuple[list[list[Any]], list[Any]] | None:
    if not isinstance(action, dict):
        return None
    market = action.get("market")
    hands = action.get("hands")
    farmer = action.get("farmer")
    if not isinstance(market, list) or not isinstance(hands, list):
        return None
    commands = [farmer, *hands]
    if any(_command(row) is None for row in commands):
        return None
    if any(not isinstance(row, list) or not row or not isinstance(row[0], str) for row in market):
        return None
    return commands, market


def _observation_view(observation: Any) -> dict[str, Any] | None:
    if not isinstance(observation, dict) or observation.get("step") != STEP:
        return None
    player = observation.get("player")
    farms = observation.get("farms")
    private = observation.get("private")
    market = observation.get("market")
    if type(player) is not int or player not in (0, 1):
        return None
    if not isinstance(farms, list) or not (0 <= player < len(farms)):
        return None
    farm = farms[player]
    if not isinstance(farm, dict):
        return None
    positions = [farm.get("farmer"), *(farm.get("hands") if isinstance(farm.get("hands"), list) else [])]
    if not positions or any(
        not isinstance(pos, (list, tuple))
        or len(pos) != 2
        or type(pos[0]) is not int
        or type(pos[1]) is not int
        for pos in positions
    ):
        return None
    money = _plain_number(farm.get("money"))
    if money is None:
        return None
    tiles = farm.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        return None
    if not all(isinstance(row, list) for row in tiles):
        return None
    if not isinstance(private, dict):
        return None
    shed = private.get("shed")
    inventories = private.get("inventories")
    if not isinstance(shed, dict) or not isinstance(inventories, list) or len(inventories) != len(positions):
        return None
    clean_shed: dict[str, int] = {}
    for item, qty in shed.items():
        if not isinstance(item, str):
            return None
        q = _plain_nonnegative_int(qty)
        if q is None:
            return None
        clean_shed[item] = q
    clean_inventories: list[dict[str, int]] = []
    for inventory in inventories:
        if not isinstance(inventory, dict):
            return None
        clean: dict[str, int] = {}
        for item, qty in inventory.items():
            if not isinstance(item, str):
                return None
            q = _plain_nonnegative_int(qty)
            if q is None:
                return None
            clean[item] = q
        clean_inventories.append(clean)
    if not isinstance(market, dict) or not isinstance(market.get("prices"), dict):
        return None
    wheat_price = _plain_number(market["prices"].get("WHEAT"))
    if wheat_price is None:
        return None
    return {
        "player": player,
        "positions": positions,
        "money": money,
        "tiles": tiles,
        "shed": clean_shed,
        "inventories": clean_inventories,
        "wheat_price": wheat_price,
    }


def _beside_shed(position: list[int] | tuple[int, int], tiles: list[list[Any]]) -> bool:
    center = len(tiles) // 2
    return position[0] in (center - 1, center) and position[1] in (center - 1, center)


def _project_shed(
    selected_commands: list[list[Any]],
    view: Mapping[str, Any],
) -> dict[str, int] | None:
    """Faithful V216 donor projection: nearby PICKUP/DROP/PLACE, ordered capacity."""
    stock = dict(view["shed"])
    total = sum(stock.values())
    if total < 0:
        return None
    for worker, command in enumerate(selected_commands):
        if worker >= len(view["positions"]) or not _beside_shed(view["positions"][worker], view["tiles"]):
            continue
        inventory = view["inventories"][worker]
        operation = command[0]
        if operation == "PICKUP" and len(command) >= 2 and command[1] in stock:
            raw_qty = command[2] if len(command) >= 3 else 1
            qty = _plain_nonnegative_int(raw_qty)
            if qty is None:
                return None
            taken = min(stock[command[1]], qty)
            stock[command[1]] -= taken
            total -= taken
        elif operation == "DROP":
            for item, held in inventory.items():
                added = min(held, max(0, SHED_CAPACITY - total))
                if added > 0:
                    stock[item] = stock.get(item, 0) + added
                    total += added
        elif operation == "PLACE" and len(command) >= 2 and command[1] not in ANIMALS:
            item = command[1]
            raw_qty = command[2] if len(command) >= 3 else 1
            qty = _plain_nonnegative_int(raw_qty)
            if qty is None:
                return None
            added = min(qty, inventory.get(item, 0), max(0, SHED_CAPACITY - total))
            if added > 0:
                stock[item] = stock.get(item, 0) + added
                total += added
    return stock


def _authored_row24(route_window: Any) -> dict[str, Any] | None:
    """Consume the landed immutable route-window envelope without importing it."""
    if getattr(route_window, "schema", None) != ROUTE_WITNESS_SCHEMA:
        return None
    if getattr(route_window, "route_source", None) != ROUTE_WITNESS_SOURCE:
        return None
    if getattr(route_window, "current_step", None) != STEP:
        return None
    if getattr(route_window, "current_index", STEP) != STEP:
        return None
    route_id = getattr(route_window, "route_id", None)
    if type(route_id) is not str or not route_id:
        return None
    rows = getattr(route_window, "rows", None)
    if not isinstance(rows, tuple) or not rows:
        return None
    row = rows[0]
    if getattr(row, "step", None) != AUTHORED_STEP:
        return None
    action_method = getattr(row, "action", None)
    if not callable(action_method):
        return None
    try:
        authored = action_method()
    except (TypeError, ValueError, KeyError):
        return None
    if not isinstance(authored, dict) or not isinstance(authored.get("market"), list):
        return None
    return authored


def _hire_count(authored: Mapping[str, Any]) -> int | None:
    market = authored.get("market")
    if not isinstance(market, list):
        return None
    hires = 0
    for order in market:
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            return None
        if order[0] == "HIRE":
            hires += 1
    return hires if 1 <= hires <= len(HIRE_FIB) else None


def _multiplier(configuration: Any) -> float | int | None:
    if configuration is None:
        return 1
    if not isinstance(configuration, dict):
        return None
    value = configuration.get("farmHandCostMult", 1)
    number = _plain_number(value)
    if number is None or number < 0:
        return None
    return number


def transform_with_report(
    selected_action: Any,
    observation: Any,
    route_window: Any,
    configuration: Any = None,
) -> tuple[Any, dict[str, Any]]:
    """Apply V216 to one already-selected current action, fail-closed to identity."""
    base = _identity(selected_action)
    report: dict[str, Any] = {
        "schema": "titan-v5-v216-day1-hire-reserve/v1",
        "engaged": False,
        "reason": "identity",
        "donor_commit": DONOR_COMMIT,
        "donor_git_blob": DONOR_GIT_BLOB,
        "route_witness_git_blob": ROUTE_WITNESS_GIT_BLOB,
    }
    selected = _selected_shape(selected_action)
    if selected is None:
        report["reason"] = "malformed_selected_action"
        return base, report
    commands, market = selected
    if market:
        report["reason"] = "selected_market_nonempty"
        return base, report
    view = _observation_view(observation)
    if view is None:
        report["reason"] = "observation_or_step"
        return base, report
    if len(commands) != len(view["positions"]):
        report["reason"] = "worker_cardinality"
        return base, report
    authored = _authored_row24(route_window)
    if authored is None:
        report["reason"] = "route_witness"
        return base, report
    hires = _hire_count(authored)
    if hires is None:
        report["reason"] = "authored_hire_count"
        return base, report
    mult = _multiplier(configuration)
    if mult is None:
        report["reason"] = "farm_hand_cost_multiplier"
        return base, report
    required = sum(HIRE_FIB[:hires]) * mult
    money = view["money"]
    report.update({"hires": hires, "required_cash": required, "money": money})
    if not (0 <= money < required):
        report["reason"] = "cash_not_short"
        return base, report
    projected = _project_shed(commands, view)
    if projected is None:
        report["reason"] = "projected_shed"
        return base, report
    projected_wheat = projected.get("WHEAT", 0)
    wheat_price = view["wheat_price"]
    deficit = required - money
    report.update({
        "projected_wheat": projected_wheat,
        "wheat_price": wheat_price,
        "deficit": deficit,
    })
    if projected_wheat < 3:
        report["reason"] = "preserve_two_wheat"
        return base, report
    if wheat_price < deficit:
        report["reason"] = "single_sale_cannot_fund"
        return base, report
    out = _identity(selected_action)
    out["market"] = [["SELL", "WHEAT", 1]]
    report["engaged"] = True
    report["reason"] = "fund_committed_day1_hires"
    return out, report


def transform(
    selected_action: Any,
    observation: Any,
    route_window: Any,
    configuration: Any = None,
) -> Any:
    """Action-only convenience surface for current composition."""
    return transform_with_report(selected_action, observation, route_window, configuration)[0]
