#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""H1 experiment: rescue mature annual yield at L1's first-decay WATER boundary.

L1 kill-late-water suppresses WATER when an annual crop has reached or passed its
``max_lifespan_step``. In the official engine, equality is the crop's *first decay
tick*, not necessarily its final live action: decay subtracts one yield unit at
equality and then every two steps until the tile weeds. The unit action executes
before that decay. At exact equality an annual crop is already one day beyond its
last WATER-yield window, so WATER adds no annual yield, while same-tile HARVEST can
still collect every currently mature unit before the first decay subtracts one.

H1 deliberately changes only that exact first-decay boundary:
``WATER -> HARVEST`` when ``max_lifespan_step == step`` and mature physical yield
is present. It does not generalize to ``max_lifespan_step < step`` even though a
multi-unit crop can legally survive later decay ticks; stale/future lifespan states,
ongoing crops, unknown/malformed state, non-WATER commands, and nonstandard
``turnsPerDay`` all preserve the exact parent action object.
"""
from __future__ import annotations

import copy
from collections import Counter

TURNS_PER_DAY = 24
LATE_START = 672
LATE_END = 718

FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}
ANNUAL = {"WHEAT", "CARROT", "MELON"}

telemetry = Counter()


def _cfg(configuration, name, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _standard_configuration(configuration):
    value = _cfg(configuration, "turnsPerDay", TURNS_PER_DAY)
    return type(value) is int and value == TURNS_PER_DAY


def _tile_for_actor(observation, actor):
    try:
        player = observation["player"]
        if type(player) is not int:
            return None
        farm = observation["farms"][player]
        hands = farm.get("hands")
        if hands is None:
            hands = []
        if not isinstance(hands, list):
            return None
        positions = [farm["farmer"], *hands]
        if actor < 0 or actor >= len(positions):
            return None
        pos = positions[actor]
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return None
        x, y = pos
        if type(x) is not int or type(y) is not int:
            return None
        tiles = farm["tiles"]
        if y < 0 or y >= len(tiles):
            return None
        row = tiles[y]
        if not isinstance(row, list) or x < 0 or x >= len(row):
            return None
        return row[x]
    except (KeyError, TypeError, IndexError):
        return None


def _first_decay_harvestable(step, tile):
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return False
    crop = tile.get("crop")
    if crop not in ANNUAL:
        return False
    planted = tile.get("planted_day")
    units = tile.get("yield_units")
    lifespan = tile.get("max_lifespan_step")
    if type(planted) is not int or type(units) is not int or type(lifespan) is not int:
        return False
    if planted < 0 or units <= 0:
        return False
    # Equality is deliberate: this experiment owns only the first decay tick.
    # A multi-unit annual crop may legally survive later (lifespan < step) ticks,
    # but those states are intentionally outside this bounded theorem.
    if lifespan != step:
        return False
    day = step // TURNS_PER_DAY
    return day - planted >= FIRST_YIELD_DAY[crop]


def transform(observation, action, configuration=None, enabled=False):
    """Return parent action or a copy with first-decay WATER -> HARVEST rescues."""
    if not enabled:
        telemetry["disabled"] += 1
        return action
    if not _standard_configuration(configuration):
        telemetry["nonstandard_configuration"] += 1
        return action
    if not isinstance(action, dict):
        telemetry["malformed_action"] += 1
        return action

    try:
        step = observation["step"]
    except (KeyError, TypeError):
        telemetry["malformed_step"] += 1
        return action
    if type(step) is not int or step < LATE_START or step > LATE_END:
        telemetry["outside_window"] += 1
        return action

    farmer = action.get("farmer")
    hands = action.get("hands")
    if not isinstance(farmer, list) or not isinstance(hands, list):
        telemetry["malformed_action"] += 1
        return action

    commands = [farmer, *hands]
    replacements = []
    for actor, command in enumerate(commands):
        if command != ["WATER"]:
            continue
        if _first_decay_harvestable(step, _tile_for_actor(observation, actor)):
            replacements.append(actor)
        else:
            telemetry["water_not_rescuable"] += 1

    if not replacements:
        return action

    out = copy.deepcopy(action)
    for actor in replacements:
        if actor == 0:
            out["farmer"] = ["HARVEST"]
        else:
            out["hands"][actor - 1] = ["HARVEST"]
    telemetry["changed_actions"] += 1
    telemetry["rescued_harvest_rows"] += len(replacements)
    return out


def install(parent, enabled=False):
    """Wrap a parent agent. Disabled/no-op paths preserve output object identity."""
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        return transform(observation, action, configuration, enabled=enabled)

    agent.parent = parent
    agent.telemetry = telemetry
    agent.h1_enabled = bool(enabled)
    return agent
