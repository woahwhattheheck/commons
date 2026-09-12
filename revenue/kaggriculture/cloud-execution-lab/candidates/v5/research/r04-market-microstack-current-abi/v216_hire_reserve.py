# SPDX-License-Identifier: Apache-2.0
"""Submitted V3.1 V216 day-one HIRE reserve on canonical market authority.

This is the exact V216 selected-action theorem from the submitted V3.1 policy
family, collapsed into the canonical R04 market carrier. It does not accept a
caller-constructed route window. Future row 24 must come from a
``MarketRouteAuthority`` that validates against the landed receipt-bound v3
route witness for the current callback.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Mapping

from market_route_authority import MarketRouteAuthority, validate_market_route_authority

DONOR_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_full_router.py"
DONOR_GIT_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"
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


def _authored_row24(
    route_authority: MarketRouteAuthority | None,
    observation: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    validated = validate_market_route_authority(
        route_authority,
        observation,
        required_end_step=AUTHORED_STEP,
    )
    if validated is None:
        return None
    actions, receipt = validated
    authored = actions.get(AUTHORED_STEP)
    if not isinstance(authored, dict) or not isinstance(authored.get("market"), list):
        return None
    return authored, receipt


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
    route_authority: MarketRouteAuthority | None,
    configuration: Any = None,
) -> tuple[Any, dict[str, Any]]:
    """Apply V216 to one selected action; fail closed unless authority is canonical."""
    base = _identity(selected_action)
    report: dict[str, Any] = {
        "schema": "titan-v5-v216-day1-hire-reserve/v2",
        "engaged": False,
        "reason": "identity",
        "donor_commit": DONOR_COMMIT,
        "donor_git_blob": DONOR_GIT_BLOB,
        "authorizing": False,
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
    bound = _authored_row24(route_authority, observation)
    if bound is None:
        report["reason"] = "canonical_route_authority_required"
        return base, report
    authored, route_receipt = bound
    report.update(
        {
            "authorizing": True,
            "route_authority_sha256": route_receipt.get("authority_sha256"),
            "route_sha256": route_receipt.get("window", {}).get("route_sha256"),
            "window_sha256": route_receipt.get("window", {}).get("window_sha256"),
        }
    )
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
    report.update(
        {
            "projected_wheat": projected_wheat,
            "wheat_price": wheat_price,
            "deficit": deficit,
        }
    )
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
    route_authority: MarketRouteAuthority | None,
    configuration: Any = None,
) -> Any:
    """Action-only convenience surface for one-V5 composition."""
    return transform_with_report(
        selected_action,
        observation,
        route_authority,
        configuration,
    )[0]
