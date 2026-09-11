# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed.  The engine accepts only the remaining capacity and destroys the rest
of a DROP payload.  PLACE is capacity-bounded without destroying the worker's
unplaced cargo.  This lane is shipped off as ``r04_place_delivery``.

When enabled, terminal-step DROP actions beside the shed are changed only when
their combined payload would overflow the remaining shed capacity.  If every
payload fits, the exact parent action is returned so normal DROP behavior,
including multi-product cargo, stays untouched.  On overflow, scarce capacity
goes to the highest public-price cargo first and excess cargo stays on workers.
Malformed terminal step/shed/inventory/price state fails closed to the parent
action.
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

    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]

    # Preserve baseline DROP semantics unless an actual capacity overflow exists.
    payload = 0
    has_drop = False
    touched_products = {
        item for item, quantity in raw_shed.items()
        if item in r04.PRODUCTS and quantity > 0
    }
    for worker in range(min(len(workers), len(view.positions))):
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
        has_drop = True
    if has_drop:
        remaining = max(0, int(r04.SHED_CAPACITY) - sum(raw_shed.values()))
        if payload <= remaining:
            return action

    # Overflow rewriting recomputes terminal SELLs and prioritizes PLACE cargo by
    # public price.  Do not coerce malformed prices into a different policy.
    if not isinstance(view.prices, dict):
        return action
    for item in touched_products:
        if type(view.prices.get(item)) is not int:
            return action

    eligible = []
    touched = False
    for worker in range(min(len(workers), len(view.positions))):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue
        touched = True
        inventory = view.inventory(worker)
        if not isinstance(inventory, dict):
            continue
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
    for worker in range(min(len(out_workers), len(view.positions))):
        command = out_workers[worker]
        if (isinstance(command, list) and command and command[0] == "DROP"
                and view.beside_shed(view.positions[worker])):
            out_workers[worker] = ["PASS"]

    used = sum(max(0, int(quantity)) for quantity in view.shed.values())
    remaining = max(0, int(r04.SHED_CAPACITY) - used)
    # Public value first; stable worker index breaks equal-value ties.
    eligible.sort(key=lambda row: (-row[0], row[2], row[3]))
    for _, held, worker, item in eligible:
        if remaining <= 0:
            break
        quantity = min(int(held), remaining)
        if quantity <= 0:
            continue
        out_workers[worker] = ["PLACE", item, quantity]
        remaining -= quantity

    out = dict(action)
    out["farmer"] = out_workers[0] if out_workers else ["PASS"]
    out["hands"] = out_workers[1:]

    stock = r04.projected_shed(out, view)
    market = [["SELL", item, stock[item]] for item in r04.PRODUCTS if int(stock.get(item, 0)) > 0]
    market.sort(key=lambda order: -int(view.prices.get(order[1], 0)) * int(order[2]))
    out["market"] = market[: int(r04.MAX_ORDERS)]
    return out
