# SPDX-License-Identifier: Apache-2.0
"""D1 experiment: prioritize already-returned SELL rows exposed to public rival supply.

This module is intentionally narrower than a price predictor. It reads only the public
``farms`` projection in the observation and treats standing rival tile ``yield_units``
as a bounded supply-pressure signal. It never reads rival private shed/inventory/order
state, never creates or changes a quantity, and never moves a sale across turns.

The only eligible mutation is a stable partition of the *leading* SELL block in the
parent's final market action: products with visible rival standing yield move before
products with no such signal, while parent order is retained within both groups.
Malformed evidence invalidates the whole signal rather than being partially trusted.
"""

from __future__ import annotations

from typing import Any


_CROP_PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
_ANIMAL_PRODUCTS = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
_ANIMAL_STRUCTURES = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
_PRODUCTS = _CROP_PRODUCTS | set(_ANIMAL_PRODUCTS.values()) | {"FERTILIZER"}
_BOARD_SIZE = 10

REPORT = {
    "calls": 0,
    "activations": 0,
    "rows_moved": 0,
    "visible_signal_units": 0,
    "signal_products": {},
}


def _strict_nonnegative_int(value: Any) -> int | None:
    """Accept only exact JSON integers; bool/string/float/subclasses are unknown."""
    if type(value) is not int or value < 0:
        return None
    return value


def public_rival_supply(observation: Any) -> dict[str, int]:
    """Return visible standing rival yield, or ``{}`` if evidence is invalid/absent.

    A structurally malformed rival board is never partially trusted. The frozen V3.1
    theorem uses the standard 10x10 board, so truncated/ragged/nonstandard board shapes
    are ambiguous and fail closed before any producing tile can authorize a reorder.
    Normal locked/empty cells and non-producing well-formed tiles contribute no signal.
    A PLANT or occupied animal structure must carry an exact known crop/animal, legal
    structure kind, and nonnegative integer ``yield_units``; otherwise the entire public
    signal fails closed.
    """
    if type(observation) is not dict:
        return {}
    farms = observation.get("farms")
    player = observation.get("player")
    if type(farms) is not list or len(farms) != 2 or type(player) is not int or player not in (0, 1):
        return {}
    rival = farms[1 - player]
    if type(rival) is not dict:
        return {}
    tiles = rival.get("tiles")
    if type(tiles) is not list or len(tiles) != _BOARD_SIZE:
        return {}

    result: dict[str, int] = {}
    for row in tiles:
        if type(row) is not list or len(row) != _BOARD_SIZE:
            return {}
        for tile in row:
            # Locked/empty cells are non-signals, not malformed producing evidence.
            if tile is None or tile == "LOCKED":
                continue
            if type(tile) is not dict:
                return {}

            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile.get("crop")
                units = _strict_nonnegative_int(tile.get("yield_units"))
                if type(crop) is not str or crop not in _CROP_PRODUCTS or units is None:
                    return {}
                if units:
                    result[crop] = result.get(crop, 0) + units
                continue

            animal = tile.get("animal")
            if animal is not None:
                if type(animal) is not str or animal not in _ANIMAL_PRODUCTS:
                    return {}
                if kind != _ANIMAL_STRUCTURES[animal]:
                    return {}
                units = _strict_nonnegative_int(tile.get("yield_units"))
                if units is None:
                    return {}
                if units:
                    product = _ANIMAL_PRODUCTS[animal]
                    result[product] = result.get(product, 0) + units
                continue

            # Only official non-producing tile shapes are admissible evidence.
            # Unknown/missing kinds or a crop attached to a non-PLANT tile make the
            # whole public board ambiguous rather than being silently ignored.
            if kind not in ("WEED", "COOP", "PASTURE"):
                return {}
            if tile.get("crop") is not None:
                return {}
    return result


def _eligible_sell(row: Any) -> bool:
    """Accept only an executable-looking SELL row with a known exact product key."""
    if type(row) is not list or len(row) < 3 or row[0] != "SELL":
        return False
    product = row[1]
    quantity = row[2]
    return (
        type(product) is str
        and product in _PRODUCTS
        and type(quantity) is int
        and quantity > 0
    )


def apply_public_supply_order(
    observation: Any,
    action: Any,
    configuration: Any = None,
    *,
    enabled: bool = True,
) -> Any:
    """Stable-partition the leading SELL block by visible rival standing supply.

    Disabled or unsupported inputs return the exact same parent object. Only absent,
    ``None``, or an exact empty ``marketParams`` mapping counts as the frozen default
    market contract; custom parameters and falsey type-confused aliases fail closed.
    Every row object, quantity, tail position and non-market action is retained.
    """
    REPORT["calls"] += 1
    if not enabled or type(action) is not dict:
        return action
    if configuration is not None and type(configuration) is not dict:
        return action
    if type(configuration) is dict:
        market_params = configuration.get("marketParams")
        if market_params is not None:
            if type(market_params) is not dict or market_params:
                return action
    market = action.get("market")
    if type(market) is not list:
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
