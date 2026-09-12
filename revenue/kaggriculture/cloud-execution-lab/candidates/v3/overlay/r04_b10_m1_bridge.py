# SPDX-License-Identifier: Apache-2.0
"""Internal V4 B10/M1 composition helper with no public feature key.

The predecessor ``r04_b10_public_supply_order.py`` stays byte-exact.  The router may call
this helper only from the existing post-EOD B10 slot when both predecessor features
``M1_WHEAT_TRADE`` and ``B10_PUBLIC_SUPPLY_ORDER`` are already enabled.  If the final
market row is the narrow independently-funded WHEAT purchase shape proved by M1, the
helper removes only that row, calls canonical B10 exactly once on the copied prefix, then
restores the exact BUY tail.  Otherwise it calls canonical B10 once on the untouched
parent action.

There is deliberately no ``r04_b10_m1_bridge`` config key, Features field, install
parameter, router flag, or independent enable bit.  This module resolves only the
intersection of two existing features, so either predecessor feature alone retains its
pre-composition behavior and public API.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Mapping


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _finite_nonnegative_money(value: Any) -> bool:
    """Engine money is numeric; hostile JSON ints must fail closed, never overflow."""
    if type(value) not in (int, float) or value < 0:
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _safe_prefunded_tail(observation: Any, action: Any, configuration: Any):
    """Return the exact removable M1 WHEAT BUY row, else ``None``.

    The proof is intentionally no broader than current M1: standard config/default
    market, executable literal rows, one final q<=MAX_BUY WHEAT BUY, no earlier
    purchase/WHEAT row, enough public WHEAT stock and shed room, and cash that remains
    sufficient even at M1's same-turn +25 WHEAT surcharge bound.  Reordering
    non-WHEAT SELL rows therefore cannot fund or defund this BUY.
    """
    import r04_m1_wheat_trade as m1

    if not m1._standard_configuration(configuration):
        return None
    if not isinstance(action, dict):
        return None
    rows = action.get("market")
    if not isinstance(rows, list) or not rows or len(rows) > m1.MAX_ORDERS:
        return None

    tail = rows[-1]
    if (not isinstance(tail, list) or len(tail) != 3
            or tail[:2] != ["BUY_PRODUCT", "WHEAT"]):
        return None
    quantity = tail[2]
    if type(quantity) is not int or not (1 <= quantity <= m1.MAX_BUY):
        return None

    for row in rows[:-1]:
        if not isinstance(row, list):
            return None
        if not row:
            continue
        if not isinstance(row[0], str):
            return None
        if row[0] in m1._PURCHASE_OPS:
            return None
        if len(row) > 1 and row[1] == "WHEAT":
            return None

    if not isinstance(observation, dict):
        return None
    player = observation.get("player")
    farms = observation.get("farms")
    market = observation.get("market")
    private = observation.get("private")
    if (type(player) is not int or player not in (0, 1)
            or not isinstance(farms, list) or player >= len(farms)
            or not isinstance(farms[player], dict)
            or not isinstance(market, dict) or not isinstance(private, dict)):
        return None

    prices = market.get("prices")
    public_inventory = market.get("inventory")
    shed = private.get("shed")
    if not isinstance(prices, dict) or not isinstance(public_inventory, dict) or not isinstance(shed, dict):
        return None

    quote = prices.get("WHEAT")
    wheat_market = public_inventory.get("WHEAT")
    if type(quote) is not int or quote < 1:
        return None
    if type(wheat_market) is not int or wheat_market < quantity:
        return None

    if any(type(value) is not int or value < 0 for value in shed.values()):
        return None
    if sum(shed.values()) + quantity > m1.SHED_CAPACITY:
        return None

    money = farms[player].get("money")
    if not _finite_nonnegative_money(money):
        return None
    required = m1.CASH_RESERVE + quantity * (quote + m1.SAME_TURN_WHEAT_SURCHARGE)
    if money < required:
        return None

    return tail


def apply_b10_m1_bridge(observation: Any, parent_action: Any, configuration: Any = None):
    """Call canonical B10 exactly once, optionally hiding one certified M1 BUY tail.

    Caller contract: this function is entered only when both existing predecessor
    feature flags are true.  Keeping that gate in the router avoids inventing a third
    independently-configurable feature whose semantics depend on the other two.
    """
    import r04_b10_public_supply_order as b10

    tail = _safe_prefunded_tail(observation, parent_action, configuration)
    if tail is None:
        return b10.apply_public_supply_order(
            observation, parent_action, configuration, enabled=True,
        )

    stripped = copy.deepcopy(parent_action)
    stripped["market"].pop()
    result = b10.apply_public_supply_order(
        observation, stripped, configuration, enabled=True,
    )

    # Canonical B10 returning the exact stripped object means it changed no action
    # bytes. Its evidence record intentionally ignores BUY rows, so the original
    # parent action is the exact final result.
    if result is stripped:
        return parent_action

    restored = copy.deepcopy(result)
    restored["market"].append(copy.deepcopy(tail))
    return restored
