#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Default-OFF B9 terminal fertilizer micro-stacker.

This experiment wraps an existing V3.1 agent. It changes only literal PASS worker
commands at steps 716-717 when that worker is already on a shed-adjacent animal tile
with public fertilizer_available == True. Step 718 keeps the parent's liquidation
but moves SELL FERTILIZER rows behind all pre-existing rows iff this wrapper collected
fertilizer in the same episode, preserving the parent's existing terminal sale order.
"""
from __future__ import annotations

import copy

COLLECT_STEPS = frozenset((716, 717))
TERMINAL_STEP = 718
ANIMALS = frozenset(("GOOSE", "COW", "SHEEP"))


def _exact_int(value):
    return type(value) is int


def _beside_shed(position, board_size):
    if (type(position) is not list or len(position) != 2
            or not all(_exact_int(v) for v in position)
            or not _exact_int(board_size) or board_size <= 0):
        return False
    center = board_size // 2
    return position[0] in (center - 1, center) and position[1] in (center - 1, center)


def _collect_passes(observation, action):
    if type(action) is not dict:
        return action, False
    try:
        player = observation["player"]
        farms = observation["farms"]
        if not _exact_int(player) or not isinstance(farms, list) or not (0 <= player < len(farms)):
            return action, False
        farm = farms[player]
        if not isinstance(farm, dict):
            return action, False
        tiles, farmer, hands = farm["tiles"], farm["farmer"], farm["hands"]
        if (not isinstance(tiles, list) or not tiles or any(not isinstance(row, list) for row in tiles)
                or any(len(row) != len(tiles) for row in tiles)
                or not isinstance(hands, list)):
            return action, False
        positions = [farmer, *hands]
        action_hands = action.get("hands")
        if not isinstance(action_hands, list):
            return action, False
        workers = [action.get("farmer") or ["PASS"], *action_hands]
    except (KeyError, IndexError, TypeError):
        return action, False

    changed = False
    for index in range(min(len(workers), len(positions))):
        if workers[index] != ["PASS"] or not _beside_shed(positions[index], len(tiles)):
            continue
        x, y = positions[index]
        if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])):
            continue
        tile = tiles[y][x]
        if (not isinstance(tile, dict) or tile.get("animal") not in ANIMALS
                or tile.get("fertilizer_available") is not True):
            continue
        workers[index] = ["COLLECT_FERTILIZER"]
        changed = True

    if not changed:
        return action, False
    result = copy.deepcopy(action)
    result["farmer"] = workers[0]
    result["hands"] = workers[1:]
    return result, True


def _trail_fertilizer_sales(action):
    if type(action) is not dict or type(action.get("market")) is not list:
        return action
    market = action["market"]
    non_fert = []
    fert = []
    for order in market:
        if type(order) is list and len(order) >= 2 and order[0] == "SELL" and order[1] == "FERTILIZER":
            fert.append(order)
        else:
            non_fert.append(order)
    reordered = non_fert + fert
    if not fert or reordered == market:
        return action
    result = copy.deepcopy(action)
    result["market"] = copy.deepcopy(reordered)
    return result


class TerminalFertilizerAgent:
    def __init__(self, parent):
        if not callable(parent):
            raise TypeError("parent must be callable")
        self.parent = parent
        self._state = {}

    def __call__(self, observation, configuration=None):
        action = self.parent(observation, configuration)
        try:
            step = observation["step"]
            player = observation["player"]
        except (KeyError, TypeError):
            return action
        if not _exact_int(step) or not _exact_int(player):
            return action

        state = self._state.get(player)
        if state is None or step <= state["last_step"]:
            state = self._state[player] = {"last_step": -1, "collected": False}
        state["last_step"] = step

        if step in COLLECT_STEPS:
            result, changed = _collect_passes(observation, action)
            if changed:
                state["collected"] = True
            return result
        if step == TERMINAL_STEP and state["collected"]:
            return _trail_fertilizer_sales(action)
        return action


def make_agent(parent):
    return TerminalFertilizerAgent(parent)
