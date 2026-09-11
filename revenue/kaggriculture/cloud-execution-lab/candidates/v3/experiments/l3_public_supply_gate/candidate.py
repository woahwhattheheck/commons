# SPDX-License-Identifier: Apache-2.0
"""Experiment-only L3 gate using an observable rival net-supply lower bound.

This module is intentionally outside ``overlay/**`` and does not change V3.1
package inputs or defaults. It arms the exact #12377 L3 seam, but permits the
late ``reserve_sales()`` suppression only when recent public market inventory
transitions do *not* prove positive rival net supply.

For product p between our calls t and t+1, the official engine gives:

    delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

Therefore

    delta_inventory + town_consume - own_sell_requested

is a conservative lower bound on ``rival_sell - rival_buy`` because executed
own SELL is never greater than our requested SELL quantity and omitted own BUY
is non-negative. A positive lower bound proves rival net supply using only
public market/town state plus our own previous action. In that case the gate
keeps E184's normal reservation behavior; otherwise L3 may suppress it.

The first observation, gaps/rewinds, malformed state, and unknown shops all fail
closed to baseline E184 behavior.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
import sys
from typing import Any, Mapping

V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402
import r04_no_late_sale_advance as l3  # noqa: E402

PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
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
DEFAULT_LOOKBACK = 8


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _nonnegative_int(value: Any) -> int:
    number = int(value)
    if number < 0:
        raise ValueError("negative public market inventory")
    return number


def _market_inventory(observation: Mapping[str, Any]) -> dict[str, int]:
    market = _get(observation, "market", {})
    raw = _get(market, "inventory", {})
    if not isinstance(raw, Mapping):
        raise ValueError("market.inventory must be a mapping")
    return {item: _nonnegative_int(raw[item]) for item in PRODUCTS}


def _town_consumption(observation: Mapping[str, Any], configuration: Any = None) -> dict[str, int]:
    """Exact deterministic town demand that follows this step's market phase."""
    step = int(_get(observation, "step", -1))
    if step < 0:
        raise ValueError("invalid step")
    shop_interval = max(1, int(_get(configuration, "townShopSellInterval", 4)))
    center_interval = max(1, int(_get(configuration, "townCenterSellInterval", 24)))
    consume = {item: 0 for item in PRODUCTS}
    town = _get(observation, "town", {})
    shops = _get(town, "unlocked_shops", [])
    if not isinstance(shops, (list, tuple)):
        raise ValueError("town.unlocked_shops must be a sequence")
    known_shops = []
    for shop in shops:
        products = SHOPS.get(shop)
        if products is None:
            raise ValueError(f"unknown shop: {shop!r}")
        known_shops.append(products)
    if step % shop_interval == 0:
        for products in known_shops:
            multiplier = 2 if len(products) == 1 else 1
            for item in products:
                consume[item] += multiplier
    if step % center_interval == 0:
        for item in CENTER_PRODUCTS:
            consume[item] += 1
    return consume


def _own_sell_upper_bound(action: Mapping[str, Any]) -> dict[str, int]:
    """Upper-bound our admitted supply by requested SELL quantities."""
    upper = {item: 0 for item in PRODUCTS}
    market = _get(action, "market", [])
    if not isinstance(market, (list, tuple)):
        raise ValueError("action.market must be a sequence")
    for order in market:
        if not isinstance(order, (list, tuple)) or not order:
            continue
        if order[0] != "SELL":
            continue
        if len(order) < 3 or order[1] not in upper:
            raise ValueError("malformed SELL order")
        quantity = int(order[2])
        if quantity <= 0:
            raise ValueError("SELL quantity must be positive")
        upper[order[1]] += quantity
    return upper


def _rival_supply_lower_bound(
    previous_inventory: Mapping[str, int],
    current_inventory: Mapping[str, int],
    own_sell_upper: Mapping[str, int],
    town_consume: Mapping[str, int],
) -> dict[str, int]:
    """Conservative per-product lower bound on rival SELL minus rival BUY units."""
    return {
        item: int(current_inventory[item]) - int(previous_inventory[item])
        + int(town_consume.get(item, 0)) - int(own_sell_upper.get(item, 0))
        for item in PRODUCTS
    }


