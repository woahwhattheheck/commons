"""Pure integration primitive for the weed-continuation capital firewall."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


def transform(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any],
    selected: dict[str, Any],
    weed_sites: Iterable[tuple[int, int]],
    animal_costs: Mapping[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Suppress a same-species, sale-funded animal copy after a rescued asset.

    A purchase is considered sale-funded when own cash before this market queue
    cannot buy one unit, while at least one earlier executable row is a SELL.
    The queue index is preserved with an empty row. No other action is changed.
    """
    sites = tuple(sorted(set(weed_sites)))
    if not sites:
        return selected, {"changed": False, "reason": "no_weed_site"}
    try:
        player = int(observation["player"])
        farm = observation["farms"][player]
        tiles = farm["tiles"]
        money = float(farm["money"])
    except (KeyError, TypeError, ValueError, IndexError):
        return selected, {"changed": False, "reason": "unsupported_observation"}
    animals: set[str] = set()
    for x, y in sites:
        try:
            tile = tiles[y][x]
        except (IndexError, TypeError):
            return selected, {"changed": False, "reason": "invalid_weed_site"}
        if isinstance(tile, dict) and isinstance(tile.get("animal"), str):
            animals.add(tile["animal"])
    if not animals:
        return selected, {"changed": False, "reason": "weed_asset_not_realized"}
    market = selected.get("market", [])
    if not isinstance(market, list):
        return selected, {"changed": False, "reason": "invalid_market"}
    try:
        limit = int(configuration.get("maxMarketOrdersPerTurn", 10))
    except (TypeError, ValueError):
        return selected, {"changed": False, "reason": "invalid_market_limit"}
    for slot, order in enumerate(market[:max(0, limit)]):
        if not (isinstance(order, list) and len(order) >= 3 and
                order[0] == "BUY_ANIMAL" and order[1] in animals):
            continue
        try:
            quantity = int(order[2])
            cost = float(animal_costs[order[1]])
        except (KeyError, TypeError, ValueError):
            continue
        if quantity <= 0 or money >= cost:
            continue
        if not any(isinstance(prior, list) and prior and prior[0] == "SELL"
                   for prior in market[:slot]):
            continue
        result = deepcopy(selected)
        result["market"][slot] = []
        return result, {
            "changed": True,
            "slot": slot,
            "animal": order[1],
            "pre_market_money": money,
            "unit_cost": cost,
            "weed_sites": [list(site) for site in sites],
            "reason": "same_species_purchase_requires_earlier_same_turn_sales",
        }
    return selected, {"changed": False, "reason": "no_sale_funded_same_species_copy"}
