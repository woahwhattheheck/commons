# SPDX-License-Identifier: Apache-2.0
"""S33 row-shed donor for the current V3.1 R04 router.

This module is intentionally experiment-only. It carries the narrow mechanism needed
for a production recompose after the current R04/L3 writer settles:

* only the contiguous leading SELL block is eligible;
* emitted SELL quantities are never changed;
* ranking uses min(requested quantity, projected shed stock) instead of the tape's raw
  request, so a 1000-unit availability dump is scored by what can actually execute;
* rows after the first non-SELL barrier and empty market slots are untouched;
* missing/malformed projection evidence falls back coherently to incumbent requested-
  quantity ROW_ORDER for the whole leading block, never a hybrid ranking.

The caller supplies the canonical R04 price function and parameter membership. That
keeps this donor independent of a stale copy of the market curves while making the exact
row-shed transform unit-testable.
"""


def _strict_nonnegative_int(value):
    return type(value) is int and value >= 0


def effective_quantity(order, projected_shed):
    """Return the realizable quantity for one known SELL row, or None on ambiguity."""
    if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
        return None
    item = order[1]
    quantity = order[2]
    if not isinstance(item, str) or not _strict_nonnegative_int(quantity):
        return None
    if type(projected_shed) is not dict or item not in projected_shed:
        return None
    available = projected_shed[item]
    if not _strict_nonnegative_int(available):
        return None
    return min(quantity, available)


def _projection_is_complete(market, lead, projected_shed, known_items):
    """Require coherent projection evidence for every known leading SELL row."""
    if type(projected_shed) is not dict:
        return False
    for order in market[:lead]:
        if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
            return False
        item = order[1]
        if item not in known_items:
            continue
        if not _strict_nonnegative_int(order[2]):
            return False
        available = projected_shed.get(item)
        if not _strict_nonnegative_int(available):
            return False
    return True


def order_sells(market, inventory, projected_shed, price_fn, known_items, inventory_default=10000):
    """Stable-sort the leading SELL block by row price impact.

    With a complete projected-shed map, known rows use realizable quantity. If any known
    leading row lacks valid projection evidence, the *entire* block falls back to incumbent
    requested-quantity scoring. This prevents a partial/type-poisoned projection from
    creating a hybrid order that neither S33 nor incumbent ROW_ORDER authorized.
    """
    if not isinstance(market, list) or not isinstance(inventory, dict):
        return market

    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market

    use_projection = _projection_is_complete(market, lead, projected_shed, known_items)
    ranked = []
    for index, order in enumerate(market[:lead]):
        if not isinstance(order, list) or len(order) < 3:
            return market
        item = order[1]
        if item not in known_items:
            # Match incumbent ROW_ORDER: unknown products get a zero score.
            score = 0
        else:
            requested = order[2]
            if not _strict_nonnegative_int(requested):
                # Bad authored quantity has no new row-shed authority. Preserve raw parent
                # order rather than inventing a coercion policy in this donor.
                return market
            quantity = min(requested, projected_shed[item]) if use_projection else requested
            level = inventory.get(item, inventory_default)
            if type(level) is not int:
                return market
            score = (price_fn(item, level) - price_fn(item, level + quantity)) * quantity
        ranked.append((score, index, order))

    # Python's sort is stable: equal-score rows retain incumbent relative order.
    ranked.sort(key=lambda row: row[0], reverse=True)
    return [row[2] for row in ranked] + market[lead:]


def apply_row_shed(observation, action, r04, configuration=None):
    """Apply only the row-shed ranking transform to an already-produced R04 action.

    This function is the exact handoff seam for a later production port. It does not call
    or reinstall the router, does not change feature globals, and does not touch workers or
    market quantities. As in incumbent ROW_ORDER, a non-empty explicit custom marketParams
    override disables the transform. Malformed configuration fails closed to the exact
    parent action instead of being coerced into a new configuration policy.
    """
    if configuration is None:
        config = {}
    elif not isinstance(configuration, dict):
        return action
    else:
        config = configuration
    market_params = config.get("marketParams")
    if market_params is not None and not isinstance(market_params, dict):
        return action
    if market_params:
        return action
    try:
        view = r04.FarmView(observation)
        projected = r04.projected_shed(action, view)
        inventory = (observation.get("market") or {}).get("inventory") or {}
        # Empty market rows are execution positions. Do not compact them: doing so can move
        # a later row into the engine's executable prefix. order_sells() changes only the
        # contiguous leading SELL positions and preserves every tail slot/object.
        market = action.get("market") or []
        ordered = order_sells(market, inventory, projected, r04._ro_price, r04._RO_PARAMS, r04._RO_I0)
    except Exception:
        return action
    if ordered == market:
        return action
    result = dict(action)
    result["market"] = ordered
    return result
