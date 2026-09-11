# SPDX-License-Identifier: Apache-2.0
"""V4 PLACE-safe terminal shed delivery.

The published R04 final-turn liquidator uses DROP for every loaded worker beside
the shed.  The engine accepts only the remaining capacity and destroys the rest
of a DROP payload.  PLACE is capacity-bounded without destroying the worker's
unplaced cargo.  This lane is shipped off as ``r04_place_delivery``.

When enabled, only terminal-step DROP actions beside the shed are touched.  The
transform chooses at most one product per worker, gives scarce shed capacity to
the highest public-price cargo first, converts accepted cargo to explicit PLACE,
and turns the remaining DROP actions into PASS.  It then recomputes terminal SELL
rows from the projected shed.  Disabled and non-terminal calls return the exact
parent action object.
"""
from __future__ import annotations


def _positive_plain_int(value):
    return type(value) is int and value > 0


def apply_place_delivery(observation, action, enabled=False):
    if not enabled or int(observation.get("step", -1)) != 718:
        return action

    import r04_full_router as r04

    view = r04.FarmView(observation)
    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    eligible = []
    for worker in range(min(len(workers), len(view.positions))):
        command = workers[worker]
        if not (isinstance(command, list) and command and command[0] == "DROP"):
            continue
        if not view.beside_shed(view.positions[worker]):
            continue
        inventory = view.inventory(worker)
        if not isinstance(inventory, dict):
            continue
        choices = []
        for item, held in inventory.items():
            if item in r04.ANIMALS or not _positive_plain_int(held):
                continue
            price = view.prices.get(item, 0)
            if type(price) is not int:
                try:
                    price = int(price)
                except (TypeError, ValueError):
                    price = 0
            try:
                product_order = r04.PRODUCTS.index(item)
            except ValueError:
                product_order = len(r04.PRODUCTS)
            choices.append((int(price), int(held), -product_order, item))
        if choices:
            price, held, _, item = max(choices)
            eligible.append((price, held, worker, item))

    # Every terminal DROP is removed even if there is no safe capacity or no
    # recognized product.  Cargo left on a worker is preserved instead of lost.
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
