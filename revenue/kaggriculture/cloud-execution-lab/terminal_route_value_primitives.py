# SPDX-License-Identifier: Apache-2.0
"""Physical primitives for P21 terminal-route certificates."""
from collections.abc import Mapping

PASS = ["PASS"]
SHED_TOUCH = {"DROP", "PLACE"}
MOVES = {(1, 0): ["EAST"], (-1, 0): ["WEST"], (0, 1): ["SOUTH"], (0, -1): ["NORTH"]}


def integer(value, name, low=0, high=1_000_000):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def unit(row, worker):
    if worker == 0:
        return row.get("farmer", PASS)
    hands = row.get("hands", [])
    return hands[worker - 1] if worker <= len(hands) else PASS


def route_row(route, step):
    if step < 0 or step >= len(route):
        return {"farmer": PASS, "hands": [], "market": []}
    row = route[step]
    if not isinstance(row, Mapping):
        raise ValueError("route rows must be mappings")
    return row


def positive(mapping):
    if not isinstance(mapping, Mapping):
        raise ValueError("stock/inventory must be a mapping")
    result = {}
    for key, value in mapping.items():
        if type(value) is not int or value < 0:
            raise ValueError("stock/inventory quantities must be non-negative integers")
        if value:
            result[key] = value
    return result


def distance(a, b):
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


def path(a, b):
    x, y = int(a[0]), int(a[1]); tx, ty = int(b[0]), int(b[1]); out = []
    while x != tx:
        dx = 1 if tx > x else -1; out.append(MOVES[(dx, 0)]); x += dx
    while y != ty:
        dy = 1 if ty > y else -1; out.append(MOVES[(0, dy)]); y += dy
    return out


def shed_access(board):
    h = board // 2
    return ((h-1, h-1), (h, h-1), (h-1, h), (h, h))


def worker_idle(route, worker, start, end):
    for step in range(start, end + 1):
        action = unit(route_row(route, step), worker)
        if action != PASS:
            return False, step, action
    return True, None, None


def other_shed_collision(route, worker, start, end):
    for step in range(start, end + 1):
        row = route_row(route, step)
        for index, action in enumerate([row.get("farmer", PASS), *row.get("hands", [])]):
            if index != worker and isinstance(action, list) and action and action[0] in SHED_TOUCH:
                return step, index, action
    return None


def preterminal_market_clear(route, start, end, limit):
    for step in range(start, end):
        if any(order for order in list(route_row(route, step).get("market", []))[:limit]):
            return False, step
    return True, None


def harvest_lot(mechanics, farm, day, target):
    x, y = target; tiles = farm.get("tiles", [])
    if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])):
        return None, "target_out_of_bounds"
    tile = tiles[y][x]
    if not isinstance(tile, Mapping) or type(tile.get("yield_units")) is not int or tile["yield_units"] <= 0:
        return None, "target_has_no_harvestable_yield"
    if tile.get("kind") == "PLANT":
        crop = tile.get("crop"); data = getattr(mechanics, "CROPS", {}).get(crop)
        if not isinstance(data, Mapping):
            return None, "unknown_crop"
        if day - int(tile.get("planted_day", day + 1)) < int(data["first_yield_day"]):
            return None, "crop_not_mature"
        return (crop, tile["yield_units"]), None
    animal = tile.get("animal"); data = getattr(mechanics, "ANIMALS", {}).get(animal)
    if animal is not None and isinstance(data, Mapping):
        return (data["product"], tile["yield_units"]), None
    return None, "unsupported_harvest_asset"
