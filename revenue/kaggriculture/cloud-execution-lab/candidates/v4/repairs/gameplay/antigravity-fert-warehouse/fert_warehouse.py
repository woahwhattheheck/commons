# SPDX-License-Identifier: Apache-2.0
"""Recovered fertilizer capacity lane, narrowed to mechanics the engine supports.

The predecessor described `$1` fertilizer sales as infinite off-site storage.
The official engine says otherwise: SELL can consume only shed inventory and a
sale quoted at the $1 floor deliberately does *not* increase market inventory.
A later BUY_PRODUCT decrements market inventory. Therefore floor dumping is
liquidation, not storage, and cannot carry a 1:1 buyback theorem.

This repair keeps the historical ``r04_fert_warehouse`` key for convergence,
but Mode B is now narrowly an EOD-capacity liquidation: only when the projected
end-of-day hand drop would overflow the shed, sell at most the number of shed
FERTILIZER units needed to create that much room. Hand inventory is never
claimed directly sellable.

Mode A retains the recovered revenue-timing experiment, also restricted to
currently sellable shed FERTILIZER. Default OFF; economics remain ungated.
"""
from __future__ import annotations

from typing import Any

SHED_CAPACITY = 100
PRICE_FLOOR = 1
REVENUE_PRICE_THRESHOLD = 44


def _plain_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _shed(private: Any) -> dict[str, Any] | None:
    if not isinstance(private, dict):
        return None
    shed = private.get("shed")
    return shed if isinstance(shed, dict) else None


def _inventories(private: Any) -> list[dict[str, Any]] | None:
    if not isinstance(private, dict):
        return None
    inventories = private.get("inventories")
    if not isinstance(inventories, list):
        return None
    if any(not isinstance(inv, dict) for inv in inventories):
        return None
    return inventories


def _mapping_units(mapping: dict[str, Any]) -> int | None:
    total = 0
    for value in mapping.values():
        qty = _plain_nonnegative_int(value)
        if qty is None:
            return None
        total += qty
    return total


def shed_total(private: Any) -> int | None:
    shed = _shed(private)
    return None if shed is None else _mapping_units(shed)


def shed_fertilizer(private: Any) -> int | None:
    shed = _shed(private)
    if shed is None:
        return None
    return _plain_nonnegative_int(shed.get("FERTILIZER", 0))


def incoming_inventory_total(private: Any) -> int | None:
    inventories = _inventories(private)
    if inventories is None:
        return None
    total = 0
    for inv in inventories:
        units = _mapping_units(inv)
        if units is None:
            return None
        total += units
    return total


def projected_eod_overflow(private: Any, shed_capacity: int = SHED_CAPACITY) -> int | None:
    capacity = _plain_nonnegative_int(shed_capacity)
    shed_units = shed_total(private)
    incoming = incoming_inventory_total(private)
    if capacity is None or shed_units is None or incoming is None:
        return None
    return max(0, shed_units + incoming - capacity)


def overflow_liquidation_quantity(private: Any, market_price: Any, *,
                                  shed_capacity: int = SHED_CAPACITY) -> int:
    """Shed FERT to sell at the floor solely to create projected EOD room."""
    price = _plain_nonnegative_int(market_price)
    overflow = projected_eod_overflow(private, shed_capacity)
    fertilizer = shed_fertilizer(private)
    if price != PRICE_FLOOR or overflow is None or fertilizer is None:
        return 0
    return min(overflow, fertilizer)


def revenue_sell_quantity(private: Any, market_price: Any, *,
                          revenue_price_threshold: int = REVENUE_PRICE_THRESHOLD) -> int:
    """Recovered revenue mode; only shed inventory is market-sellable."""
    price = _plain_nonnegative_int(market_price)
    threshold = _plain_nonnegative_int(revenue_price_threshold)
    fertilizer = shed_fertilizer(private)
    if price is None or threshold is None or fertilizer is None or price < threshold:
        return 0
    return fertilizer


def decide(private: Any, market_price: Any, *,
           shed_capacity: int = SHED_CAPACITY,
           revenue_price_threshold: int = REVENUE_PRICE_THRESHOLD) -> dict[str, Any]:
    """Return one sell decision: ``overflow_liquidation`` / ``revenue`` / ``hold``."""
    overflow_qty = overflow_liquidation_quantity(
        private,
        market_price,
        shed_capacity=shed_capacity,
    )
    if overflow_qty > 0:
        return {
            "mode": "overflow_liquidation",
            "orders": [["SELL", "FERTILIZER", overflow_qty]],
        }

    revenue_qty = revenue_sell_quantity(
        private,
        market_price,
        revenue_price_threshold=revenue_price_threshold,
    )
    if revenue_qty > 0:
        return {
            "mode": "revenue",
            "orders": [["SELL", "FERTILIZER", revenue_qty]],
        }
    return {"mode": "hold", "orders": []}
