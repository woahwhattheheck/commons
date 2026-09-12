# SPDX-License-Identifier: Apache-2.0
"""Internal V4 B10/M1 composition helper with no public feature key.

The predecessor ``r04_b10_public_supply_order.py`` stays byte-exact. The router may call
this helper only from the existing post-EOD B10 slot when both predecessor features
``M1_WHEAT_TRADE`` and ``B10_PUBLIC_SUPPLY_ORDER`` are already enabled.

Crucially, a WHEAT BUY is hidden from B10 only when the caller supplies the exact action
that entered M1 and the post-EOD action is provably that exact market prefix plus one
safe final M1-shaped WHEAT BUY. Shape/funding alone is not provenance: another shipped
controller can already own a final WHEAT BUY, in which case M1 returns its parent
unchanged and canonical B10's cash-spend veto must remain in force.
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
    """Engine money is numeric; hostile huge ints must fail closed, never overflow."""
    if type(value) not in (int, float) or value < 0:
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _m1_append_provenance(parent_action: Any, final_action: Any) -> bool:
    """Prove final market == exact pre-M1 market + exactly one row."""
    if not isinstance(parent_action, dict) or not isinstance(final_action, dict):
        return False
    before = parent_action.get("market")
    after = final_action.get("market")
    if not isinstance(before, list) or not isinstance(after, list):
        return False
    if len(after) != len(before) + 1:
        return False
    # Equality is intentionally structural rather than identity: M1 deep-copies
    # its output, while EOD may conservatively return that copied action unchanged.
    return after[:-1] == before


def _safe_prefunded_tail(observation: Any, action: Any, configuration: Any,
                         m1_parent_action: Any):
    """Return exact removable M1-authored WHEAT BUY row, else ``None``."""
    import r04_m1_wheat_trade as m1

    if not _m1_append_provenance(m1_parent_action, action):
        return None
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


def apply_b10_m1_bridge(observation: Any, parent_action: Any, configuration: Any = None,
                        *, m1_parent_action: Any = None):
    """Call canonical B10 once; hide one BUY only with exact M1 append provenance."""
    import r04_b10_public_supply_order as b10

    tail = _safe_prefunded_tail(
        observation, parent_action, configuration, m1_parent_action,
    )
    if tail is None:
        return b10.apply_public_supply_order(
            observation, parent_action, configuration, enabled=True,
        )

    stripped = copy.deepcopy(parent_action)
    stripped["market"].pop()
    result = b10.apply_public_supply_order(
        observation, stripped, configuration, enabled=True,
    )

    if result is stripped:
        return parent_action

    restored = copy.deepcopy(result)
    restored["market"].append(copy.deepcopy(tail))
    return restored
