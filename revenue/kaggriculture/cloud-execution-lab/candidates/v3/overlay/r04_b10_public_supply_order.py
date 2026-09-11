# SPDX-License-Identifier: Apache-2.0
"""V4 B10: public rival-supply SELL ordering.

This is the repaired #12487 mechanism, packaged as a V4 helper. It uses only
public market/town observations plus our own previous returned action. For a
product p between callbacks t and t+1 the official engine gives::

    delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

Because executed own SELL cannot exceed our requested SELL quantity and executed
own BUY is non-negative::

    rival_sell - rival_buy >= delta_inventory + town_consume - own_sell_requested

A positive lower bound therefore proves realized rival net supply without
reading rival orders, shed, or carried inventory.

When enabled, B10 may reorder only the parent's already-existing leading SELL
block. WHEAT stays at its exact row index (C5 owns WHEAT timing), every quantity
and non-WHEAT row is preserved, and products with stronger proved prior-step
rival net supply move earlier among the remaining non-WHEAT SELL positions.
A later cash-spending row vetoes the transform so B10 cannot perturb financing
for HIRE/BUY_* obligations. The terminal callback at step 718 is observation-
only for B10 under the standard 720-step episode: upstream B9/PLACE own the final
liquidation row semantics, so B10 records public evidence but never reorders that
callback. Nonstandard episode lengths, missing installed runtime configuration,
and engine-unreachable callback/town history fail closed and break evidence
continuity. All current public evidence is validated before mutation; malformed
or ambiguous state fails closed to the exact parent action.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
WHEAT = "WHEAT"
STANDARD_MAX_ORDERS = 10
STANDARD_EPISODE_STEPS = 720
LAST_AGENT_STEP = STANDARD_EPISODE_STEPS - 2
MAX_UNLOCKED_SHOPS = 8
BUY_OPS = {"HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"}
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
    if type(value) is not int:  # bool must not alias int in evidence logic.
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


def _require_standard_market_cap(configuration: Any = None) -> int:
    episode_value = (_get(configuration, "episodeSteps", STANDARD_EPISODE_STEPS)
                     if configuration is not None else STANDARD_EPISODE_STEPS)
    episode_steps = _strict_int(episode_value, "episodeSteps")
    if episode_steps != STANDARD_EPISODE_STEPS:
        raise ValueError("B10 supports only standard episodeSteps=720")

    value = (_get(configuration, "maxMarketOrdersPerTurn", STANDARD_MAX_ORDERS)
             if configuration is not None else STANDARD_MAX_ORDERS)
    cap = _strict_int(value, "maxMarketOrdersPerTurn")
    if cap != STANDARD_MAX_ORDERS:
        raise ValueError("B10 supports only standard maxMarketOrdersPerTurn=10")
    return cap


def _inventory(observation: Mapping[str, Any]) -> dict[str, int]:
    market = _get(observation, "market", None)
    raw = _get(market, "inventory", None)
    if not isinstance(raw, Mapping):
        raise ValueError("market.inventory must be a mapping")
    return {item: _strict_int(raw[item], "market.inventory.%s" % item)
            for item in PRODUCTS}


def _interval(configuration: Any, key: str, default: int) -> int:
    value = _get(configuration, key, default) if configuration is not None else default
    return _positive_int(value, key)


def _shop_vector(observation: Mapping[str, Any]) -> tuple[str, ...]:
    town = _get(observation, "town", None)
    shops = _get(town, "unlocked_shops", None)
    # Official observations are JSON arrays. Accepting tuple-like synthetic
    # state would weaken the fail-closed public-evidence contract.
    if not isinstance(shops, list):
        raise ValueError("town.unlocked_shops must be a list")
    if len(shops) > MAX_UNLOCKED_SHOPS:
        raise ValueError("town.unlocked_shops exceeds engine maximum")
    for shop in shops:
        if type(shop) is not str or shop not in SHOPS:
            raise ValueError("unknown shop %r" % (shop,))
    return tuple(shops)


def _expected_shop_count(step: int, configuration: Any = None) -> int:
    """Exact number of shop instances reachable in the official append-only town."""
    turns_per_day = _interval(configuration, "turnsPerDay", 24)
    unlock_interval = _interval(configuration, "townShopUnlockInterval", 3)
    day = step // turns_per_day
    return min(MAX_UNLOCKED_SHOPS, day // unlock_interval)


def _validate_shop_snapshot(step: int, shops: Sequence[str], configuration: Any = None) -> None:
    expected = _expected_shop_count(step, configuration)
    if len(shops) != expected:
        raise ValueError("town shop count is unreachable at this callback step")


def _validate_shop_transition(previous_step: int, current_step: int,
                              previous_shops: Sequence[str], current_shops: Sequence[str]) -> None:
    """Prove append-only ordered history across consecutive official callbacks."""
    if current_step != previous_step + 1:
        raise ValueError("shop transition requires consecutive callbacks")
    previous = tuple(previous_shops)
    current = tuple(current_shops)
    if current[:len(previous)] != previous:
        raise ValueError("town shop history must preserve the exact prior prefix")


def _town_consumption(observation: Mapping[str, Any], configuration: Any = None) -> dict[str, int]:
    """Exact deterministic public town demand after this callback's market phase."""
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
    upper = {item: 0 for item in PRODUCTS}
    for order in _market_rows(action):
        if not isinstance(order, (list, tuple)) or not order:
            continue
        if order[0] != "SELL":
            continue
        if len(order) < 3 or order[1] not in upper:
            raise ValueError("malformed own SELL")
        upper[order[1]] += _positive_int(order[2], "own SELL quantity")
    return upper


