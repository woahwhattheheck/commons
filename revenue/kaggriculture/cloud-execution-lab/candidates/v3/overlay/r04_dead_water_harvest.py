# SPDX-License-Identifier: Apache-2.0
"""V4 W1: recover provably dead WATER turns into same-tile HARVEST.

This lane is intentionally narrower than worker reassignment. It never hires,
moves, buys, plants, services animals, or touches market rows. During the
existing late-water window it only rewrites an authored ["WATER"] when:

* the WATER is provably wasted (the plant is already watered today, or its
  public max_lifespan_step is at/before the current step), and
* the same standing plant is provably harvestable from public state.

Annual crops start with yield_units == 1 before maturity in the official engine,
so yield_units alone is not sufficient. We also require planted_day plus the
official first_yield_day for the crop. Unexpected state fails closed.
"""
from __future__ import annotations

LATE_START = 672
LATE_END = 718

FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}

_WATER = ["WATER"]
_HARVEST = ["HARVEST"]
_UNKNOWN = object()

report = {
    "steps_active": 0,
    "already_watered": 0,
    "expiring": 0,
    "not_harvestable": 0,
    "recovered": 0,
}


def reset():
    for key in report:
        report[key] = 0


def get_report():
    return dict(report)


def _plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _worker_tile(farm, position):
    try:
        x, y = position
        if not _plain_int(x) or not _plain_int(y):
            return _UNKNOWN
        tiles = farm["tiles"]
        if y < 0 or y >= len(tiles):
            return _UNKNOWN
        row = tiles[y]
        if x < 0 or x >= len(row):
            return _UNKNOWN
        return row[x]
    except Exception:
        return _UNKNOWN


def _wasted_water_reason(step, tile):
    """Return why WATER is wasted on this plant, else None."""
    try:
        if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
            return None
        if tile.get("watered_today") is True:
            return "already_watered"
        max_lifespan_step = tile.get("max_lifespan_step")
        if _plain_int(max_lifespan_step) and max_lifespan_step <= step:
            return "expiring"
    except Exception:
        return None
    return None


def _harvestable(tile, day):
    """Prove that HARVEST can collect positive units on the standing plant."""
    try:
        if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
            return False
        crop = tile.get("crop")
        first_yield_day = FIRST_YIELD_DAY.get(crop)
        if first_yield_day is None:
            return False
        planted_day = tile.get("planted_day")
        yield_units = tile.get("yield_units")
        if not _plain_int(planted_day) or not _plain_int(yield_units):
            return False
        if yield_units <= 0:
            return False
        return day - planted_day >= first_yield_day
    except Exception:
        return False


def apply_dead_water_harvest(observation, action, enabled=True):
    """Recover same-tile HARVESTs; return the original object when unchanged."""
    if not enabled:
        return action
    try:
        step = observation["step"]
        day = observation["day"]
        if not _plain_int(step) or not _plain_int(day):
            return action
        if step < LATE_START or step > LATE_END:
            return action
        if not isinstance(action, dict):
            return action

        farm = observation["farms"][observation["player"]]
        positions = [farm["farmer"]] + list(farm.get("hands") or [])
        commands = [action.get("farmer")] + list(action.get("hands") or [])
        report["steps_active"] += 1

        changed = False
        new_commands = list(commands)
        for index, (command, position) in enumerate(zip(commands, positions)):
            if command != _WATER:
                continue
            tile = _worker_tile(farm, position)
            if tile is _UNKNOWN:
                continue
            reason = _wasted_water_reason(step, tile)
            if reason is None:
                continue
            report[reason] += 1
            if not _harvestable(tile, day):
                report["not_harvestable"] += 1
                continue
            new_commands[index] = list(_HARVEST)
            report["recovered"] += 1
            changed = True

        if not changed:
            return action
        out = dict(action)
        out["farmer"] = new_commands[0]
        out["hands"] = new_commands[1:]
        return out
    except Exception:
        return action
