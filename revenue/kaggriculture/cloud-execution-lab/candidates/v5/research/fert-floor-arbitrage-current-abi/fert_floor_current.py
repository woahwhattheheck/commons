# SPDX-License-Identifier: Apache-2.0
"""Current-V5 evidence adapter for floor-price fertilizer acquisition/application.

This is a fresh re-author from durable source mechanics, not a reconstruction of
the lost ``r04_fert_arbitrage`` payload. It has no producer/controller calls and
is default-disconnected. The only policy choices represented here are:

* append one BUY_PRODUCT FERTILIZER order when the *public current quote* is
  exactly 2, one market slot and cash are available, no owned fertilizer already
  exists, and the board contains an uncovered live plant opportunity;
* replace only a literal PASS of an actor already carrying fertilizer while
  standing on such a plant with FERTILIZE.

The adapter intentionally never invents PICKUP routing. Natural current-V5
engagement must prove shed -> actor custody before economics can promote this.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping

ITEM = "FERTILIZER"
STRICT_BUY_PRICE = 2
MAX_MARKET_ORDERS = 10
TURNS_PER_DAY = 24
EPISODE_STEPS = 720

MECHANISM_SOURCE_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/"
    "fwd-buy-census/fert_floor_apply.py"
)
MECHANISM_SOURCE_BLOB = "a32160a2298e9d92a824b52bc272535583a85a67"
MECHANISM_PR = 13057
MECHANISM_FOLLOWUP = "d8fa49ccbedf2a51c65431bae51a7f99e648da20"


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and (
        type(value) is int or math.isfinite(value)
    )


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _identity(selected: Any, reason: str, **extra: Any):
    report = {
        "changed": False,
        "reason": reason,
        "buy_added": False,
        "fertilize_actor_indices": (),
        "strict_buy_price": STRICT_BUY_PRICE,
        "mechanism_source_blob": MECHANISM_SOURCE_BLOB,
    }
    report.update(extra)
    return selected, report


def _configuration(configuration: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if configuration is None:
        return {
            "maxMarketOrdersPerTurn": MAX_MARKET_ORDERS,
            "turnsPerDay": TURNS_PER_DAY,
            "episodeSteps": EPISODE_STEPS,
        }
    if not isinstance(configuration, Mapping):
        return None
    cfg = dict(configuration)
    expected = {
        "maxMarketOrdersPerTurn": MAX_MARKET_ORDERS,
        "turnsPerDay": TURNS_PER_DAY,
        "episodeSteps": EPISODE_STEPS,
    }
    for key, default in expected.items():
        value = cfg.get(key, default)
        if type(value) is not int or value != default:
            return None
    return cfg


def _eligible_plant(tile: Any, day: int) -> bool:
    if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
        return False
    crop = tile.get("crop")
    covered = tile.get("fertilized_until_day", -1)
    if type(crop) is not str or not crop:
        return False
    if type(covered) is not int:
        return False
    if tile.get("dead") is True:
        return False
    # Official FERTILIZE covers the current day plus the next two days.
    return covered < day + 2


def _board_has_opportunity(tiles: Any, day: int) -> bool:
    return (
        isinstance(tiles, list)
        and bool(tiles)
        and all(isinstance(row, list) for row in tiles)
        and any(_eligible_plant(tile, day) for row in tiles for tile in row)
    )


def _actor_tile(tiles: list[list[Any]], position: Any) -> Any:
    if (
        not isinstance(position, list)
        or len(position) != 2
        or any(type(value) is not int for value in position)
    ):
        return None
    x, y = position
    if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
        return None
    return tiles[y][x]


def _fert_qty(inventory: Any) -> int | None:
    if not isinstance(inventory, Mapping):
        return None
    value = inventory.get(ITEM, 0)
    if not _nonnegative_int(value):
        return None
    return value


def _parse(observation: Any, selected: Any, configuration: Mapping[str, Any] | None):
    cfg = _configuration(configuration)
    if cfg is None or not isinstance(observation, Mapping) or not isinstance(selected, Mapping):
        return None, "malformed_envelope"
    player = observation.get("player")
    step = observation.get("step")
    farms = observation.get("farms")
    private = observation.get("private")
    market_state = observation.get("market")
    if (
        type(player) is not int
        or player not in (0, 1)
        or type(step) is not int
        or not 0 <= step < EPISODE_STEPS
        or not isinstance(farms, list)
        or player >= len(farms)
        or not isinstance(private, Mapping)
        or not isinstance(market_state, Mapping)
    ):
        return None, "malformed_observation"
    farm = farms[player]
    if not isinstance(farm, Mapping):
        return None, "malformed_farm"
    farmer = farm.get("farmer")
    hands = farm.get("hands")
    tiles = farm.get("tiles")
    money = farm.get("money")
    inventories = private.get("inventories")
    shed = private.get("shed")
    prices = market_state.get("prices")
    if (
        not isinstance(farmer, list)
        or not isinstance(hands, list)
        or not isinstance(tiles, list)
        or not isinstance(inventories, list)
        or len(inventories) != len(hands) + 1
        or not isinstance(shed, Mapping)
        or not isinstance(prices, Mapping)
        or not _finite_number(money)
        or money < 0
    ):
        return None, "malformed_farm_state"
    positions = [farmer, *hands]

    selected_farmer = selected.get("farmer")
    selected_hands = selected.get("hands")
    selected_market = selected.get("market")
    if (
        not isinstance(selected_farmer, list)
        or not selected_farmer
        or not isinstance(selected_hands, list)
        or len(selected_hands) != len(hands)
        or not isinstance(selected_market, list)
        or len(selected_market) > MAX_MARKET_ORDERS
        or any(not isinstance(command, list) or not command for command in [selected_farmer, *selected_hands])
        or any(not isinstance(order, list) or not order for order in selected_market)
    ):
        return None, "selected_action_invalid"

    fert_price = prices.get(ITEM)
    if not _finite_number(fert_price) or fert_price < 0:
        return None, "malformed_fertilizer_price"

    shed_fert = _fert_qty(shed)
    actor_fert = [_fert_qty(inventory) for inventory in inventories]
    if shed_fert is None or any(value is None for value in actor_fert):
        return None, "malformed_fertilizer_inventory"

    return {
        "cfg": cfg,
        "player": player,
        "step": step,
        "day": step // TURNS_PER_DAY,
        "farm": farm,
        "positions": positions,
        "tiles": tiles,
        "money": float(money),
        "inventories": inventories,
        "shed_fert": shed_fert,
        "actor_fert": actor_fert,
        "fert_price": float(fert_price),
        "selected_market": selected_market,
    }, None


def _market_mentions_fertilizer(market: list[list[Any]]) -> bool:
    for order in market:
        # Known BUY_PRODUCT/SELL rows name the item at index 1. Unknown short
        # rows are preserved and do not grant candidate authority.
        if len(order) >= 2 and order[1] == ITEM:
            return True
    return False


class FertFloorArbitrageCurrentABI:
    """Default-disconnected selected-action research adapter."""

    def __init__(self, *, buy: bool = True, apply: bool = True):
        if type(buy) is not bool or type(apply) is not bool:
            raise TypeError("buy and apply must be exact bool")
        self.buy = buy
        self.apply = apply

    def transform(
        self,
        observation: Any,
        selected: Any,
        configuration: Mapping[str, Any] | None = None,
    ):
        parsed, error = _parse(observation, selected, configuration)
        if parsed is None:
            return _identity(
                selected,
                error or "malformed_envelope",
                buy_enabled=self.buy,
                apply_enabled=self.apply,
            )

        action = deepcopy(selected)
        commands = [action["farmer"], *action["hands"]]
        fertilized: list[int] = []

        if self.apply:
            for index, (position, inventory) in enumerate(
                zip(parsed["positions"], parsed["inventories"])
            ):
                command = commands[index]
                qty = _fert_qty(inventory)
                tile = _actor_tile(parsed["tiles"], position)
                if (
                    command == ["PASS"]
                    and qty is not None
                    and qty > 0
                    and _eligible_plant(tile, parsed["day"])
                ):
                    commands[index] = ["FERTILIZE"]
                    fertilized.append(index)

        action["farmer"] = commands[0]
        action["hands"] = commands[1:]

        buy_added = False
        if self.buy:
            owned_fert = parsed["shed_fert"] + sum(parsed["actor_fert"])
            can_buy = (
                parsed["fert_price"] == STRICT_BUY_PRICE
                and parsed["money"] >= STRICT_BUY_PRICE
                and owned_fert == 0
                and len(action["market"]) < MAX_MARKET_ORDERS
                and not _market_mentions_fertilizer(action["market"])
                and _board_has_opportunity(parsed["tiles"], parsed["day"])
            )
            if can_buy:
                action["market"].append(["BUY_PRODUCT", ITEM, 1])
                buy_added = True

        changed = action != selected
        if not changed:
            reason = "identity"
            if self.buy and parsed["fert_price"] != STRICT_BUY_PRICE:
                reason = "fertilizer_price_not_strict_floor_entry"
            elif self.buy and parsed["shed_fert"] + sum(parsed["actor_fert"]) > 0:
                reason = "owned_fertilizer_already_present"
            elif self.buy and _market_mentions_fertilizer(parsed["selected_market"]):
                reason = "parent_fertilizer_market_intent"
            elif self.buy and len(parsed["selected_market"]) >= MAX_MARKET_ORDERS:
                reason = "market_capacity_full"
            elif self.buy and not _board_has_opportunity(parsed["tiles"], parsed["day"]):
                reason = "no_live_fertilizer_opportunity"
            return _identity(
                selected,
                reason,
                buy_enabled=self.buy,
                apply_enabled=self.apply,
                observed_fertilizer_price=parsed["fert_price"],
            )

        return action, {
            "changed": True,
            "reason": "fert_floor_arbitrage_current_transform",
            "buy_enabled": self.buy,
            "apply_enabled": self.apply,
            "buy_added": buy_added,
            "fertilize_actor_indices": tuple(fertilized),
            "strict_buy_price": STRICT_BUY_PRICE,
            "observed_fertilizer_price": parsed["fert_price"],
            "mechanism_source_blob": MECHANISM_SOURCE_BLOB,
        }