def _rival_supply_lower_bound(previous_inventory: Mapping[str, int],
                              current_inventory: Mapping[str, int],
                              previous_town_consume: Mapping[str, int],
                              previous_own_sell_upper: Mapping[str, int]) -> dict[str, int]:
    return {
        item: (int(current_inventory[item]) - int(previous_inventory[item])
               + int(previous_town_consume[item])
               - int(previous_own_sell_upper[item]))
        for item in PRODUCTS
    }


def _cash_spending(order: Any) -> bool:
    return isinstance(order, (list, tuple)) and bool(order) and order[0] in BUY_OPS


def _leading_sell_count(rows: Sequence[Any]) -> int:
    lead = 0
    while lead < len(rows):
        order = rows[lead]
        # The official engine parses only list orders. A tuple that merely
        # looks like SELL is a no-op timing slot and must never be activated
        # by B10's copy-on-write conversion to list.
        if not isinstance(order, list) or not order or order[0] != "SELL":
            break
        lead += 1
    return lead


def _reorder_leading_sells(action: Mapping[str, Any],
                           evidence: Mapping[str, int]) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Prioritize proved rival-supply products inside the existing leading SELL block."""
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
        if order[1] == WHEAT:
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
        # Latch invalidation must not depend on step validity: a malformed-step
        # callback breaks evidence continuity just as surely as any other bad
        # current observation. If even the player cannot be identified safely,
        # discard all latches rather than allowing stale cross-call evidence.
        try:
            player = _strict_int(_get(observation, "player", None), "player")
        except (KeyError, TypeError, ValueError):
            self.players.clear()
            return
        if player not in (0, 1):
            self.players.clear()
            return
        self.players.pop(player, None)

    def _begin(self, observation: Mapping[str, Any], configuration: Any = None) -> tuple[int, int, dict[str, int]]:
        step, player = _step_player(observation)
        current = _inventory(observation)
        current_shops = _shop_vector(observation)
        _validate_shop_snapshot(step, current_shops, configuration)
        previous = self.players.get(player)
        if previous is None or step != previous["step"] + 1:
            return step, player, {}
        _validate_shop_transition(previous["step"], step, previous["shops"], current_shops)
        lower = _rival_supply_lower_bound(previous["inventory"], current,
                                          previous["town_consume"], previous["own_sell_upper"])
        return step, player, lower

    def _current_record(self, observation: Mapping[str, Any], action: Mapping[str, Any],
                        configuration: Any = None) -> tuple[int, dict[str, Any]]:
        """Validate/materialize current evidence before any action mutation."""
        step, player = _step_player(observation)
        shops = _shop_vector(observation)
        _validate_shop_snapshot(step, shops, configuration)
        return player, {
            "step": step,
            "inventory": _inventory(observation),
            "shops": shops,
            "town_consume": _town_consumption(observation, configuration),
            "own_sell_upper": _own_sell_upper(action),
        }

    def apply(self, observation: Mapping[str, Any], parent_action: Mapping[str, Any],
              configuration: Any = None) -> Mapping[str, Any]:
        try:
            _require_standard_market_cap(configuration)
        except (KeyError, TypeError, ValueError):
            self._drop_player(observation)
            return parent_action

        custom_params = (_get(configuration, "marketParams", None)
                         if configuration is not None else None)
        if custom_params is not None:
            if not isinstance(custom_params, Mapping) or custom_params:
                self._drop_player(observation)
                return parent_action

        try:
            step, player, evidence = self._begin(observation, configuration)
            current_player, current_record = self._current_record(
                observation, parent_action, configuration
            )
            if current_player != player:
                raise ValueError("player changed while materializing current evidence")
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

        # B10 only reorders existing SELL rows, so the prevalidated current
        # inventory/town/own-SELL record is identical for the returned action.
        self.players[player] = current_record
        return result


ORDER = RivalSupplyOrder(enabled=True)


def invalidate_public_supply_order(observation) -> None:
    """Break public-evidence continuity without applying the market transform."""
    ORDER._drop_player(observation)


def apply_public_supply_order(observation, parent_action, configuration=None, enabled=True):
    """Apply B10 to the final parent action; disabled is exact object identity."""
    if not enabled:
        return parent_action
    ORDER.enabled = True
    if configuration is None:
        invalidate_public_supply_order(observation)
        return parent_action
    return ORDER.apply(observation, parent_action, configuration)
