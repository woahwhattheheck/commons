# SPDX-License-Identifier: Apache-2.0
"""S33 row-shed source contract for V3.1.

This module is deliberately outside deterministic package inputs.  It freezes the
narrow mechanism measured by the S33 field gate before production composition:
rank only the contiguous leading SELL block using the units that can actually be
sold from the current projected shed, rather than the tape's requested quantity.

The transform never changes a market row or quantity.  It only reorders existing
leading SELL rows.  Malformed inputs fail closed to the original market ordering.
"""


def _strict_nonnegative_int(value):
    return type(value) is int and value >= 0


def effective_sell_quantity(order, projected_shed):
    """Return min(requested SELL units, projected shed units), or None on ambiguity."""
    if not isinstance(order, (list, tuple)) or len(order) < 3 or order[0] != "SELL":
        return None
    if not isinstance(projected_shed, dict):
        return None
    item = order[1]
    requested = order[2]
    available = projected_shed.get(item, 0)
    if not _strict_nonnegative_int(requested) or not _strict_nonnegative_int(available):
        return None
    return min(requested, available)


def order_leading_sells(market, inventory, projected_shed, price_fn, inventory_default=10000):
    """Stable-sort the leading SELL block by executable price-drop value.

    ``price_fn(item, inventory_level)`` is the incumbent R04 price curve.  Every
    market row and requested quantity is preserved byte-for-byte at the value
    level; only the order of the leading SELL rows can change.
    """
    if not isinstance(market, list) or not isinstance(inventory, dict):
        return market
    if not _strict_nonnegative_int(inventory_default):
        return market

    lead = 0
    while lead < len(market):
        order = market[lead]
        if not isinstance(order, list) or not order or order[0] != "SELL":
            break
        lead += 1
    if lead < 2:
        return market

    scored = []
    for index, order in enumerate(market[:lead]):
        if len(order) < 3:
            return market
        item = order[1]
        quantity = effective_sell_quantity(order, projected_shed)
        level = inventory.get(item, inventory_default)
        if quantity is None or not _strict_nonnegative_int(level):
            return market
        try:
            before = price_fn(item, level)
            after = price_fn(item, level + quantity)
        except Exception:
            return market
        if not _strict_nonnegative_int(before) or not _strict_nonnegative_int(after):
            return market
        scored.append(((before - after) * quantity, index, order))

    # Python's sort is stable; index is retained only as an explicit source-contract
    # witness that equal scores keep the incumbent row order.
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored] + market[lead:]
