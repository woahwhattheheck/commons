# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed.  The engine accepts only the remaining capacity and destroys the rest
of a DROP payload.  PLACE is capacity-bounded without destroying the worker's
unplaced cargo.  This lane is shipped off as ``r04_place_delivery``.

When enabled, terminal-step DROP actions beside the shed are changed only when
their combined payload would overflow the remaining shed capacity.  If every
payload fits, the exact parent action is returned so normal DROP behavior,
including multi-product cargo, stays untouched.  Overflow also fails closed when
one worker carries multiple sellable products: the engine permits only one PLACE
command per worker, so rewriting that DROP could leave profitable shed capacity
unused.  Otherwise scarce capacity goes to the highest public-price cargo first
and excess cargo stays on workers.  Malformed terminal step/shed/inventory/
price/position/board state fails closed to the parent action.
"""
from __future__ import annotations


def _positive_plain_int(value):
    return type(value) is int and value > 0


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
    # silently truncated before a destructive DROP rewrite.
    raw_farmer = action.get("farmer")
    raw_hands = action.get("hands")
    if not isinstance(raw_farmer, list) or not isinstance(raw_hands, list):
        return action
    workers = [raw_farmer, *raw_hands]

    # Validate the public geometry/inventory surfaces used by beside_shed() and
    # inventory() before the transform touches them. beside_shed() derives the
    # shed center from len(tiles), so malformed board dimensions must not be
    # allowed to redefine shed adjacency. Exact actor cardinality is required in
    # both directions: neither the public state nor the parent action may expose
    # only a prefix of the actual worker set.
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

    # Preserve baseline DROP semantics unless an actual capacity overflow exists.
    # A worker with >1 positive sellable product is also fail-closed on overflow:
    # one unit action can PLACE only one product, while DROP can fill room from
    # multiple inventory rows. Rewriting such a worker can therefore lower the
    # final-turn liquidation value by leaving capacity unused.
    payload = 0
    has_drop = False
    multi_sellable_drop = False
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
        sellable_kinds = 0
        for item, held in inventory.items():
            if type(held) is not int or held < 0:
                return action
            payload += held
            if item in r04.PRODUCTS and held > 0:
                touched_products.add(item)
                sellable_kinds += 1
        if sellable_kinds > 1:
            multi_sellable_drop = True
        has_drop = True
    if has_drop:
        remaining = max(0, int(r04.SHED_CAPACITY) - sum(raw_shed.values()))
        if payload <= remaining:
            return action
        if multi_sellable_drop:
            return action

    # Overflow rewriting reprices PLACE priority and rebuilds terminal SELLs.
    # Validate every sellable product that can participate; never coerce a
    # malformed public price into a different cargo choice or sale order.
    if not isinstance(view.prices, dict):
        return action
    for item in touched_products:
        price = view.prices.get(item)
        if type(price) is not int or price < 0:
            return action

    eligible = []
    touched = False
    for worker in range(len(workers)):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue
        touched = True
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

    if not touched:
        return action

    # Every shed-adjacent terminal DROP is removed even when there is no safe
    # capacity or recognized product. Cargo left on a worker is preserved.
    out_workers = [list(command) if isinstance(command, list) else command for command in workers]
    for worker in range(len(out_workers)):
        command = out_workers[worker]
        if (isinstance(command, list) and command and command[0] == "DROP"
                and view.beside_shed(view.positions[worker])):
            out_workers[worker] = ["PASS"]

    used = sum(raw_shed.values())
    remaining = max(0, int(r04.SHED_CAPACITY) - used)
    # Public value first; stable worker index breaks equal-value ties.
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
        stock = r04.projected_shed(out, view)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
    if not isinstance(stock, dict):
        return action
    market = []
    for item in r04.PRODUCTS:
        quantity = stock.get(item, 0)
        if type(quantity) is not int or quantity < 0:
            return action
        if quantity <= 0:
            continue
        price = view.prices.get(item)
        if type(price) is not int or price < 0:
            return action
        market.append(["SELL", item, quantity])
    market.sort(key=lambda order: -view.prices[order[1]] * order[2])
    out["market"] = market[: int(r04.MAX_ORDERS)]
    return out
