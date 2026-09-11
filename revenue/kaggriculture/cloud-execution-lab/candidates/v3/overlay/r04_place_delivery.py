# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed. The engine accepts only remaining capacity and destroys DROP overflow.
PLACE is capacity-bounded without destroying the worker's unplaced cargo. This
lane is shipped off as ``r04_place_delivery``.

The V4 seam is defensive, not a terminal product-mix optimizer. When enabled,
it may replace terminal shed-adjacent DROP rows only on true overflow and only
when the rewritten unit actions project to the *exact same shed contents* as the
parent action. The parent market vector is preserved verbatim. Therefore the
terminal SELL rows, raw market indices, quantities, public-market trajectory,
and own cash path are unchanged even against arbitrary hidden rival orders; the
only possible difference is overflow cargo remaining on a worker instead of
being destroyed after the last useful callback. Any ambiguous or malformed
state fails closed to the exact parent action.
"""
from __future__ import annotations


def _positive_plain_int(value):
    return type(value) is int and value > 0


def _valid_stock(stock):
    return isinstance(stock, dict) and all(
        type(quantity) is int and quantity >= 0 for quantity in stock.values()
    )


def apply_place_delivery(observation, action, enabled=False):
    if not enabled:
        return action
    if not isinstance(observation, dict) or type(observation.get("step")) is not int:
        return action
    if observation.get("step") != 718 or not isinstance(action, dict):
        return action

    import r04_full_router as r04

    private = observation.get("private")
    raw_shed = private.get("shed") if isinstance(private, dict) else None
    if not isinstance(raw_shed, dict):
        return action
    if any(type(quantity) is not int or quantity < 0 for quantity in raw_shed.values()):
        return action
    try:
        view = r04.FarmView(observation)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action

    # Parent actions are positional: one farmer command plus exactly one command
    # per hand. Missing/partial vectors are ambiguous and must not be padded or
    # silently truncated before a destructive DROP rewrite. Preserve the final
    # market vector exactly; PLACE is not allowed to reorder or rebuild it.
    raw_farmer = action.get("farmer")
    raw_hands = action.get("hands")
    raw_market = action.get("market")
    if (not isinstance(raw_farmer, list) or not isinstance(raw_hands, list)
            or not isinstance(raw_market, list)):
        return action
    workers = [raw_farmer, *raw_hands]

    # Validate all public geometry/inventory surfaces before the transform uses
    # them. The standard engine is 10x10 and all actor coordinates are in-bounds.
    if (not isinstance(view.tiles, list) or not isinstance(view.positions, list)
            or not isinstance(view.inventories, list)):
        return action
    if len(view.tiles) != 10 or any(not isinstance(row, list) or len(row) != 10
                                    for row in view.tiles):
        return action
    if len(view.positions) != len(workers) or len(view.inventories) != len(workers):
        return action
    for position in view.positions:
        if (not isinstance(position, (list, tuple)) or len(position) != 2
                or type(position[0]) is not int or type(position[1]) is not int):
            return action
        x, y = position
        if not (0 <= x < 10 and 0 <= y < 10):
            return action

    # Preserve baseline DROP semantics unless there is actual capacity overflow.
    # Track touched sellable products so any price used for candidate selection is
    # a strict public integer; no malformed price is coerced into a choice.
    payload = 0
    has_drop = False
    sellable_drop_kinds = set()
    touched_products = {
        item for item, quantity in raw_shed.items()
        if item in r04.PRODUCTS and quantity > 0
    }
    for worker in range(len(workers)):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue
        inventory = view.inventory(worker)
        if not isinstance(inventory, dict):
            return action
        for item, held in inventory.items():
            if type(held) is not int or held < 0:
                return action
            payload += held
            if item in r04.PRODUCTS and held > 0:
                touched_products.add(item)
                sellable_drop_kinds.add(item)
        has_drop = True

    if not has_drop:
        return action
    remaining = max(0, int(r04.SHED_CAPACITY) - sum(raw_shed.values()))
    if payload <= remaining:
        return action

    # Different product kinds have different nonlinear quote curves. Current spot
    # price is not a cash-monotone way to reallocate scarce final shed capacity.
    # This early guard avoids proposing known-mix changes; exact projected-shed
    # equality below remains the authoritative invariant for every candidate.
    if len(sellable_drop_kinds) > 1:
        return action

    if not isinstance(view.prices, dict):
        return action
    for item in touched_products:
        price = view.prices.get(item)
        if type(price) is not int or price < 0:
            return action

    try:
        parent_stock = r04.projected_shed(action, view)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
    if not _valid_stock(parent_stock):
        return action

    eligible = []
    for worker in range(len(workers)):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue
        inventory = view.inventory(worker)
        if not isinstance(inventory, dict):
            return action
        choices = []
        for item, held in inventory.items():
            if item not in r04.PRODUCTS or not _positive_plain_int(held):
                continue
            price = view.prices[item]
            product_order = r04.PRODUCTS.index(item)
            choices.append((price, held, -product_order, item))
        if choices:
            price, held, _, item = max(choices)
            eligible.append((price, held, worker, item))

    # Start by removing every touched DROP. A safe PLACE is added only where it
    # can preserve the parent's projected shed exactly; otherwise the final
    # equality guard returns the untouched parent object.
    out_workers = [list(command) if isinstance(command, list) else command for command in workers]
    for worker in range(len(out_workers)):
        command = out_workers[worker]
        if (isinstance(command, list) and command and command[0] == "DROP"
                and view.beside_shed(view.positions[worker])):
            out_workers[worker] = ["PASS"]

    remaining = max(0, int(r04.SHED_CAPACITY) - sum(raw_shed.values()))
    eligible.sort(key=lambda row: (-row[0], row[2], row[3]))
    for _, held, worker, item in eligible:
        if remaining <= 0:
            break
        quantity = min(held, remaining)
        if quantity <= 0:
            continue
        out_workers[worker] = ["PLACE", item, quantity]
        remaining -= quantity

    out = dict(action)
    out["farmer"] = out_workers[0]
    out["hands"] = out_workers[1:]

    try:
        candidate_stock = r04.projected_shed(out, view)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
    if not _valid_stock(candidate_stock):
        return action

    # This is the safety theorem. Identical projected shed means the exact parent
    # market vector can be reused unchanged. No product mix, quantity, raw row,
    # or hidden-rival lockstep path is changed by the unit-action substitution.
    if candidate_stock != parent_stock:
        return action
    out["market"] = raw_market
    return out
