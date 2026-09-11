# SPDX-License-Identifier: Apache-2.0
"""Production-preview helper for the reviewed B5 CARROT no-detour factor.

This is an additive preview copy, not a shipped overlay module. Valid standard-config
semantics match the source-green #12499 experiment: only an already-authored literal
PASS may become FERTILIZE, only on that actor's current CARROT tile, only with carried
fertilizer, and only when coverage is incomplete. Every represented actor is validated
atomically before any replacement is recorded. The package preview additionally binds
the reviewed timing theorem to literal ``turnsPerDay == 24``.
"""
from __future__ import annotations

import copy

DONOR_HEAD = "15e8367e4d3fff41e7e6eb2d088327f558764454"
DONOR_BLOB = "4e4f9d490332f075cf50df595cb7a067d6236066"
_MISSING = object()


def _int(value):
    return type(value) is int


def _config_value(configuration, key):
    if configuration is None:
        return _MISSING
    if isinstance(configuration, dict):
        return configuration.get(key, _MISSING)
    getter = getattr(configuration, "get", None)
    if callable(getter):
        try:
            return getter(key, _MISSING)
        except (AttributeError, KeyError, TypeError, ValueError):
            return _MISSING
    try:
        return getattr(configuration, key, _MISSING)
    except (AttributeError, KeyError, TypeError, ValueError):
        return _MISSING


def _standard_timing(configuration):
    turns = _config_value(configuration, "turnsPerDay")
    return type(turns) is int and turns == 24


def _eligible(tile, inventory, day):
    if not isinstance(tile, dict) or not isinstance(inventory, dict) or not _int(day):
        return False
    fertilizer = inventory.get("FERTILIZER")
    coverage = tile.get("fertilized_until_day")
    return (
        tile.get("kind") == "PLANT"
        and tile.get("crop") == "CARROT"
        and _int(fertilizer)
        and fertilizer > 0
        and _int(coverage)
        and coverage < day + 2
    )


def apply_carrot_fertilizer(observation, configuration, action):
    """Apply B5 after the parent R04 action; malformed evidence is exact-parent identity."""
    if not _standard_timing(configuration):
        return action
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action

    player = observation.get("player")
    step = observation.get("step")
    farms = observation.get("farms")
    private = observation.get("private")
    if (
        not _int(player)
        or player < 0
        or not _int(step)
        or step < 0
        or not isinstance(farms, list)
        or player >= len(farms)
        or not isinstance(private, dict)
    ):
        return action

    farm = farms[player]
    inventories = private.get("inventories")
    farm_hands = farm.get("hands") if isinstance(farm, dict) else None
    action_hands = action.get("hands")
    if (
        not isinstance(farm, dict)
        or "farmer" not in farm
        or "farmer" not in action
        or not isinstance(farm_hands, list)
        or not isinstance(action_hands, list)
        or not isinstance(inventories, list)
    ):
        return action

    positions = [farm["farmer"], *farm_hands]
    commands = [action["farmer"], *action_hands]
    if len(positions) != len(commands) or len(commands) != len(inventories):
        return action
    tiles = farm.get("tiles")
    if not isinstance(tiles, list):
        return action

    actor_rows = []
    for command, position, inventory in zip(commands, positions, inventories):
        if not isinstance(command, list) or not command or not isinstance(command[0], str):
            return action
        if command[0] == "PASS" and command != ["PASS"]:
            return action
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 2
            or not _int(position[0])
            or not _int(position[1])
            or not isinstance(inventory, dict)
        ):
            return action
        if "FERTILIZER" in inventory:
            fertilizer = inventory["FERTILIZER"]
            if not _int(fertilizer) or fertilizer < 0:
                return action
        x, y = position
        if y < 0 or y >= len(tiles) or not isinstance(tiles[y], list) or x < 0 or x >= len(tiles[y]):
            return action
        tile = tiles[y][x]
        if (
            command == ["PASS"]
            and isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and tile.get("crop") == "CARROT"
            and not _int(tile.get("fertilized_until_day"))
        ):
            return action
        actor_rows.append((command, inventory, x, y, tile))

    day = step // 24
    claimed = set()
    replacements = {}
    for actor, (command, inventory, x, y, tile) in enumerate(actor_rows):
        if command != ["PASS"] or (x, y) in claimed:
            continue
        if not _eligible(tile, inventory, day):
            continue
        replacements[actor] = ["FERTILIZE"]
        claimed.add((x, y))

    if not replacements:
        return action
    result = copy.deepcopy(action)
    result_commands = [result["farmer"], *result["hands"]]
    for actor, command in replacements.items():
        result_commands[actor] = command
    result["farmer"] = result_commands[0]
    result["hands"] = result_commands[1:]
    return result
