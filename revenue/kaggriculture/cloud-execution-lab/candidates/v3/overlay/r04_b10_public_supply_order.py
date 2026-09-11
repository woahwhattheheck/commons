# SPDX-License-Identifier: Apache-2.0
"""V4 B10: public rival-supply SELL ordering.

B10 uses only public market/town observations plus our own previously returned
action. Evidence is accepted only inside a valid step-0-anchored contiguous
epoch. Any malformed callback, missing configuration, gap, repeat, or rewind
drops that player's latch and cannot re-seed it mid-episode.

Only the seven products that cannot be BUY_PRODUCT'ed are eligible to move.
WHEAT and FERTILIZER remain pinned at their exact incoming row indices. This
keeps B10's authorization theorem on a public-state surface we can prove from
the official engine without reconstructing hidden buy/sell cycles.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
NONBUYABLE_PRODUCTS = (
    "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL",
)
PINNED_PRODUCTS = frozenset(("WHEAT", "FERTILIZER"))
WHEAT = "WHEAT"
STANDARD_MARKET_I0 = 10_000
STANDARD_SHED_CAPACITY = 100
STANDARD_MAX_ORDERS = 10
STANDARD_EPISODE_STEPS = 720
LAST_AGENT_STEP = STANDARD_EPISODE_STEPS - 2
MAX_UNLOCKED_SHOPS = 8
BUY_OPS = {"HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"}

# First standard-market inventory at which a SELL quotes $1 and therefore
# stops incrementing public inventory. EGG's standard curve never reaches the
# $1 floor in the reachable B10 horizon, so its room is bounded by shed mass.
NONBUYABLE_FLOOR_INVENTORY = {
    "CARROT": 10_842,
    "TOMATO": 10_529,
    "STRAWBERRY": 10_062,
    "MELON": 10_158,
    "MILK": 10_076,
    "WOOL": 10_059,
}

SHOPS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
CENTER_PRODUCTS = tuple(item for item in PRODUCTS if item != "FERTILIZER")


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _strict_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError("%s must be a JSON integer" % label)
    return value


def _positive_int(value: Any, label: str) -> int:
    number = _strict_int(value, label)
    if number <= 0:
        raise ValueError("%s must be positive" % label)
    return number


def _step_player(observation: Mapping[str, Any]) -> tuple[int, int]:
    step = _strict_int(_get(observation, "step", None), "step")
    player = _strict_int(_get(observation, "player", None), "player")
    if step < 0 or step > LAST_AGENT_STEP or player not in (0, 1):
        raise ValueError("invalid or engine-unreachable step/player")
    return step, player


def _require_standard_market_cap(configuration: Any = None) -> tuple[int, int]:
    if configuration is None:
        raise ValueError("installed runtime configuration is required")

    episode_steps = _strict_int(
        _get(configuration, "episodeSteps", STANDARD_EPISODE_STEPS),
        "episodeSteps",
    )
    if episode_steps != STANDARD_EPISODE_STEPS:
        raise ValueError("B10 supports only standard episodeSteps=720")

    cap = _strict_int(
        _get(configuration, "maxMarketOrdersPerTurn", STANDARD_MAX_ORDERS),
        "maxMarketOrdersPerTurn",
    )
    if cap != STANDARD_MAX_ORDERS:
        raise ValueError("B10 supports only standard maxMarketOrdersPerTurn=10")

    shed_capacity = _positive_int(
        _get(configuration, "shedCapacity", STANDARD_SHED_CAPACITY),
        "shedCapacity",
    )
    if shed_capacity != STANDARD_SHED_CAPACITY:
        raise ValueError("B10 supports only standard shedCapacity=100")
    return cap, shed_capacity


def _inventory(observation: Mapping[str, Any]) -> dict[str, int]:
    market = _get(observation, "market", None)
    raw = _get(market, "inventory", None)
    if not isinstance(raw, Mapping):
        raise ValueError("market.inventory must be a mapping")
    return {
        item: _strict_int(raw[item], "market.inventory.%s" % item)
        for item in PRODUCTS
    }


def _interval(configuration: Any, key: str, default: int) -> int:
    value = _get(configuration, key, default) if configuration is not None else default
    return _positive_int(value, key)


def _shop_vector(observation: Mapping[str, Any]) -> tuple[str, ...]:
    town = _get(observation, "town", None)
    shops = _get(town, "unlocked_shops", None)
    if not isinstance(shops, list):
        raise ValueError("town.unlocked_shops must be a list")
    if len(shops) > MAX_UNLOCKED_SHOPS:
        raise ValueError("town.unlocked_shops exceeds engine maximum")
    for shop in shops:
        if type(shop) is not str or shop not in SHOPS:
            raise ValueError("unknown shop %r" % (shop,))
    return tuple(shops)


def _expected_shop_count(step: int, configuration: Any = None) -> int:
    turns_per_day = _interval(configuration, "turnsPerDay", 24)
    unlock_interval = _interval(configuration, "townShopUnlockInterval", 3)
    day = step // turns_per_day
    return min(MAX_UNLOCKED_SHOPS, day // unlock_interval)


def _validate_shop_snapshot(step: int, shops: Sequence[str],
                            configuration: Any = None) -> None:
    if len(shops) != _expected_shop_count(step, configuration):
        raise ValueError("town shop count is unreachable at this callback step")


def _validate_shop_transition(previous_step: int, current_step: int,
                              previous_shops: Sequence[str],
                              current_shops: Sequence[str]) -> None:
    if current_step != previous_step + 1:
        raise ValueError("shop transition requires consecutive callbacks")
    previous = tuple(previous_shops)
    current = tuple(current_shops)
    if current[:len(previous)] != previous:
        raise ValueError("town shop history must preserve the exact prior prefix")


def _town_consumption(observation: Mapping[str, Any],
                      configuration: Any = None) -> dict[str, int]:
    step, _ = _step_player(observation)
    shop_interval = _interval(configuration, "townShopSellInterval", 4)
    center_interval = _interval(configuration, "townCenterSellInterval", 24)
    shops = _shop_vector(observation)

    consume = {item: 0 for item in PRODUCTS}
    if step % shop_interval == 0:
        for shop in shops:
            products = SHOPS[shop]
            multiplier = 2 if len(products) == 1 else 1
            for item in products:
                consume[item] += multiplier
    if step % center_interval == 0:
        for item in CENTER_PRODUCTS:
            consume[item] += 1
    return consume


def _market_rows(action: Mapping[str, Any]) -> list[Any]:
    rows = _get(action, "market", None)
    if not isinstance(rows, list):
        raise ValueError("action.market must be a list")
    if len(rows) > STANDARD_MAX_ORDERS:
        raise ValueError("parent market exceeds standard executable prefix")
    return rows


def _own_sell_upper(action: Mapping[str, Any]) -> dict[str, int]:
    """Requested SELL upper bound using only rows the engine can execute."""
    upper = {item: 0 for item in PRODUCTS}
    for order in _market_rows(action):
        # Official _parse_order requires a list. Tuple-shaped lookalikes are
        # market no-ops and must not mask the rival-supply lower bound.
        if not isinstance(order, list) or not order:
            continue
        if order[0] != "SELL":
            continue
        if len(order) < 3 or order[1] not in upper:
            raise ValueError("malformed own SELL")
        upper[order[1]] += _positive_int(order[2], "own SELL quantity")
    return upper


def _gross_market_delta(previous_inventory: Mapping[str, int],
                        current_inventory: Mapping[str, int],
                        previous_town_consume: Mapping[str, int]) -> dict[str, int]:
    return {
        item: (
            int(current_inventory[item])
            - int(previous_inventory[item])
            + int(previous_town_consume[item])
        )
        for item in PRODUCTS
    }


def _rival_supply_lower_bound(previous_inventory: Mapping[str, int],
                              current_inventory: Mapping[str, int],
                              previous_town_consume: Mapping[str, int],
                              previous_own_sell_upper: Mapping[str, int]) -> dict[str, int]:
    gross = _gross_market_delta(
        previous_inventory, current_inventory, previous_town_consume
    )
    return {
        item: gross[item] - int(previous_own_sell_upper[item])
        for item in PRODUCTS
    }


def _max_visible_nonbuyable_supply(item: str, start_inventory: int,
                                   shed_capacity: int) -> int:
    """Max public +inventory reachable before the standard $1 SELL floor."""
    if item not in NONBUYABLE_PRODUCTS:
        raise ValueError("visible-supply floor applies only to non-buyables")
    ceiling = 2 * shed_capacity
    floor_inventory = NONBUYABLE_FLOOR_INVENTORY.get(item)
    if floor_inventory is None:
        return ceiling
    return max(0, min(ceiling, floor_inventory - int(start_inventory)))


def _transition_evidence(previous: Mapping[str, Any],
                         current_inventory: Mapping[str, int],
                         shed_capacity: int) -> dict[str, int]:
    """Validate one consecutive edge and return certifiable rival lower bounds."""
    gross = _gross_market_delta(
        previous["inventory"], current_inventory, previous["town_consume"]
    )

    for item in NONBUYABLE_PRODUCTS:
        value = gross[item]
        if value < 0:
            raise ValueError("non-buyable public inventory over-drop")
        room = _max_visible_nonbuyable_supply(
            item, previous["inventory"][item], shed_capacity
        )
        if value > room:
            raise ValueError("non-buyable public supply exceeds standard price-floor room")

    # Only the non-buyable domain is authorized to move. Across those products,
    # both players can expose at most their two starting sheds of positive mass.
    if sum(gross[item] for item in NONBUYABLE_PRODUCTS) > 2 * shed_capacity:
        raise ValueError("non-buyable positive public net exceeds two-shed capacity")

    lower = {
        item: gross[item] - int(previous["own_sell_upper"][item])
        for item in PRODUCTS
    }
    if sum(max(0, lower[item]) for item in NONBUYABLE_PRODUCTS) > shed_capacity:
        raise ValueError("proved rival non-buyable net exceeds one-shed capacity")

    # Buyable-product history is intentionally outside B10's authorization
    # theorem. Keep it from influencing telemetry or ordering.
    for item in PINNED_PRODUCTS:
        lower[item] = 0
    return lower


def _cash_spending(order: Any) -> bool:
    return isinstance(order, (list, tuple)) and bool(order) and order[0] in BUY_OPS


def _leading_sell_count(rows: Sequence[Any]) -> int:
    lead = 0
    while lead < len(rows):
        order = rows[lead]
        if not isinstance(order, list) or not order or order[0] != "SELL":
            break
        lead += 1
    return lead


def _reorder_leading_sells(action: Mapping[str, Any],
                           evidence: Mapping[str, int]) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    rows = _market_rows(action)
    lead = _leading_sell_count(rows)
    if lead < 2:
        return action, None
    if any(_cash_spending(order) for order in rows[lead:]):
        return action, None

    movable_indices = []
    movable_rows = []
    for index in range(lead):
        order = rows[index]
        if len(order) < 3 or order[1] not in PRODUCTS:
            return action, None
        _positive_int(order[2], "leading SELL quantity")
        if order[1] in PINNED_PRODUCTS:
            continue
        movable_indices.append(index)
        movable_rows.append(list(order))
    if len(movable_rows) < 2:
        return action, None

    positive = {item: max(0, int(evidence.get(item, 0))) for item in PRODUCTS}
    if not any(positive[row[1]] > 0 for row in movable_rows):
        return action, None

    ordered = sorted(movable_rows, key=lambda row: -positive[row[1]])
    if ordered == movable_rows:
        return action, None

    result = copy.deepcopy(action)
    for index, order in zip(movable_indices, ordered):
        result["market"][index] = order
    return result, {
        "leading_sell_rows": lead,
        "movable_indices": movable_indices,
        "before": [row[1] for row in movable_rows],
        "after": [row[1] for row in ordered],
        "evidence": {row[1]: positive[row[1]] for row in movable_rows},
    }


class RivalSupplyOrder:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
        self.players: dict[int, dict[str, Any]] = {}
        self.telemetry = {
            "confirmed_supply_transitions": 0,
            "reorders": 0,
            "last_positive_products": [],
            "last_before": [],
            "last_after": [],
        }

    def _drop_player(self, observation: Any) -> None:
        try:
            player = _strict_int(_get(observation, "player", None), "player")
        except (KeyError, TypeError, ValueError):
            self.players.clear()
            return
        if player not in (0, 1):
            self.players.clear()
            return
        self.players.pop(player, None)

    def _current_record(self, observation: Mapping[str, Any],
                        action: Mapping[str, Any],
                        configuration: Any) -> tuple[int, dict[str, Any]]:
        step, player = _step_player(observation)
        shops = _shop_vector(observation)
        _validate_shop_snapshot(step, shops, configuration)
        inventory = _inventory(observation)
        if step == 0 and any(
            inventory[item] != STANDARD_MARKET_I0 for item in PRODUCTS
        ):
            raise ValueError("step0 market inventory must equal standard I0")
        return player, {
            "step": step,
            "inventory": inventory,
            "shops": shops,
            "town_consume": _town_consumption(observation, configuration),
            "own_sell_upper": _own_sell_upper(action),
        }

    def apply(self, observation: Mapping[str, Any],
              parent_action: Mapping[str, Any],
              configuration: Any = None) -> Mapping[str, Any]:
        if configuration is None:
            self._drop_player(observation)
            return parent_action

        try:
            _, shed_capacity = _require_standard_market_cap(configuration)
        except (KeyError, TypeError, ValueError):
            self._drop_player(observation)
            return parent_action

        custom_params = _get(configuration, "marketParams", None)
        if custom_params is not None:
            if not isinstance(custom_params, Mapping) or custom_params:
                self._drop_player(observation)
                return parent_action

        try:
            player, current_record = self._current_record(
                observation, parent_action, configuration
            )
            step = current_record["step"]

            # A valid step0 explicitly replaces stale process/module state and is
            # the only legal episode seed.
            if step == 0:
                self.players[player] = current_record
                return parent_action

            previous = self.players.get(player)
            if previous is None:
                return parent_action
            if step != previous["step"] + 1:
                self.players.pop(player, None)
                return parent_action

            _validate_shop_transition(
                previous["step"], step, previous["shops"], current_record["shops"]
            )
            evidence = _transition_evidence(
                previous, current_record["inventory"], shed_capacity
            )
        except (KeyError, TypeError, ValueError):
            self._drop_player(observation)
            return parent_action

        result = parent_action
        positives = [item for item, value in evidence.items() if value > 0]
        if positives:
            self.telemetry["confirmed_supply_transitions"] += 1
            self.telemetry["last_positive_products"] = sorted(positives)
            if self.enabled and step != LAST_AGENT_STEP:
                try:
                    candidate, detail = _reorder_leading_sells(parent_action, evidence)
                    if detail is not None:
                        result = candidate
                        self.telemetry["reorders"] += 1
                        self.telemetry["last_before"] = detail["before"]
                        self.telemetry["last_after"] = detail["after"]
                except (KeyError, TypeError, ValueError):
                    result = parent_action

        self.players[player] = current_record
        return result


ORDER = RivalSupplyOrder(enabled=True)


def invalidate_public_supply_order(observation) -> None:
    ORDER._drop_player(observation)


def apply_public_supply_order(observation, parent_action,
                              configuration=None, enabled=True):
    if not enabled:
        return parent_action
    ORDER.enabled = True
    if configuration is None:
        invalidate_public_supply_order(observation)
        return parent_action
    return ORDER.apply(observation, parent_action, configuration)
