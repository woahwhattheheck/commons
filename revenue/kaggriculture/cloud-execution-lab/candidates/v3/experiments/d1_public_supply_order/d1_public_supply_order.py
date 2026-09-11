# SPDX-License-Identifier: Apache-2.0
"""D1 experiment: prioritize already-returned SELL rows exposed to public rival supply.

This module is intentionally narrower than a price predictor.  It reads only the public
`farms` projection in the observation and treats standing rival tile `yield_units` as a
bounded supply-pressure signal.  It never reads rival private shed/inventory/order state,
never creates or changes a quantity, and never moves a sale across turns.

The only eligible mutation is a stable partition of the *leading* SELL block in the
parent's final market action: products with visible rival standing yield move before
products with no such signal, while parent order is retained within both groups.  The
Kaggriculture interpreter executes market rows index-by-index, so this is the smallest
row-position experiment that can test Muse D1 without repeating broad sale-timing arms.
"""

from __future__ import annotations

from typing import Any


_ANIMAL_PRODUCTS = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}

REPORT = {
    "calls": 0,
    "activations": 0,
    "rows_moved": 0,
    "visible_signal_units": 0,
    "signal_products": {},
}


def _strict_nonnegative_int(value: Any) -> int | None:
    """Accept only real integer public counters; bool/string/float are unknown."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def public_rival_supply(observation: Any) -> dict[str, int]:
    """Return visible standing yield by product for the one rival, or {} fail-closed.

    `farms[*].tiles[*][*]` is public in the pinned official interpreter.  Private shed,
    per-worker inventory, seeds and market orders are deliberately outside this helper.
    A malformed tile/counter contributes nothing rather than being coerced.
    """
    if not isinstance(observation, dict):
        return {}
    farms = observation.get("farms")
    player = observation.get("player")
    if (not isinstance(farms, list) or len(farms) != 2
            or isinstance(player, bool) or not isinstance(player, int) or player not in (0, 1)):
        return {}
    rival = farms[1 - player]
    if not isinstance(rival, dict):
        return {}
    tiles = rival.get("tiles")
    if not isinstance(tiles, list):
        return {}

    result: dict[str, int] = {}
    for row in tiles:
        if not isinstance(row, list):
            continue
        for tile in row:
            if not isinstance(tile, dict):
                continue
            units = _strict_nonnegative_int(tile.get("yield_units"))
            if not units:
                continue
            product = None
            if tile.get("kind") == "PLANT" and isinstance(tile.get("crop"), str):
                product = tile["crop"]
            elif isinstance(tile.get("animal"), str):
                product = _ANIMAL_PRODUCTS.get(tile["animal"])
            if product:
                result[product] = result.get(product, 0) + units
    return result


def _eligible_sell(row: Any) -> bool:
    if not isinstance(row, list) or len(row) < 3 or row[0] != "SELL":
        return False
    quantity = row[2]
    return not isinstance(quantity, bool) and isinstance(quantity, int) and quantity > 0


def apply_public_supply_order(
    observation: Any,
    action: Any,
    configuration: Any = None,
    *,
    enabled: bool = True,
) -> Any:
    """Stable-partition the leading SELL block by visible rival standing supply.

    Disabled or unsupported inputs return the exact same parent object.  Custom market
    parameters also fail closed so this experiment stays on the exact live V3.1 market
    contract.  Every row object, quantity, tail position and non-market action is retained.
    """
    REPORT["calls"] += 1
    if not enabled or not isinstance(action, dict):
        return action
    if isinstance(configuration, dict) and configuration.get("marketParams"):
        return action
    market = action.get("market")
    if not isinstance(market, list):
        return action

    lead = 0
    while lead < len(market) and _eligible_sell(market[lead]):
        lead += 1
    if lead < 2:
        return action

    signal = public_rival_supply(observation)
    if not signal:
        return action
    leading = market[:lead]
    pressured = [row for row in leading if signal.get(row[1], 0) > 0]
    quiet = [row for row in leading if signal.get(row[1], 0) <= 0]
    ordered = pressured + quiet
    if ordered == leading:
        return action

    changed = dict(action)
    changed["market"] = ordered + market[lead:]
    REPORT["activations"] += 1
    REPORT["rows_moved"] += sum(a is not b for a, b in zip(leading, ordered))
    activated_products = {row[1] for row in pressured}
    REPORT["visible_signal_units"] += sum(signal.get(item, 0) for item in activated_products)
    counts = REPORT["signal_products"]
    for item in activated_products:
        counts[item] = counts.get(item, 0) + 1
    return changed
