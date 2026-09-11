# SPDX-License-Identifier: Apache-2.0
"""S33 row-shed donor for the current V3.1 convergence root.

This module isolates the field-tested ROW_ORDER scoring change without changing
production defaults.  The production consumer should pass the result of
r04_full_router.projected_shed(action, FarmView(observation)) as
``projected_shed`` and keep the SELL rows themselves byte-for-byte unchanged.
"""

import math


_RO_PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO": (60, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}
_RO_I0 = 10000


def _ro_shape(func, x, span):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return x ** 0.5
    if func == "log":
        return math.log(1.0 + x)
    if func == "hinge":
        u = x / span
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def _ro_price(item, inventory):
    base, span, below_f, below_t, above_f, above_t = _RO_PARAMS[item]
    if inventory < _RO_I0:
        amp = below_t * base / _ro_shape(below_f, span, span)
        price = base + amp * _ro_shape(below_f, _RO_I0 - inventory, span)
    else:
        amp = above_t * base / _ro_shape(above_f, span, span)
        price = base - amp * _ro_shape(above_f, inventory - _RO_I0, span)
    return max(1, int(round(price)))


def _effective_quantity(item, requested, projected_shed):
    """Return the quantity used only for ROW_ORDER valuation.

    ``None`` or malformed projection data deliberately falls back to the
    inherited requested-quantity score.  A real projected shed produced by the
    current router contains strict integer quantities for every product.
    """
    if type(projected_shed) is not dict:
        return requested
    available = projected_shed.get(item)
    if type(available) is not int:
        return requested
    return min(requested, max(0, available))


def order_sells(market, inventory, projected_shed=None):
    """Rank only the contiguous leading SELL block using realizable quantity.

    The returned rows and their quantities are never edited.  ``projected_shed``
    affects only the score used by the stable sort.  Passing ``None`` exactly
    reproduces the inherited requested-quantity valuation rule.
    """
    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market

    def drop(order):
        if len(order) < 3:
            return 0
        item = order[1]
        if item not in _RO_PARAMS:
            return 0
        try:
            level = int(inventory.get(item, _RO_I0))
            requested = max(0, int(order[2]))
        except (AttributeError, TypeError, ValueError, OverflowError):
            return 0
        quantity = _effective_quantity(item, requested, projected_shed)
        return (_ro_price(item, level) - _ro_price(item, level + quantity)) * quantity

    return sorted(market[:lead], key=drop, reverse=True) + market[lead:]
