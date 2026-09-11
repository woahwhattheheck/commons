# SPDX-License-Identifier: Apache-2.0
"""S33 row-shed donor: rank leading SELL rows by units that can actually execute.

This module is intentionally package-neutral. The production consumer should splice the
same bounded quantity into R04's existing ``order_sells`` score while leaving order rows,
quantities, non-SELL barriers, and the default price curve untouched.
"""
from __future__ import annotations


def sellable_quantity(order, projected_shed):
    """Return the row's executable scoring quantity, capped by projected own shed stock."""
    if len(order) < 3:
        return 0
    quantity = max(0, int(order[2]))
    item = order[1]
    available = max(0, int(projected_shed.get(item, 0)))
    return min(quantity, available)


def order_sells(market, inventory, projected_shed, price_fn, price_params):
    """Stable-sort only the leading SELL block using projected-shed-bounded price impact.

    This is the exact S33 mechanism: the submitted row is never edited. Only its ranking
    score substitutes ``min(requested quantity, projected shed quantity)`` for the authored
    request quantity. Rows after the first non-SELL barrier retain their exact positions.
    """
    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market

    def drop(order):
        item = order[1]
        if item not in price_params or len(order) < 3:
            return 0
        level = int(inventory.get(item, 10000))
        quantity = sellable_quantity(order, projected_shed)
        return (price_fn(item, level) - price_fn(item, level + quantity)) * quantity

    return sorted(market[:lead], key=drop, reverse=True) + market[lead:]
