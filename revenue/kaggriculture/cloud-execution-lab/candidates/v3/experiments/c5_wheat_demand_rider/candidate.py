# SPDX-License-Identifier: Apache-2.0
"""Experiment-only C5 wheat demand rider.

The experiment uses only public market/town observations plus our own previous
returned action.  The official engine's market inventory counts successful BUYs
as negative inventory and successful SELLs as positive inventory *except* a SELL
quoted at the $1 floor, which pays the seller but does not add market inventory.
For WHEAT between callbacks this gives a conservative gross-buy theorem::

    rival_buy >= previous_inventory - current_inventory
                 - town_consume - own_buy_requested_upper_bound

Visible own/rival sells can only make this bound smaller, failed/partial own BUYs
can only make it smaller, and inventory-invisible $1 sells do not make inventory
fall.  A positive value therefore proves at least that many realized rival
BUY_PRODUCT(WHEAT) units; it does *not* prove rival net demand after hidden sells.

On such a transition, C5 may move exactly one already-authored current WHEAT
SELL row to a newly appended trailing market row.  The original row becomes an
empty no-op, every other raw row keeps the exact same index/content, total WHEAT
SELL quantity is unchanged, and any later executable cash-spending row vetoes
the move so we cannot remove sale funding from a purchase.  The executable row
cap is derived from the current runtime configuration with official integer
clamping (max(1, cap)); non-integer/bool cap values fail closed.

This module lives outside overlay/**.  It is default-OFF research evidence and
has no release/default/package/Kaggle authority.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

DEFAULT_MAX_ORDERS = 10
WHEAT = "WHEAT"
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


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _strict_int(value: Any, label: str) -> int:
    if type(value) is not int:  # bool must not alias int in evidence logic.
        raise ValueError(f"{label} must be a JSON integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    number = _strict_int(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _interval(configuration: Any, key: str, default: int) -> int:
    value = _get(configuration, key, default) if configuration is not None else default
    return _positive_int(value, key)


def _market_cap(configuration: Any = None) -> int:
    """Strict subset of official cap semantics: exact ints clamp to >=1; others fail closed."""
    value = _get(configuration, "maxMarketOrdersPerTurn", DEFAULT_MAX_ORDERS) if configuration is not None else DEFAULT_MAX_ORDERS
    return max(1, _strict_int(value, "maxMarketOrdersPerTurn"))


def _step_player(observation: Mapping[str, Any]) -> tuple[int, int]:
    step = _strict_int(_get(observation, "step", None), "step")
    player = _strict_int(_get(observation, "player", None), "player")
    if step < 0 or player < 0:
        raise ValueError("negative step/player")
    return step, player


def _wheat_inventory(observation: Mapping[str, Any]) -> int:
    market = _get(observation, "market", None)
    inventory = _get(market, "inventory", None)
    if not isinstance(inventory, Mapping) or WHEAT not in inventory:
        raise ValueError("missing public WHEAT inventory")
    return _strict_int(inventory[WHEAT], "market.inventory.WHEAT")


def _wheat_price(observation: Mapping[str, Any]) -> int:
    market = _get(observation, "market", None)
    prices = _get(market, "prices", None)
    if not isinstance(prices, Mapping) or WHEAT not in prices:
        raise ValueError("missing public WHEAT price")
    return _strict_int(prices[WHEAT], "market.prices.WHEAT")


def _town_wheat_consumption(observation: Mapping[str, Any], configuration: Any = None) -> int:
    """Exact deterministic WHEAT units consumed after this step's market phase."""
    step, _ = _step_player(observation)
    shop_interval = _interval(configuration, "townShopSellInterval", 4)
    center_interval = _interval(configuration, "townCenterSellInterval", 24)
    town = _get(observation, "town", None)
    shops = _get(town, "unlocked_shops", None)
    if not isinstance(shops, (list, tuple)):
        raise ValueError("town.unlocked_shops must be a sequence")

    consume = 0
    if step % shop_interval == 0:
        for shop in shops:
            if type(shop) is not str or shop not in SHOPS:
                raise ValueError(f"unknown shop {shop!r}")
            products = SHOPS[shop]
            if WHEAT in products:
                # All WHEAT-consuming shops are multi-product; multiplier == 1.
                consume += 1
    else:
        for shop in shops:
            if type(shop) is not str or shop not in SHOPS:
                raise ValueError(f"unknown shop {shop!r}")
    if step % center_interval == 0:
        consume += 1
    return consume


def _market_rows(action: Mapping[str, Any], executable_cap: int) -> list[Any]:
    market = _get(action, "market", None)
    if not isinstance(market, list):
        raise ValueError("action.market must be a list")
    if type(executable_cap) is not int or executable_cap < 1:
        raise ValueError("executable cap must be a positive integer")
    return market[:executable_cap]


def _own_wheat_buy_upper(action: Mapping[str, Any], executable_cap: int) -> int:
    """Upper-bound successfully executed own WHEAT BUY_PRODUCT units."""
    total = 0
    for order in _market_rows(action, executable_cap):
        if not isinstance(order, (list, tuple)) or not order:
            continue
        if order[0] != "BUY_PRODUCT" or len(order) < 2 or order[1] != WHEAT:
            continue
        if len(order) < 3:
            # Engine would parse this as a no-op; fail closed rather than infer.
            raise ValueError("malformed own WHEAT BUY_PRODUCT")
        total += _positive_int(order[2], "own WHEAT BUY quantity")
    return total


