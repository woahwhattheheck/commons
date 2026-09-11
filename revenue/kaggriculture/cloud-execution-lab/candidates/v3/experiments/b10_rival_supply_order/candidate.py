# SPDX-License-Identifier: Apache-2.0
"""Experiment-only B10 public rival-supply SELL ordering.

This module uses only public market/town observations plus our own previous
returned action. For product p between callbacks t and t+1, the official engine
gives::

    delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

Because executed own SELL cannot exceed our requested SELL quantity and executed
own BUY is non-negative::

    rival_sell - rival_buy >= delta_inventory + town_consume - own_sell_requested

A positive lower bound therefore proves realized rival net supply without reading
rival orders, shed, or carried inventory. The bound is conservative: our own BUY
can hide rival supply, and failed / $1-floor own SELL requests only reduce the
bound because requested SELL is an upper bound on inventory-increasing own supply.

When enabled, B10 may reorder only the parent's already-existing leading SELL
block. WHEAT stays at its exact row index (C5 owns WHEAT-demand timing), every
quantity and non-WHEAT row is preserved, and products with stronger proven
prior-step rival net supply move earlier among the remaining non-WHEAT SELL
positions. A later cash-spending row vetoes the transform so the experiment
cannot perturb financing for HIRE/BUY_* obligations.

No row is added or removed. Farmer/hand actions, product quantities, WHEAT rows,
non-leading rows, and market-order count are exact-parent. This lives outside
``overlay/**`` and has no release/default/package/Kaggle authority.
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

PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
WHEAT = "WHEAT"
MAX_ORDERS = 10
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
        raise ValueError(f"{label} must be a JSON integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    number = _strict_int(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _step_player(observation: Mapping[str, Any]) -> tuple[int, int]:
    step = _strict_int(_get(observation, "step", None), "step")
    player = _strict_int(_get(observation, "player", None), "player")
    if step < 0 or player < 0:
        raise ValueError("negative step/player")
    return step, player


def _inventory(observation: Mapping[str, Any]) -> dict[str, int]:
    market = _get(observation, "market", None)
    raw = _get(market, "inventory", None)
    if not isinstance(raw, Mapping):
        raise ValueError("market.inventory must be a mapping")
    return {item: _strict_int(raw[item], f"market.inventory.{item}") for item in PRODUCTS}


def _interval(configuration: Any, key: str, default: int) -> int:
    value = _get(configuration, key, default) if configuration is not None else default
    return _positive_int(value, key)


def _town_consumption(observation: Mapping[str, Any], configuration: Any = None) -> dict[str, int]:
    """Exact deterministic public town demand after this callback's market phase."""
    step, _ = _step_player(observation)
    shop_interval = _interval(configuration, "townShopSellInterval", 4)
    center_interval = _interval(configuration, "townCenterSellInterval", 24)
    town = _get(observation, "town", None)
    shops = _get(town, "unlocked_shops", None)
    if not isinstance(shops, (list, tuple)):
        raise ValueError("town.unlocked_shops must be a sequence")

    consume = {item: 0 for item in PRODUCTS}
    known = []
    for shop in shops:
        if type(shop) is not str or shop not in SHOPS:
            raise ValueError(f"unknown shop {shop!r}")
        known.append(SHOPS[shop])
    if step % shop_interval == 0:
        for products in known:
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
    if len(rows) > MAX_ORDERS:
        # The official engine truncates after ten. Treat an oversized parent as
        # ambiguous rather than pretending rows beyond the prefix do not matter.
        raise ValueError("parent market exceeds executable prefix")
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


def _rival_supply_lower_bound(
    previous_inventory: Mapping[str, int],
    current_inventory: Mapping[str, int],
    previous_town_consume: Mapping[str, int],
    previous_own_sell_upper: Mapping[str, int],
) -> dict[str, int]:
    """Conservative lower bound on rival SELL minus rival BUY for each product."""
    return {
        item: (
            int(current_inventory[item])
            - int(previous_inventory[item])
            + int(previous_town_consume[item])
            - int(previous_own_sell_upper[item])
        )
        for item in PRODUCTS
    }


def _cash_spending(order: Any) -> bool:
    return isinstance(order, (list, tuple)) and bool(order) and order[0] in BUY_OPS


def _leading_sell_count(rows: Sequence[Any]) -> int:
    lead = 0
    while lead < len(rows):
        order = rows[lead]
        if not isinstance(order, (list, tuple)) or not order or order[0] != "SELL":
            break
        lead += 1
    return lead


def _reorder_leading_sells(
    action: Mapping[str, Any], evidence: Mapping[str, int]
) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Prioritize proven rival-supply products inside the existing leading SELL block."""
    rows = _market_rows(action)
    lead = _leading_sell_count(rows)
    if lead < 2:
        return action, None
    if any(_cash_spending(order) for order in rows[lead:]):
        return action, None

    # Keep every WHEAT row fixed so C5 and feed/funding semantics are outside B10.
    movable_indices: list[int] = []
    movable_rows: list[list[Any]] = []
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

    # Python sort is stable, so native R04 order remains the exact tie-breaker.
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

    def _begin(self, observation: Mapping[str, Any]) -> tuple[int, int, dict[str, int]]:
        step, player = _step_player(observation)
        current = _inventory(observation)
        previous = self.players.get(player)
        if previous is None or step != previous["step"] + 1:
            return step, player, {}
        lower = _rival_supply_lower_bound(
            previous["inventory"], current, previous["town_consume"], previous["own_sell_upper"]
        )
        return step, player, lower

    def _finish(
        self,
        observation: Mapping[str, Any],
        action: Mapping[str, Any],
        configuration: Any = None,
    ) -> None:
        step, player = _step_player(observation)
        self.players[player] = {
            "step": step,
            "inventory": _inventory(observation),
            "town_consume": _town_consumption(observation, configuration),
            "own_sell_upper": _own_sell_upper(action),
        }

    def apply(
        self,
        observation: Mapping[str, Any],
        parent_action: Mapping[str, Any],
        configuration: Any = None,
    ) -> Mapping[str, Any]:
        try:
            _, _, evidence = self._begin(observation)
        except (KeyError, TypeError, ValueError):
            return parent_action

        result: Mapping[str, Any] = parent_action
        positives = [item for item, value in evidence.items() if value > 0]
        if positives:
            self.telemetry["confirmed_supply_transitions"] += 1
            self.telemetry["last_positive_products"] = sorted(positives)
            custom_params = _get(configuration, "marketParams", None) if configuration is not None else None
            if self.enabled and not custom_params:
                try:
                    candidate, detail = _reorder_leading_sells(parent_action, evidence)
                    if detail is not None:
                        result = candidate
                        self.telemetry["reorders"] += 1
                        self.telemetry["last_before"] = detail["before"]
                        self.telemetry["last_after"] = detail["after"]
                except (KeyError, TypeError, ValueError):
                    result = parent_action

        try:
            # B10 changes order only, not SELL quantities. Record the action we
            # actually emit so the next transition stays bound to our output.
            self._finish(observation, result, configuration)
        except (KeyError, TypeError, ValueError):
            try:
                _, player = _step_player(observation)
                self.players.pop(player, None)
            except (KeyError, TypeError, ValueError):
                pass
        return result


# Exact ready-V3.1 R04 tuple on frozen pre-L3 base 508b.
BASE_AGENT = base.install(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)
ORDER = RivalSupplyOrder(enabled=True)


def agent(observation, configuration=None):
    parent = BASE_AGENT(observation, configuration)
    return ORDER.apply(observation, parent, configuration)


agent.telemetry = ORDER.telemetry
