# SPDX-License-Identifier: Apache-2.0
"""S33 row-shed donor for the current V3.1 R04 router.

This module is intentionally experiment-only.  It carries the narrow mechanism needed
for a production recompose after the current R04/L3 writer settles:

* only the contiguous leading SELL block is eligible;
* emitted SELL quantities are never changed;
* ranking uses min(requested quantity, projected shed stock) instead of the tape's raw
  request, so a 1000-unit availability dump is scored by what can actually execute;
* rows after the first non-SELL barrier are untouched;
* malformed projected-stock evidence fails closed to the parent ordering.

The caller supplies the canonical R04 price function and parameter membership.  That
keeps this donor independent of a stale copy of the market curves while making the exact
row-shed transform unit-testable.
"""


def _strict_nonnegative_int(value):
    return type(value) is int and value >= 0


def effective_quantity(order, projected_shed):
    """Return the executable quantity used for ranking, or None on ambiguity."""
    if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
        return None
    item = order[1]
    quantity = order[2]
    if not isinstance(item, str) or not _strict_nonnegative_int(quantity):
        return None
    if not isinstance(projected_shed, dict) or item not in projected_shed:
        return None
    available = projected_shed[item]
    if not _strict_nonnegative_int(available):
        return None
    return min(quantity, available)


def order_sells(market, inventory, projected_shed, price_fn, known_items, inventory_default=10000):
    """Stable-sort the leading SELL block by executable row price impact.

    ``price_fn(item, inventory_level)`` is the canonical R04 ``_ro_price`` callable and
    ``known_items`` is its canonical parameter membership.  Returning ``market`` itself on
    malformed row/shed evidence is deliberate: the donor never manufactures authority from
    an ambiguous private-state projection.
    """
    if not isinstance(market, list) or not isinstance(inventory, dict):
        return market

    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market

    ranked = []
    for index, order in enumerate(market[:lead]):
        if not isinstance(order, list) or len(order) < 3:
            return market
        item = order[1]
        if item not in known_items:
            # Match incumbent ROW_ORDER's zero-score behavior for an unknown product rather
            # than letting private-state data create a new ordering claim.
            score = 0
        else:
            quantity = effective_quantity(order, projected_shed)
            if quantity is None:
                return market
            level = inventory.get(item, inventory_default)
            if type(level) is not int:
                return market
            score = (price_fn(item, level) - price_fn(item, level + quantity)) * quantity
        ranked.append((score, index, order))

    # Python's sort is stable: equal-score rows retain incumbent relative order.
    ranked.sort(key=lambda row: row[0], reverse=True)
    ordered = [row[2] for row in ranked] + market[lead:]
    return ordered


def apply_row_shed(observation, action, r04, configuration=None):
    """Apply only the row-shed ranking transform to an already-produced R04 action.

    This function is the exact handoff seam for a later production port.  It does not call
    or reinstall the router, does not change feature globals, and does not touch workers or
    market quantities.  As in incumbent ROW_ORDER, any explicit custom marketParams override
    disables the transform.
    """
    if (configuration or {}).get("marketParams") or {}:
        return action
    try:
        view = r04.FarmView(observation)
        projected = r04.projected_shed(action, view)
        inventory = (observation.get("market") or {}).get("inventory") or {}
        # Keep the exact market row cardinality and tail objects. Empty slots are execution
        # positions, not disposable representation: compacting them can move later rows into
        # the engine's executable prefix. order_sells() itself only replaces the leading
        # contiguous SELL positions when the ranking changes.
        market = action.get("market") or []
        ordered = order_sells(market, inventory, projected, r04._ro_price, r04._RO_PARAMS, r04._RO_I0)
    except Exception:
        return action
    if ordered == market:
        return action
    result = dict(action)
    result["market"] = ordered
    return result