def _rival_wheat_buy_lower_bound(
    previous_inventory: int,
    current_inventory: int,
    previous_town_consume: int,
    previous_own_buy_upper: int,
) -> int:
    """Conservative lower bound on gross realized rival BUY_PRODUCT(WHEAT) units."""
    return (
        int(previous_inventory)
        - int(current_inventory)
        - int(previous_town_consume)
        - int(previous_own_buy_upper)
    )


def _cash_spending(order: Any) -> bool:
    return isinstance(order, (list, tuple)) and bool(order) and order[0] in BUY_OPS


def _relocate_wheat_sell(
    action: Mapping[str, Any], executable_cap: int
) -> tuple[Mapping[str, Any], dict[str, int] | None]:
    """Move one executable WHEAT SELL to a new executable tail row without shifting others."""
    market = _market_rows(action, executable_cap)
    # Appending must remain inside the runtime executable prefix.  If raw action
    # has a tail past the cap, len(market)==cap and this fails closed.
    if len(market) >= executable_cap:
        return action, None

    wheat_rows: list[tuple[int, Sequence[Any]]] = []
    for index, order in enumerate(market):
        if not isinstance(order, (list, tuple)) or not order or len(order) < 2:
            continue
        if order[1] != WHEAT:
            continue
        # Ambiguous same-product market activity is intentionally outside C5.
        if order[0] != "SELL" or len(order) < 3:
            return action, None
        try:
            _positive_int(order[2], "WHEAT SELL quantity")
        except ValueError:
            return action, None
        wheat_rows.append((index, order))

    if len(wheat_rows) != 1:
        return action, None
    index, _order = wheat_rows[0]

    # Removing the earlier sale must not remove funding from any later executable spend.
    if any(_cash_spending(row) for row in market[index + 1 :]):
        return action, None

    result = copy.deepcopy(action)
    result_market = result["market"]
    moved = copy.deepcopy(result_market[index])
    result_market[index] = []
    result_market.append(moved)
    return result, {
        "from_index": index,
        "to_index": len(result_market) - 1,
        "quantity": _positive_int(moved[2], "moved WHEAT SELL quantity"),
    }


class WheatDemandRider:
    """Per-player public-transition detector + same-step sale-row timing transform."""

    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
        self.players: dict[int, dict[str, int]] = {}
        self.telemetry = {
            "confirmed_rival_buy_transitions": 0,
            "relocations": 0,
            "moved_units": 0,
            "last_rival_buy_lower_bound": 0,
            "last_from_index": None,
            "last_to_index": None,
        }

    def _begin(self, observation: Mapping[str, Any]) -> tuple[int, int, int]:
        step, player = _step_player(observation)
        current_inventory = _wheat_inventory(observation)
        previous = self.players.get(player)
        if previous is None or step != previous["step"] + 1:
            return step, player, 0
        lower = _rival_wheat_buy_lower_bound(
            previous["inventory"],
            current_inventory,
            previous["town_consume"],
            previous["own_buy_upper"],
        )
        return step, player, lower

    def _current_record(
        self,
        observation: Mapping[str, Any],
        action: Mapping[str, Any],
        configuration: Any = None,
    ) -> tuple[int, dict[str, int], int, int]:
        """Validate/materialize all current evidence before any timing mutation."""
        step, player = _step_player(observation)
        executable_cap = _market_cap(configuration)
        price = _wheat_price(observation)
        record = {
            "step": step,
            "inventory": _wheat_inventory(observation),
            "town_consume": _town_wheat_consumption(observation, configuration),
            "own_buy_upper": _own_wheat_buy_upper(action, executable_cap),
        }
        return player, record, price, executable_cap

    def _forget_player(self, observation: Mapping[str, Any]) -> None:
        try:
            _, player = _step_player(observation)
            self.players.pop(player, None)
        except (KeyError, TypeError, ValueError):
            pass

    def apply(
        self,
        observation: Mapping[str, Any],
        parent_action: Mapping[str, Any],
        configuration: Any = None,
    ) -> Mapping[str, Any]:
        """Return exact parent unless all public C5 predicates are proved."""
        try:
            _, player, lower = self._begin(observation)
            current_player, current_record, current_price, executable_cap = self._current_record(
                observation, parent_action, configuration
            )
            if current_player != player:
                raise ValueError("player changed while materializing evidence")
        except (KeyError, TypeError, ValueError):
            # Current malformed evidence invalidates the transition *before* any
            # relocation and clears stale state so it cannot authorize next turn.
            self._forget_player(observation)
            return parent_action

        result: Mapping[str, Any] = parent_action
        if lower > 0:
            self.telemetry["confirmed_rival_buy_transitions"] += 1
            self.telemetry["last_rival_buy_lower_bound"] = lower
            if self.enabled and current_price > 1:
                try:
                    candidate, moved = _relocate_wheat_sell(parent_action, executable_cap)
                    if moved is not None:
                        result = candidate
                        self.telemetry["relocations"] += 1
                        self.telemetry["moved_units"] += moved["quantity"]
                        self.telemetry["last_from_index"] = moved["from_index"]
                        self.telemetry["last_to_index"] = moved["to_index"]
                except (KeyError, TypeError, ValueError):
                    result = parent_action

        # Relocation changes only a SELL row, so the already-validated record of
        # own BUY upper-bound/town/public inventory is identical for result.
        self.players[player] = current_record
        return result


# Exact ready-V3.1 R04 tuple from V3-MANIFEST.json at frozen base 508b.  This
# base predates the separate L3 carrier, so no L3 keyword is passed to install().
BASE_AGENT = base.install(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)
RIDER = WheatDemandRider(enabled=True)


def agent(observation, configuration=None):
    parent = BASE_AGENT(observation, configuration)
    return RIDER.apply(observation, parent, configuration)


agent.telemetry = RIDER.telemetry
