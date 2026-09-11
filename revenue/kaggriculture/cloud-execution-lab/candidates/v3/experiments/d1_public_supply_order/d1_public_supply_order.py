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


_PRODUCTS = frozenset({
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
})
_CROPS = frozenset({"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"})
_ANIMAL_PRODUCTS = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
_EMPTY_KINDS = frozenset({"WEED", "COOP", "PASTURE"})
_MISSING = object()

REPORT = {
    "calls": 0,
    "activations": 0,
    "rows_moved": 0,
    "visible_signal_units": 0,
    "signal_products": {},
}


def _strict_nonnegative_int(value: Any) -> int | None:
    """Accept only real integer public counters; bool/string/float are invalid."""
    if type(value) is not int or value < 0:
        return None
    return value


def _default_market_contract(configuration: Any) -> bool:
    """True only when configuration proves the pinned default market contract.

    Kaggle's configuration is dict-like rather than guaranteed to be a literal dict, so
    support a callable ``get`` while retaining a sentinel that distinguishes an absent
    field from falsey malformed overrides.  ``None``/missing and an exact empty mapping
    are semantically the official default; any other supplied marketParams value fails
    closed, including false/0/[]/"".
    """
    if configuration is None:
        return True
    try:
        getter = configuration.get
    except Exception:
        return False
    if not callable(getter):
        return False
    try:
        market_params = getter("marketParams", _MISSING)
    except TypeError:
        # Some mapping-like implementations expose get(key) only.  They cannot prove
        # field absence separately from a malformed falsey value, so stay conservative.
        try:
            market_params = getter("marketParams")
        except Exception:
            return False
        return market_params is None
    except Exception:
        return False
    return (
        market_params is _MISSING
        or market_params is None
        or (type(market_params) is dict and not market_params)
    )


def public_rival_supply(observation: Any) -> dict[str, int] | None:
    """Return visible standing yield, {} for valid no-signal, or None for invalid evidence.

    The distinction is intentional.  D1 must never combine one valid rival tile with an
    unreadable/malformed sibling and then treat the partial board as authoritative.  Only
    official public tile shapes are accepted: None/LOCKED, WEED, empty COOP/PASTURE,
    PLANT with a known crop and strict yield counter, or occupied COOP/PASTURE with a
    known animal and strict yield counter.  Private shed, inventories, seeds and market
    orders remain outside this helper entirely.
    """
    if type(observation) is not dict:
        return None
    farms = observation.get("farms")
    player = observation.get("player")
    if type(farms) is not list or len(farms) != 2 or type(player) is not int or player not in (0, 1):
        return None
    rival = farms[1 - player]
    if type(rival) is not dict:
        return None
    tiles = rival.get("tiles")
    if type(tiles) is not list:
        return None

    result: dict[str, int] = {}
    for row in tiles:
        if type(row) is not list:
            return None
        for tile in row:
            if tile is None or tile == "LOCKED":
                continue
            if type(tile) is not dict:
                return None
            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile.get("crop")
                units = _strict_nonnegative_int(tile.get("yield_units"))
                if type(crop) is not str or crop not in _CROPS or units is None:
                    return None
                if units:
                    result[crop] = result.get(crop, 0) + units
                continue
            if kind in ("COOP", "PASTURE") and "animal" in tile:
                animal = tile.get("animal")
                product = _ANIMAL_PRODUCTS.get(animal) if type(animal) is str else None
                units = _strict_nonnegative_int(tile.get("yield_units"))
                expected_kind = "COOP" if animal == "GOOSE" else "PASTURE"
                if product is None or kind != expected_kind or units is None:
                    return None
                if units:
                    result[product] = result.get(product, 0) + units
                continue
            if kind in _EMPTY_KINDS and "animal" not in tile:
                continue
            return None
    return result


def _eligible_sell(row: Any) -> bool:
    """Validate a literal leading SELL row before D1 is allowed to inspect its item."""
    if type(row) is not list or len(row) < 3 or row[0] != "SELL":
        return False
    item, quantity = row[1], row[2]
    return type(item) is str and item in _PRODUCTS and type(quantity) is int and quantity > 0


def apply_public_supply_order(
    observation: Any,
    action: Any,
    configuration: Any = None,
    *,
    enabled: bool = True,
) -> Any:
    """Stable-partition the leading SELL block by visible rival standing supply.

    Disabled, malformed or unsupported inputs return the exact same parent object.  The
    rival public evidence is atomic: a malformed sibling tile invalidates the signal rather
    than being silently skipped.  Every row object, quantity, tail position and non-market
    action is retained.
    """
    REPORT["calls"] += 1
    if not enabled or type(action) is not dict or not _default_market_contract(configuration):
        return action
    market = action.get("market")
    if type(market) is not list:
        return action

    lead = 0
    while lead < len(market):
        row = market[lead]
        # A non-SELL row is the intentional end of the prefix.  A literal SELL with
        # malformed item/quantity is different: D1 must not partially reinterpret a
        # malformed market action, so preserve exact parent identity.
        if type(row) is not list or not row or row[0] != "SELL":
            break
        if not _eligible_sell(row):
            return action
        lead += 1
    if lead < 2:
        return action

    signal = public_rival_supply(observation)
    if signal is None or not signal:
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
