# SPDX-License-Identifier: Apache-2.0
"""Current-selected-action recovery of submitted V3.1 V231 late COW acquisition.

This deliberately preserves only the published late V231 window (steps 216..227).
The separately parameterized ``cattle_early`` window is not implemented here because
the submitted V3.1 winner shipped it disabled.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

SUBMITTED_V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
SUBMITTED_V31_ROUTER_GIT_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"
SUBMITTED_V31_ROUTER_SHA256 = "41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a"
SUBMITTED_V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"

ANIMALS = ("COW", "SHEEP", "GOOSE")
MILK_SHOPS = ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP")
SHED_CAPACITY = 100
MAX_ORDERS = 10
LATE_START = 216
LATE_END = 227
DEFAULT_CAP = 4


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _quantity(command: list[Any]) -> int:
    if len(command) < 3:
        return 1
    value = command[2]
    return value if _is_int(value) and value >= 0 else -1


def _new_state() -> dict[str, Any]:
    return {
        "last": -1,
        "confirmed": 0,
        "reserved": 0,
        "pending_buy": None,
        "carrying": {},
        "pending_places": [],
        "sites": {},
        "milk_credit": 0,
        "requested": 0,
        "failed_purchase_units": 0,
        "picked": 0,
        "placed": 0,
        "failed_placements": 0,
        "extra_milk_harvested": 0,
        "extra_milk_sale_requests": 0,
    }


def _shape(observation: Any, selected: Any) -> bool:
    if not isinstance(observation, dict) or not isinstance(selected, dict):
        return False
    if not _is_int(observation.get("step")) or not _is_int(observation.get("player")):
        return False
    farms = observation.get("farms")
    player = observation.get("player")
    if not isinstance(farms, list) or not (0 <= player < len(farms)):
        return False
    farm = farms[player]
    private = observation.get("private")
    market_obs = observation.get("market")
    town = observation.get("town")
    if not isinstance(farm, dict) or not isinstance(private, dict) or not isinstance(market_obs, dict) or not isinstance(town, dict):
        return False
    tiles = farm.get("tiles")
    hands = farm.get("hands")
    farmer = farm.get("farmer")
    inventories = private.get("inventories")
    shed = private.get("shed")
    prices = market_obs.get("prices")
    shops = town.get("unlocked_shops")
    if not isinstance(tiles, list) or not tiles or any(not isinstance(row, list) for row in tiles):
        return False
    if not isinstance(hands, list) or not isinstance(farmer, (list, tuple)) or len(farmer) != 2:
        return False
    if not isinstance(inventories, list) or len(inventories) != 1 + len(hands):
        return False
    if any(not isinstance(inventory, dict) for inventory in inventories):
        return False
    if not isinstance(shed, dict) or not isinstance(prices, dict) or not isinstance(shops, list):
        return False
    for mapping in [shed, *inventories]:
        for animal in ANIMALS:
            value = mapping.get(animal, 0)
            if not _is_int(value) or value < 0:
                return False
    workers = [selected.get("farmer"), *(selected.get("hands") or [])]
    if selected.get("farmer") is None or not isinstance(selected.get("hands"), list):
        return False
    if len(workers) != len(inventories):
        return False
    if any(not isinstance(work, list) or not work or not isinstance(work[0], str) for work in workers):
        return False
    orders = selected.get("market")
    if not isinstance(orders, list) or len(orders) > MAX_ORDERS:
        return False
    if any(not isinstance(order, list) or not order or not isinstance(order[0], str) for order in orders):
        return False
    return True


def _tile(farm: dict[str, Any], position: Any) -> Any:
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        return None
    x, y = position
    if not _is_int(x) or not _is_int(y):
        return None
    rows = farm["tiles"]
    if not (0 <= y < len(rows)) or not (0 <= x < len(rows[y])):
        return None
    return rows[y][x]


def _beside_shed(farm: dict[str, Any], position: Any) -> bool:
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        return False
    x, y = position
    if not _is_int(x) or not _is_int(y):
        return False
    center = len(farm["tiles"]) // 2
    return x in (center - 1, center) and y in (center - 1, center)


def _projected_shed(selected: dict[str, Any], observation: dict[str, Any]) -> dict[str, int]:
    """Conservative stock projection used only for V231's harvested-milk sale credit."""
    farm = observation["farms"][observation["player"]]
    private = observation["private"]
    stock: dict[str, int] = {}
    for item, qty in private["shed"].items():
        stock[item] = max(0, int(qty)) if _is_int(qty) else 0
    total = sum(stock.values())
    positions = [farm["farmer"], *farm["hands"]]
    workers = [selected["farmer"], *selected["hands"]]
    inventories = private["inventories"]
    for actor, work in enumerate(workers):
        if actor >= len(positions) or not _beside_shed(farm, positions[actor]):
            continue
        inventory = inventories[actor]
        if not isinstance(inventory, dict):
            continue
        operation = work[0]
        if operation == "PICKUP" and len(work) >= 2:
            item = work[1]
            quantity = _quantity(work)
            if quantity < 0:
                continue
            taken = min(stock.get(item, 0), quantity)
            stock[item] = max(0, stock.get(item, 0) - taken)
            total -= taken
        elif operation == "DROP":
            for item, held in inventory.items():
                if not _is_int(held) or held <= 0:
                    continue
                added = min(held, max(0, SHED_CAPACITY - total))
                stock[item] = stock.get(item, 0) + added
                total += added
        elif operation == "PLACE" and len(work) >= 2 and work[1] not in ANIMALS:
            item = work[1]
            quantity = _quantity(work)
            held = inventory.get(item, 0)
            if quantity < 0 or not _is_int(held):
                continue
            added = min(quantity, max(0, held), max(0, SHED_CAPACITY - total))
            stock[item] = stock.get(item, 0) + added
            total += added
    return stock


