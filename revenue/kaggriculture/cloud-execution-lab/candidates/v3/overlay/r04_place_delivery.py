# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed. The engine accepts only the remaining capacity and destroys DROP
overflow. PLACE is capacity-bounded without destroying the worker's unplaced
cargo. This lane is shipped off as ``r04_place_delivery``.

The transform is deliberately minimal: if every shed-adjacent DROP payload fits
in the remaining shed capacity, return the exact parent action so normal DROP
semantics (including multi-product cargo) stay untouched. Only an actual
overflow risk is rewritten. In that case, qualifying DROP actions become
capacity-bounded PLACE/PASS actions, scarce capacity goes to the highest public
price cargo first, and terminal SELL rows are recomputed from projected shed
stock. Any malformed or ambiguous state fails closed to the exact parent action.
"""

from __future__ import annotations


def _plain_nonnegative_int(value):
    return type(value) is int and value >= 0


def _plain_positive_int(value):
    return type(value) is int and value > 0


def _apply_place_delivery(observation, action):
    import r04_full_router as r04

    private = observation.get("private")
    if not isinstance(private, dict):
        return action
    raw_shed = private.get("shed")
    if not isinstance(raw_shed, dict):
        return action
    if any(not _plain_nonnegative_int(quantity) for quantity in raw_shed.values()):
        return action

    view = r04.FarmView(observation)
    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    touched = []
    total_payload = 0

    for worker in range(min(len(workers), len(view.positions))):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue

        inventory = view.inventory(worker)
        if not isinstance(inventory, dict):
            return action
        payload = 0
        for held in inventory.values():
            if not _plain_nonnegative_int(held):
                return action
            payload += held
        touched.append((worker, inventory))
        total_payload += payload

    if not touched:
        return action

    used = sum(raw_shed.values())
    capacity = r04.SHED_CAPACITY
    if not _plain_nonnegative_int(capacity):
        return action
    remaining = max(0, capacity - used)

    # DROP is safe and strictly more faithful whenever every payload fits.
    # Preserve the exact parent object, including multi-product DROP semantics.
    if total_payload <= remaining:
        return action

    eligible = []
    for worker, inventory in touched:
        choices = []
        for item, held in inventory.items():
            if item not in r04.PRODUCTS or not _plain_positive_int(held):
                continue
            price = view.prices.get(item)
            if type(price) is not int:
                return action
            product_order = r04.PRODUCTS.index(item)
            choices.append((price, held, -product_order, item))
        if choices:
            price, held, _, item = max(choices)
            eligible.append((price, held, worker, item))

    out_workers = [
        list(command) if isinstance(command, list) else command for command in workers
    ]
    for worker, _inventory in touched:
        out_workers[worker] = ["PASS"]

    # Public value first; stable worker index and product name break equal-value ties.
    eligible.sort(key=lambda row: (-row[0], row[2], row[3]))
    for _price, held, worker, item in eligible:
        if remaining <= 0:
            break
        quantity = min(held, remaining)
        if quantity <= 0:
            continue
        out_workers[worker] = ["PLACE", item, quantity]
        remaining -= quantity

    out = dict(action)
    out["farmer"] = out_workers[0] if out_workers else ["PASS"]
    out["hands"] = out_workers[1:]

    stock = r04.projected_shed(out, view)
    if not isinstance(stock, dict):
        return action
    market = []
    for item in r04.PRODUCTS:
        quantity = stock.get(item, 0)
        if not _plain_nonnegative_int(quantity):
            return action
        if quantity <= 0:
            continue
        price = view.prices.get(item)
        if type(price) is not int:
            return action
        market.append(["SELL", item, quantity])
    market.sort(key=lambda order: -view.prices[order[1]] * order[2])
    out["market"] = market[: r04.MAX_ORDERS]
    return out


def apply_place_delivery(observation, action, enabled=False):
    if not enabled:
        return action
    if not isinstance(observation, dict) or type(observation.get("step")) is not int:
        return action
    if observation.get("step") != 718 or not isinstance(action, dict):
        return action
    try:
        return _apply_place_delivery(observation, action)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
