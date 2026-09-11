# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed. The engine accepts only the remaining capacity and destroys the rest
of a DROP payload. PLACE is capacity-bounded without destroying the worker's
unplaced cargo. This lane is shipped off as ``r04_place_delivery``.

When enabled, terminal-step DROP actions beside the shed are considered only
when their combined payload would overflow the remaining shed capacity. A
candidate PLACE rewrite is returned only when the official lightweight shed
projection is *exactly identical* to the parent DROP projection. This preserves
the terminal shed contents and the parent's market queue while allowing a
same-product overflow rewrite to leave otherwise-destroyed excess cargo on a
worker. Any rewrite that would change admitted product mix, quantity, unknown
cargo ordering, or other projected shed state fails closed to the exact parent.
Malformed terminal step/shed/inventory/price/position/board/action state also
fails closed to the parent action.
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
    # silently truncated before a destructive DROP rewrite. Preserve the parent
    # market queue byte-for-behavior: PLACE is only a unit-action repair.
    raw_farmer = action.get("farmer")
    raw_hands = action.get("hands")
    raw_market = action.get("market")
    if (not isinstance(raw_farmer, list) or not isinstance(raw_hands, list)
            or not isinstance(raw_market, list)):
        return action
    workers = [raw_farmer, *raw_hands]

    # Validate the public geometry/inventory surfaces used by beside_shed() and
    # inventory() before the transform touches them. beside_shed() derives the
    # shed center from len(tiles), so malformed board dimensions must not be
    # allowed to redefine shed adjacency. Exact actor cardinality is required in
    # both directions: neither the public state nor the parent action may expose
    # only a prefix of the actual worker set. Coordinates must also be in bounds;
    # otherwise a malformed sibling could be silently ignored while another
    # actor is rewritten.
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
                or type(position[0]) is not int or type(position[1]) is not int
                or not (0 <= position[0] < 10) or not (0 <= position[1] < 10)):
            return action

    # Preserve baseline DROP semantics unless an actual capacity overflow exists.
    payload = 0
    has_drop = False
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
        has_drop = True
    if not has_drop:
        return action
    remaining = max(0, int(r04.SHED_CAPACITY) - sum(raw_shed.values()))
    if payload <= remaining:
        return action

    # The parent projection is the safety oracle. It preserves worker order,
    # inventory insertion order, capacity clipping, and arbitrary shed keys.
    # Any candidate whose projected shed differs is not a defensive rewrite.
    try:
        parent_stock = r04.projected_shed(action, view)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError):
        return action
    if (not isinstance(parent_stock, dict)
            or any(type(quantity) is not int or quantity < 0
                   for quantity in parent_stock.values())):
        return action

    # Candidate selection may use public prices, but price priority is not a
    # correctness theorem: market SELLs are requoted per unit against evolving
    # shared inventory. The exact projected-shed equality below is authoritative.
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

    # Every shed-adjacent terminal DROP is removed in the candidate. Exact shed
    # equality decides whether that candidate is allowed to escape the function.
    # Cargo left on a worker is preserved instead of being destroyed by DROP.
    out_workers = [list(command) if isinstance(command, list) else command for command in workers]
    for worker in range(len(out_workers)):
        command = out_workers[worker]
        if (isinstance(command, list) and command and command[0] == "DROP"
                and view.beside_shed(view.positions[worker])):
            out_workers[worker] = ["PASS"]

    used = sum(raw_shed.values())
    remaining = max(0, int(r04.SHED_CAPACITY) - used)
    # Public value is only a deterministic proposal order. Any cross-product
    # reallocation that changes the projected shed is rejected below.
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
    if not isinstance(candidate_stock, dict) or candidate_stock != parent_stock:
        return action

    # The terminal market request is already derived from the parent projection.
    # Keeping it exactly unchanged makes the unit-action repair behaviorally
    # transparent to per-unit market repricing and rival lockstep execution.
    out["market"] = raw_market
    return out