class PublicSupplyGate:
    def __init__(self, lookback: int = DEFAULT_LOOKBACK):
        self.lookback = int(lookback)
        if self.lookback < 1:
            raise ValueError("lookback must be positive")
        self.players: dict[int, dict[str, Any]] = {}
        self.last_evidence: dict[int, dict[str, int]] = {}

    def _fresh(self) -> dict[str, Any]:
        return {
            "last_step": None,
            "inventory": None,
            "own_sell_upper": None,
            "town_consume": None,
            "pressure": deque(maxlen=self.lookback),
        }

    def begin(self, observation: Mapping[str, Any]) -> bool:
        """Return whether L3 may suppress at this observation; false is fail-closed."""
        try:
            step = int(_get(observation, "step", -1))
            player = int(_get(observation, "player", -1))
            current = _market_inventory(observation)
            if step < 0 or player < 0:
                raise ValueError("invalid step/player")
        except (KeyError, TypeError, ValueError):
            return False

        state = self.players.setdefault(player, self._fresh())
        if state["last_step"] is None or step != int(state["last_step"]) + 1:
            state["pressure"].clear()
            self.last_evidence[player] = {}
            return False
        if state["inventory"] is None or state["own_sell_upper"] is None or state["town_consume"] is None:
            state["pressure"].clear()
            self.last_evidence[player] = {}
            return False

        try:
            lower = _rival_supply_lower_bound(
                state["inventory"], current, state["own_sell_upper"], state["town_consume"]
            )
        except (KeyError, TypeError, ValueError):
            state["pressure"].clear()
            self.last_evidence[player] = {}
            return False
        self.last_evidence[player] = lower
        state["pressure"].append(any(value > 0 for value in lower.values()))
        return not any(state["pressure"])

    def finish(self, observation: Mapping[str, Any], action: Mapping[str, Any], configuration: Any = None) -> None:
        """Record only public transition inputs and our own requested SELL upper bound."""
        try:
            step = int(_get(observation, "step", -1))
            player = int(_get(observation, "player", -1))
            if step < 0 or player < 0:
                raise ValueError("invalid step/player")
            inventory = _market_inventory(observation)
            own_sell_upper = _own_sell_upper_bound(action)
            town_consume = _town_consumption(observation, configuration)
        except (KeyError, TypeError, ValueError):
            if player >= 0:
                self.players[player] = self._fresh()
            return
        state = self.players.setdefault(player, self._fresh())
        state["last_step"] = step
        state["inventory"] = inventory
        state["own_sell_upper"] = own_sell_upper
        state["town_consume"] = town_consume


GATE = PublicSupplyGate()
REPORT = {
    "late_decisions": 0,
    "suppressed": 0,
    "guarded": 0,
    "last_step": None,
}
_ALLOW_SUPPRESS = False
_ORIGINAL_SUPPRESSED = l3.suppressed


def _conditional_suppressed(step: Any, enabled: Any, threshold: Any = l3.DEFAULT_THRESHOLD) -> bool:
    step = int(step)
    threshold = int(threshold)
    if not bool(enabled) or step < threshold:
        return False
    REPORT["late_decisions"] += 1
    REPORT["last_step"] = step
    if not _ALLOW_SUPPRESS:
        REPORT["guarded"] += 1
        return False
    REPORT["suppressed"] += 1
    # Preserve #12377's L3 telemetry contract on actual suppression only.
    l3.REPORT["suppressed_steps"] += 1
    l3.REPORT["last"] = step
    return True


BASE_AGENT = base.install(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    no_late_sale_advance=True,
    no_late_sale_advance_step=648,
)


def agent(observation, configuration=None):
    """Exact live-R04 baseline + L3, conditioned only by public supply evidence."""
    global _ALLOW_SUPPRESS
    _ALLOW_SUPPRESS = GATE.begin(observation)
    l3.suppressed = _conditional_suppressed
    try:
        action = BASE_AGENT(observation, configuration)
    finally:
        l3.suppressed = _ORIGINAL_SUPPRESSED
        _ALLOW_SUPPRESS = False
    GATE.finish(observation, action, configuration)
    return action


agent.telemetry = REPORT
