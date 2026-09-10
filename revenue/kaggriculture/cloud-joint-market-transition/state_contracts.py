# SPDX-License-Identifier: Apache-2.0
"""Internal support for the exact TITAN joint transition oracle."""
from __future__ import annotations

import math
from typing import Any, Mapping

from engine_binding import _copy


def _validate_json_tree(value: Any, path: str = "$", *, depth: int = 0) -> None:
    if depth > 64:
        raise ValueError(f"state_too_deep:{path}")
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"nonfinite_value:{path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_tree(item, f"{path}/{index}", depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non_string_key:{path}")
            _validate_json_tree(item, f"{path}/{key}", depth=depth + 1)
        return
    raise ValueError(f"non_json_state_type:{path}:{type(value).__name__}")


def _require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise ValueError(f"{name}_must_be_int")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name}_below_minimum")
    return value


def _validate_party(farm: Mapping[str, Any], private: Mapping[str, Any], label: str) -> None:
    if not isinstance(farm, dict) or not isinstance(private, dict):
        raise ValueError(f"{label}_party_must_be_dicts")
    for key in ("money", "tiles", "farmer", "hands", "unlocked_quadrants", "hires_today"):
        if key not in farm:
            raise ValueError(f"{label}_missing_farm_{key}")
    if isinstance(farm["money"], bool) or not isinstance(farm["money"], (int, float)):
        raise ValueError(f"{label}_invalid_money")
    if not math.isfinite(float(farm["money"])):
        raise ValueError(f"{label}_nonfinite_money")
    _require_int(farm["hires_today"], f"{label}_hires_today", minimum=0)
    if not all(isinstance(farm[key], list) for key in ("tiles", "farmer", "hands", "unlocked_quadrants")):
        raise ValueError(f"{label}_invalid_farm_lists")
    if len(farm["farmer"]) != 2 or any(type(x) is not int for x in farm["farmer"]):
        raise ValueError(f"{label}_invalid_farmer_position")
    if not isinstance(private.get("shed"), dict) or not isinstance(private.get("seeds"), dict):
        raise ValueError(f"{label}_missing_stock_maps")
    if not isinstance(private.get("inventories"), list):
        raise ValueError(f"{label}_missing_inventories")
    if len(private["inventories"]) != 1 + len(farm["hands"]):
        raise ValueError(f"{label}_worker_inventory_count_mismatch")
    for stock_name in ("shed", "seeds"):
        for item, quantity in private[stock_name].items():
            if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
                raise ValueError(f"{label}_invalid_{stock_name}_quantity")
    for inventory in private["inventories"]:
        if not isinstance(inventory, dict):
            raise ValueError(f"{label}_invalid_inventory")
        for item, quantity in inventory.items():
            if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
                raise ValueError(f"{label}_invalid_carried_quantity")


def _validate_market(mechanics: Any, market: Mapping[str, Any]) -> None:
    if not isinstance(market, dict):
        raise ValueError("market_must_be_dict")
    inventory = market.get("inventory")
    prices = market.get("prices")
    if not isinstance(inventory, dict) or not isinstance(prices, dict):
        raise ValueError("market_inventory_and_prices_required")
    for item in mechanics.PRODUCTS:
        if item not in inventory or item not in prices:
            raise ValueError(f"market_missing_{item}")
        if type(inventory[item]) is not int:
            raise ValueError(f"market_inventory_{item}_must_be_int")
        if isinstance(prices[item], bool) or not isinstance(prices[item], (int, float)):
            raise ValueError(f"market_price_{item}_must_be_numeric")
        if not math.isfinite(float(prices[item])):
            raise ValueError(f"market_price_{item}_nonfinite")
        if inventory[item] < 0:
            raise ValueError(f"market_inventory_{item}_negative")
    if "params" in market and not isinstance(market["params"], dict):
        raise ValueError("market_params_must_be_dict")
    params = market.get("params")
    for item in mechanics.PRODUCTS:
        expected = mechanics.market_price(item, inventory[item], params)
        if prices[item] != expected:
            raise ValueError(f"market_price_state_mismatch:{item}:{prices[item]}!={expected}")


