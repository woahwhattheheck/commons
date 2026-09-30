# SPDX-License-Identifier: Apache-2.0
"""Market-prefix accounting for P21 terminal-route certificates."""
from collections.abc import Mapping
from copy import deepcopy
from terminal_route_value_primitives import positive


def sale_only(queue, limit):
    return all((not o) or (isinstance(o, list) and len(o) >= 3 and o[0] == "SELL"
                           and isinstance(o[1], str) and type(o[2]) is int and o[2] > 0)
               for o in list(queue)[:limit])


def append_after_commitments(queue, product, quantity, limit):
    """Fill executable trailing slack while preserving every inactive tail row."""
    inherited = deepcopy(list(queue)); prefix = inherited[:limit]
    last = max((i for i, order in enumerate(prefix) if order), default=-1)
    for slot in range(last + 1, limit):
        if slot < len(inherited):
            if inherited[slot]:
                continue
            out = deepcopy(inherited); out[slot] = ["SELL", product, quantity]
            return out, slot
        if len(inherited) < limit:
            out = deepcopy(inherited)
            while len(out) < slot:
                out.append([])
            out.append(["SELL", product, quantity])
            return out, slot
    return None, None


def quiet_sale_receipts(mechanics, market, shed, queue, limit):
    """Exact unitwise own receipts for an executable SELL-only prefix, quiet rival."""
    if not isinstance(market, Mapping) or not isinstance(market.get("inventory"), Mapping):
        raise ValueError("public market inventory is required")
    if not sale_only(queue, limit):
        return None
    stock = dict(positive(shed))
    inventory = {k: v for k, v in market["inventory"].items() if type(v) is int and v >= 0}
    cash = 0; filled = {}
    for order in list(queue)[:limit]:
        if not order:
            continue
        product, requested = order[1], order[2]
        quantity = min(requested, stock.get(product, 0)); sold = 0
        for _ in range(quantity):
            if product not in inventory:
                return None
            price = int(mechanics.market_price(product, inventory[product], market.get("params")))
            if price < 1:
                return None
            cash += price; stock[product] -= 1; sold += 1
            if price > 1:
                inventory[product] += 1
        filled[product] = filled.get(product, 0) + sold
    return {"cash": cash, "shed": stock, "market_inventory": inventory, "filled": filled}
