#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""B3 experiment: replace provably low-value WATER with same-tile HARVEST.

The transform is intentionally narrow and stateless. It only edits a parent WATER
when the official interpreter's public crop state proves that skipping this watering:

* cannot create a second consecutive dry day at the next daily refresh;
* cannot sacrifice an immediate non-ongoing WATER yield increment; and
* cannot sacrifice a fertilized ongoing-production bonus due at the next refresh.

Even then, it edits only when the same tile already holds legally harvestable yield.
Otherwise the exact parent action object is returned.

Official source pin used for the crop semantics:
  interpreter commit 28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c
  kaggriculture.py sha256
  bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e
"""
from __future__ import annotations

import copy
from collections import Counter

TURNS_PER_DAY = 24

# Exact public crop timing constants from the pinned official interpreter.
CROPS = {
    "WHEAT": {
        "first_yield_day": 2,
        "max_yield_day": 4,
        "interval": 0,
        "max_yield": 6,
        "ongoing": False,
    },
    "CARROT": {
        "first_yield_day": 2,
        "max_yield_day": 3,
        "interval": 0,
        "max_yield": 4,
        "ongoing": False,
    },
    "TOMATO": {
        "first_yield_day": 8,
        "max_yield_day": 8,
        "interval": 1,
        "max_yield": 4,
        "ongoing": True,
    },
    "STRAWBERRY": {
        "first_yield_day": 10,
        "max_yield_day": 10,
        "interval": 2,
        "max_yield": 4,
        "ongoing": True,
    },
    "MELON": {
        "first_yield_day": 10,
        "max_yield_day": 12,
        "interval": 0,
        "max_yield": 6,
        "ongoing": False,
    },
}

telemetry = Counter()


def _cfg(configuration, name, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _standard_configuration(configuration):
    try:
        return int(_cfg(configuration, "turnsPerDay", TURNS_PER_DAY)) == TURNS_PER_DAY
    except (TypeError, ValueError):
        return False


def _tile_for_actor(observation, actor):
    try:
        player = int(observation["player"])
        farm = observation["farms"][player]
        positions = [farm["farmer"], *(farm.get("hands") or [])]
        if actor < 0 or actor >= len(positions):
            return None
        position = positions[actor]
        if not isinstance(position, (list, tuple)) or len(position) != 2:
            return None
        x, y = int(position[0]), int(position[1])
        tiles = farm["tiles"]
        if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
            return None
        return tiles[y][x]
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _crop_state(tile):
    """Return validated public crop state or None; never coerce malformed booleans."""
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return None
    crop = tile.get("crop")
    if crop not in CROPS:
        return None
    planted = tile.get("planted_day")
    dry = tile.get("consecutive_unwatered")
    watered = tile.get("watered_today")
    units = tile.get("yield_units")
    fertilized_until = tile.get("fertilized_until_day", -1)
    if type(planted) is not int or type(dry) is not int or type(watered) is not bool:
        return None
    if type(units) is not int or type(fertilized_until) is not int:
        return None
    if planted < 0 or dry < 0 or units < 0:
        return None
    return crop, planted, dry, watered, units, fertilized_until


def _harvestable(day, crop, planted_day, units):
    return units > 0 and day - planted_day >= CROPS[crop]["first_yield_day"]


def _water_has_crop_value(day, crop, planted_day, watered_today, units, fertilized_until):
    """Mirror only the official WATER-dependent yield terms.

    Non-ongoing crops gain yield synchronously on WATER during their yield window.
    Ongoing crops gain base yield at daily refresh without WATER, but an active
    fertilizer bonus at a production refresh requires WATER that day.
    """
    if watered_today:
        return False

    cd = CROPS[crop]
    if not cd["ongoing"]:
        age = day - planted_day
        window_start = (cd["max_yield_day"] + 1) // 2
        return window_start <= age <= cd["max_yield_day"] and units < cd["max_yield"]

    next_day = day + 1
    days_since_first = next_day - planted_day - cd["first_yield_day"]
    if days_since_first < 0:
        return False
    if days_since_first % cd["interval"] != 0:
        return False
    production_count = days_since_first // cd["interval"] + 1
    if production_count > cd["max_yield"]:
        return False
    return fertilized_until >= day and units < cd["max_yield"]


def transform(observation, action, configuration=None, enabled=False):
    """Return parent action or a copy with safe WATER->HARVEST substitutions."""
    if not enabled:
        telemetry["disabled"] += 1
        return action
    if not _standard_configuration(configuration):
        telemetry["nonstandard_configuration"] += 1
        return action
    try:
        step = observation["step"]
        if type(step) is not int or step < 0:
            telemetry["malformed_step"] += 1
            return action
        day = step // TURNS_PER_DAY
        farmer = action.get("farmer") or ["PASS"]
        hands = list(action.get("hands") or [])
    except (AttributeError, KeyError, TypeError):
        telemetry["malformed_action"] += 1
        return action

    commands = [farmer, *hands]
    replacements = {}
    for actor, command in enumerate(commands):
        if command != ["WATER"]:
            continue
        state = _crop_state(_tile_for_actor(observation, actor))
        if state is None:
            telemetry["water_unknown_tile"] += 1
            continue
        crop, planted, dry, watered, units, fertilized_until = state

        # If it was not already watered, a second consecutive dry day weeds the tile.
        if not watered and dry >= 1:
            telemetry["kept_survival_water"] += 1
            continue
        if _water_has_crop_value(day, crop, planted, watered, units, fertilized_until):
            telemetry["kept_yield_water"] += 1
            continue
        if not _harvestable(day, crop, planted, units):
            telemetry["no_productive_replacement"] += 1
            continue

        replacements[actor] = ["HARVEST"]

    if not replacements:
        return action

    out = copy.deepcopy(action)
    if 0 in replacements:
        out["farmer"] = replacements[0]
    for actor, replacement in replacements.items():
        if actor == 0:
            continue
        index = actor - 1
        if index < len(out.get("hands") or []):
            out["hands"][index] = replacement

    telemetry["changed_actions"] += 1
    telemetry["water_to_harvest"] += len(replacements)
    return out


def install(parent, enabled=False):
    """Wrap an exact parent agent. Disabled mode preserves parent output identity."""
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        return transform(observation, action, configuration, enabled=enabled)

    agent.telemetry = telemetry
    agent.parent = parent
    agent.b3_enabled = bool(enabled)
    return agent