def _validate_town(mechanics: Any, town: Mapping[str, Any]) -> None:
    if not isinstance(town, dict) or not isinstance(town.get("unlocked_shops"), list):
        raise ValueError("town_unlocked_shops_required")
    if len(town["unlocked_shops"]) > mechanics.MAX_SHOP_INSTANCES:
        raise ValueError("too_many_town_shop_instances")
    for shop in town["unlocked_shops"]:
        if not isinstance(shop, str) or shop not in mechanics.SHOPS:
            raise ValueError(f"unknown_town_shop:{shop!r}")


def _validated_config(configuration: Mapping[str, Any]) -> dict[str, int]:
    if not isinstance(configuration, dict):
        raise ValueError("configuration_must_be_dict")
    values = {
        "boardSize": configuration.get("boardSize", 10),
        "maxMarketOrdersPerTurn": configuration.get("maxMarketOrdersPerTurn", 10),
        "farmHandCostMult": configuration.get("farmHandCostMult", 1),
        "shedCapacity": configuration.get("shedCapacity", 100),
        "townShopSellInterval": configuration.get("townShopSellInterval", 4),
        "townCenterSellInterval": configuration.get("townCenterSellInterval", 24),
    }
    _require_int(values["boardSize"], "boardSize", minimum=2)
    _require_int(values["maxMarketOrdersPerTurn"], "maxMarketOrdersPerTurn")
    _require_int(values["farmHandCostMult"], "farmHandCostMult", minimum=0)
    _require_int(values["shedCapacity"], "shedCapacity", minimum=0)
    _require_int(values["townShopSellInterval"], "townShopSellInterval")
    _require_int(values["townCenterSellInterval"], "townCenterSellInterval")
    return values


def _validate_party_against_config(
    mechanics: Any, farm: Mapping[str, Any], private: Mapping[str, Any],
    configuration: Mapping[str, int], label: str,
) -> None:
    board_size = configuration["boardSize"]
    tiles = farm["tiles"]
    if len(tiles) != board_size or any(not isinstance(row, list) or len(row) != board_size for row in tiles):
        raise ValueError(f"{label}_board_shape_mismatch")
    if farm["hires_today"] != len(farm["hands"]):
        raise ValueError(f"{label}_hire_hand_count_mismatch")
    positions = [farm["farmer"], *farm["hands"]]
    for position in positions:
        if (not isinstance(position, list) or len(position) != 2 or
                any(type(coordinate) is not int or coordinate < 0 or coordinate >= board_size for coordinate in position)):
            raise ValueError(f"{label}_invalid_worker_position")
    expected_quadrants = ["NW", *mechanics.LAND_ORDER[:max(0, len(farm["unlocked_quadrants"]) - 1)]]
    if farm["unlocked_quadrants"] != expected_quadrants:
        raise ValueError(f"{label}_invalid_unlocked_quadrants")
    if sum(private["shed"].values()) > configuration["shedCapacity"]:
        raise ValueError(f"{label}_shed_over_capacity")


def _without_market(action: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _copy(value) for key, value in action.items() if key != "market"}


def _unit_fields(action: Mapping[str, Any]) -> tuple[Any, Any]:
    return action.get("farmer", ["PASS"]), action.get("hands", [])


def _validate_action(action: Any, label: str) -> None:
    if not isinstance(action, dict):
        raise ValueError(f"{label}_action_must_be_dict")
    if "market" in action and not isinstance(action["market"], list):
        raise ValueError(f"{label}_market_must_be_list")
    if "hands" in action and not isinstance(action["hands"], list):
        raise ValueError(f"{label}_hands_must_be_list")
    if "farmer" in action and not isinstance(action["farmer"], list):
        raise ValueError(f"{label}_farmer_must_be_list")


def _active_queue(action: Mapping[str, Any], max_orders: int) -> list[Any]:
    market = action.get("market", [])
    return _copy(market[:max_orders])
