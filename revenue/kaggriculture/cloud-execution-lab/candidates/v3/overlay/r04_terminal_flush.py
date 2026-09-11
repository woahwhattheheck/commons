# SPDX-License-Identifier: Apache-2.0
"""Experimental R04 final-day market flush for TITAN V3.1.

This lane is deliberately *not* wired into the submission/runtime. Importing it
has no effect. A caller must explicitly wrap an already-configured R04 host with
``install(host)``.

The candidate begins at step 698, matching the previously frozen terminal-routing
study's final-day intervention boundary. It only changes market rows: farmer and
hand actions are preserved byte-for-byte. Existing SELL quantities are never
duplicated, the market-order cap is respected, and R04 keeps ownership of the
last-step liquidation.
"""
from __future__ import annotations

import r04_full_router as r04

TERMINAL_START = 698
TERMINAL_END = r04.LAST_STEP - 1
MIN_PRICE = 2
FLUSH_ITEMS = tuple(r04.FLUSH_ITEMS)


def terminal_flush(observation, action, *, start=TERMINAL_START):
    """Sell eligible projected shed stock during the bounded final-day window."""
    step = int(observation["step"])
    if step < int(start) or step >= r04.LAST_STEP:
        return action

    market = [list(order) for order in (action.get("market") or [])]
    if len(market) >= r04.MAX_ORDERS:
        return action

    view = r04.FarmView(observation)
    stock = r04.projected_shed(action, view)
    selling = {}
    for order in market:
        if order and order[0] == "SELL" and len(order) >= 3:
            item = order[1]
            selling[item] = selling.get(item, 0) + max(0, int(order[2]))

    extra = []
    for item in FLUSH_ITEMS:
        quantity = max(0, int(stock.get(item, 0)) - selling.get(item, 0))
        if quantity <= 0 or int(view.prices.get(item, 0)) < MIN_PRICE:
            continue
        extra.append(["SELL", item, quantity])

    room = r04.MAX_ORDERS - len(market)
    if not extra or room <= 0:
        return action

    extra.sort(
        key=lambda order: (
            -int(view.prices.get(order[1], 0)) * int(order[2]),
            order[1],
        )
    )
    out = dict(action)
    out["market"] = extra[:room] + market
    return out


def install(host, *, start=TERMINAL_START):
    """Explicitly wrap an installed R04 callable; there is no module-level activation."""
    if host is None or not callable(host):
        raise TypeError("host must be a callable installed R04 agent")
    start = int(start)
    if start < 0 or start >= r04.LAST_STEP:
        raise ValueError("terminal flush start must be in [0, LAST_STEP)")

    def wrapped(observation, configuration=None):
        parent = host(observation, configuration)
        return terminal_flush(observation, parent, start=start)

    return wrapped