@dataclass
class V231LateCurrentABI:
    """Selected-action adapter for the submitted V231 late livestock substitution."""

    enabled: bool = False
    cap: int = DEFAULT_CAP
    _states: dict[int, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be exact bool")
        if not _is_int(self.cap) or self.cap <= 0:
            raise ValueError("cap must be a positive integer")

    def transform(self, observation: Any, selected: Any) -> Any:
        if not self.enabled:
            return copy.deepcopy(selected)
        if not _shape(observation, selected):
            return copy.deepcopy(selected)

        step = observation["step"]
        seat = observation["player"]
        state = self._states.get(seat)
        if state is None or step <= state["last"]:
            state = self._states[seat] = _new_state()
        return self._transform_valid(observation, selected, state)

    def _transform_valid(
        self, observation: dict[str, Any], selected: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]:
        step = observation["step"]
        seat = observation["player"]
        farm = observation["farms"][seat]
        private = observation["private"]
        shed = private["shed"]
        inventories = private["inventories"]
        positions = [farm["farmer"], *farm["hands"]]

        pending = state["pending_buy"]
        if pending is not None:
            current_cows = shed.get("COW", 0)
            before = pending["before"]
            gained = max(0, current_cows - before) if _is_int(current_cows) else 0
            confirmed = min(pending["quantity"], gained)
            state["confirmed"] += confirmed
            state["reserved"] += confirmed
            state["failed_purchase_units"] += pending["quantity"] - confirmed
            state["pending_buy"] = None

        for pending_place in state["pending_places"]:
            x, y = pending_place["site"]
            tile = _tile(farm, (x, y))
            if (
                isinstance(tile, dict)
                and tile.get("animal") == "COW"
                and tile.get("placed_day") == pending_place["day"]
            ):
                state["sites"][(x, y)] = pending_place["day"]
                state["placed"] += 1
                actor = pending_place["actor"]
                state["carrying"][actor] = max(0, state["carrying"].get(actor, 0) - 1)
            else:
                state["failed_placements"] += 1
        state["pending_places"] = []
        state["last"] = step

        result = copy.deepcopy(selected)
        workers = [result["farmer"], *result["hands"]]
        seen_harvest: set[tuple[int, int]] = set()
        cow_in_shed = shed.get("COW", 0)
        cow_available = cow_in_shed if _is_int(cow_in_shed) and cow_in_shed > 0 else 0
        occupied: set[tuple[int, int]] = set()

        for actor, work in enumerate(workers[: len(positions)]):
            inventory = inventories[actor]
            if not isinstance(inventory, dict):
                continue
            tile = _tile(farm, positions[actor])
            if tile is None:
                continue
            x, y = positions[actor]
            site = (x, y)

            if (
                work == ["HARVEST"]
                and site in state["sites"]
                and site not in seen_harvest
                and isinstance(tile, dict)
                and tile.get("animal") == "COW"
                and tile.get("placed_day") == state["sites"][site]
            ):
                units = tile.get("yield_units", 0)
                units = units if _is_int(units) and units > 0 else 0
                state["milk_credit"] += units
                state["extra_milk_harvested"] += units
                seen_harvest.add(site)

            if len(work) >= 2 and work[:2] == ["PICKUP", "SHEEP"]:
                quantity = _quantity(work)
                if (
                    quantity > 0
                    and state["reserved"] >= quantity
                    and cow_available >= quantity
                    and _beside_shed(farm, positions[actor])
                    and not any(
                        _is_int(inventory.get(animal, 0)) and inventory.get(animal, 0) > 0
                        for animal in ANIMALS
                    )
                ):
                    work[1] = "COW"
                    state["reserved"] -= quantity
                    cow_available -= quantity
                    state["carrying"][actor] = state["carrying"].get(actor, 0) + quantity
                    state["picked"] += quantity

            if (
                len(work) >= 2
                and work[:2] == ["PLACE", "SHEEP"]
                and state["carrying"].get(actor, 0) > 0
                and _is_int(inventory.get("COW", 0))
                and inventory.get("COW", 0) > 0
                and isinstance(tile, dict)
                and tile.get("kind") == "PASTURE"
                and "animal" not in tile
                and site not in occupied
            ):
                work[1] = "COW"
                state["pending_places"].append(
                    {"actor": actor, "site": site, "day": step // 24}
                )

            if (
                len(work) >= 2
                and work[0] == "PLACE"
                and work[1] in ANIMALS
                and _is_int(inventory.get(work[1], 0))
                and inventory.get(work[1], 0) > 0
            ):
                occupied.add(site)

        result["farmer"], result["hands"] = workers[0], workers[1:]
        market = result["market"]
        animal_orders = [
            order for order in market if len(order) >= 3 and order[0] == "BUY_ANIMAL"
        ]
        shops = observation["town"]["unlocked_shops"]
        prices = observation["market"]["prices"]
        counts = {"COW": 0, "SHEEP": 0}
        for row in farm["tiles"]:
            for tile in row:
                if isinstance(tile, dict) and tile.get("animal") in counts:
                    counts[tile["animal"]] += 1

        cargo = 0
        for inventory in inventories:
            for animal in ANIMALS:
                cargo += inventory.get(animal, 0)

        stock_animals = sum(shed.get(animal, 0) for animal in ANIMALS)

        milk_shops = sum(shop in MILK_SHOPS for shop in shops)
        milk_price = prices.get("MILK")
        wool_price = prices.get("WOOL")
        late = (
            LATE_START <= step <= LATE_END
            and len(shops) >= 3
            and milk_shops >= 2
            and "YARN_STORE" not in shops
            and _is_int(milk_price)
            and _is_int(wool_price)
            and milk_price >= wool_price
        )
        if (
            late
            and state["confirmed"] < self.cap
            and not state["reserved"]
            and not any(state["carrying"].values())
            and not state["pending_places"]
            and not cargo
            and not stock_animals
            and len(animal_orders) == 1
            and len(animal_orders[0]) >= 3
            and animal_orders[0][1] == "SHEEP"
            and counts["COW"] >= 4
            and counts["SHEEP"] >= 2
        ):
            order = animal_orders[0]
            quantity = order[2]
            if (
                _is_int(quantity)
                and 1 <= quantity <= 2
                and quantity <= self.cap - state["confirmed"]
            ):
                order[1] = "COW"
                state["requested"] += quantity
                before = shed.get("COW", 0)
                state["pending_buy"] = {"before": before, "quantity": quantity}

        if state["milk_credit"] > 0:
            stock = _projected_shed(result, observation)
            total_planned = 0
            for order in market:
                if (
                    len(order) >= 3
                    and order[:2] == ["SELL", "MILK"]
                    and _is_int(order[2])
                    and order[2] > 0
                ):
                    total_planned += order[2]
            extra = min(
                state["milk_credit"], max(0, stock.get("MILK", 0) - total_planned)
            )
            if extra:
                for order in market:
                    if (
                        len(order) >= 3
                        and order[:2] == ["SELL", "MILK"]
                        and _is_int(order[2])
                        and order[2] > 0
                    ):
                        order[2] += extra
                        state["milk_credit"] -= extra
                        state["extra_milk_sale_requests"] += extra
                        break

        result["market"] = market
        return result
