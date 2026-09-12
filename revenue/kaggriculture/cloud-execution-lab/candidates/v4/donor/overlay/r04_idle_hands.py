# SPDX-License-Identifier: Apache-2.0
"""Default-off idle-worker conversions for the TITAN V4 donor workspace.

This module never schedules movement and never invents inventory.  It only replaces
literal PASS commands for workers already standing on an eligible tile:

* ``apply_feed``: carried WHEAT + unfed animal -> FEED.
* ``apply_care``: fed + uncared animal -> CARE (all animals or goose-only).
* ``apply_wheat_fertilize``: carried fertilizer + unfertilized age-2..4 WHEAT -> FERTILIZE.

All transforms fail closed on malformed state, preserve the exact parent action object
when no replacement is made, and choose at most one actor per board tile.  ``apply_all``
is additionally gated by ``idle_all`` so merely installing the module cannot activate
behavior accidentally.
"""
from __future__ import annotations

import copy
from typing import Any

_TURNS_PER_DAY = 24
_MISSING = object()


def _strict_nonnegative_inventory(mapping: Any) -> bool:
    if not isinstance(mapping, dict):
        return False
    return all(isinstance(k, str) and type(v) is int and v >= 0 for k, v in mapping.items())


def _actor_rows(action: Any, observation: Any):
    """Return canonical actor tuples or ``None``; validates the whole actor surface atomically."""
    if not isinstance(action, dict) or not isinstance(observation, dict):
        return None
    player = observation.get("player", _MISSING)
    step = observation.get("step", _MISSING)
    farms = observation.get("farms", _MISSING)
    private = observation.get("private", _MISSING)
    if type(player) is not int or player < 0 or type(step) is not int or step < 0:
        return None
    if (not isinstance(farms, list) or len(farms) != 2 or player not in (0, 1)
            or not isinstance(private, dict)):
        return None
    farm = farms[player]
    if not isinstance(farm, dict):
        return None
    farmer_pos = farm.get("farmer", _MISSING)
    hand_pos = farm.get("hands", _MISSING)
    tiles = farm.get("tiles", _MISSING)
    inventories = private.get("inventories", _MISSING)
    farmer_cmd = action.get("farmer", _MISSING)
    hand_cmd = action.get("hands", _MISSING)
    if (not isinstance(farmer_pos, list) or not isinstance(hand_pos, list)
            or not isinstance(tiles, list) or not isinstance(inventories, list)
            or not isinstance(farmer_cmd, list) or not isinstance(hand_cmd, list)):
        return None

    positions = [farmer_pos, *hand_pos]
    commands = [farmer_cmd, *hand_cmd]
    if len(positions) != len(commands) or len(commands) != len(inventories):
        return None

    rows = []
    for actor, (position, command, inventory) in enumerate(zip(positions, commands, inventories)):
        if (not isinstance(command, list) or not command or not isinstance(command[0], str)
                or (command[0] == "PASS" and command != ["PASS"])):
            return None
        if (not isinstance(position, list) or len(position) != 2
                or type(position[0]) is not int or type(position[1]) is not int
                or not _strict_nonnegative_inventory(inventory)):
            return None
        x, y = position
        if not (0 <= y < len(tiles) and isinstance(tiles[y], list)
                and 0 <= x < len(tiles[y])):
            return None
        rows.append((actor, command, (x, y), inventory, tiles[y][x]))
    return rows, step


def _replace(action: dict[str, Any], replacements: dict[int, list[str]]):
    if not replacements:
        return action
    out = copy.deepcopy(action)
    commands = [out["farmer"], *out["hands"]]
    for actor, command in replacements.items():
        commands[actor] = command
    out["farmer"], out["hands"] = commands[0], commands[1:]
    return out


def _unique_pass_candidates(rows, predicate):
    """Choose only tiles with exactly one eligible literal-PASS actor."""
    candidates: dict[tuple[int, int], list[int]] = {}
    for actor, command, site, inventory, tile in rows:
        if command == ["PASS"] and predicate(tile, inventory):
            candidates.setdefault(site, []).append(actor)
    return {actors[0] for actors in candidates.values() if len(actors) == 1}


def _strict_animal(tile: Any):
    if not isinstance(tile, dict):
        return None
    animal = tile.get("animal", _MISSING)
    fed = tile.get("fed_today", _MISSING)
    cared = tile.get("cared_today", _MISSING)
    if not isinstance(animal, str) or not animal:
        return None
    if type(fed) is not bool or type(cared) is not bool:
        return None
    return animal, fed, cared


def apply_feed(action: Any, observation: Any, *, enabled: bool = False):
    """Replace one eligible PASS per tile with FEED; otherwise preserve parent identity."""
    if not enabled:
        return action
    parsed = _actor_rows(action, observation)
    if parsed is None:
        return action
    rows, _step = parsed

    def eligible(tile, inventory):
        state = _strict_animal(tile)
        wheat = inventory.get("WHEAT", 0)
        return state is not None and state[1] is False and type(wheat) is int and wheat > 0

    actors = _unique_pass_candidates(rows, eligible)
    return _replace(action, {actor: ["FEED"] for actor in actors})


def apply_care(
    action: Any,
    observation: Any,
    *,
    care_all: bool = False,
    care_goose: bool = False,
):
    """Replace eligible PASS with CARE; ``care_goose`` alone restricts to GOOSE."""
    if not care_all and not care_goose:
        return action
    parsed = _actor_rows(action, observation)
    if parsed is None:
        return action
    rows, _step = parsed

    def eligible(tile, _inventory):
        state = _strict_animal(tile)
        if state is None:
            return False
        animal, fed, cared = state
        if not fed or cared:
            return False
        return care_all or (care_goose and animal == "GOOSE")

    actors = _unique_pass_candidates(rows, eligible)
    return _replace(action, {actor: ["CARE"] for actor in actors})


def apply_wheat_fertilize(action: Any, observation: Any, *, enabled: bool = False):
    """Spend an idle PASS on a provably useful age-2..4 WHEAT fertilization."""
    if not enabled:
        return action
    parsed = _actor_rows(action, observation)
    if parsed is None:
        return action
    rows, step = parsed
    day = step // _TURNS_PER_DAY

    def eligible(tile, inventory):
        if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or tile.get("crop") != "WHEAT":
            return False
        fertilizer = inventory.get("FERTILIZER", 0)
        planted = tile.get("planted_day", _MISSING)
        coverage = tile.get("fertilized_until_day", _MISSING)
        yield_units = tile.get("yield_units", _MISSING)
        if (type(fertilizer) is not int or fertilizer <= 0
                or type(planted) is not int or planted < 0
                or type(coverage) is not int
                or type(yield_units) is not int or not 0 <= yield_units <= 6):
            return False
        age = day - planted
        # At five or six units, a fertilized +2 WATER has no marginal advantage
        # over an ordinary +1 WATER under WHEAT's six-unit cap.
        return 2 <= age <= 4 and coverage < day and yield_units <= 4

    actors = _unique_pass_candidates(rows, eligible)
    return _replace(action, {actor: ["FERTILIZE"] for actor in actors})


def apply_all(
    action: Any,
    observation: Any,
    *,
    idle_all: bool = False,
    feed_all: bool = False,
    care_all: bool = False,
    care_goose: bool = False,
    wheat_fert: bool = False,
):
    """Apply the three default-off idle layers in source order behind a global gate."""
    if not idle_all:
        return action
    out = apply_feed(action, observation, enabled=feed_all)
    out = apply_care(out, observation, care_all=care_all, care_goose=care_goose)
    out = apply_wheat_fertilize(out, observation, enabled=wheat_fert)
    return out


def install(
    parent,
    *,
    idle_all: bool = False,
    feed_all: bool = False,
    care_all: bool = False,
    care_goose: bool = False,
    wheat_fert: bool = False,
):
    """Return a wrapper; all features ship disabled unless explicitly enabled by caller."""
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        return apply_all(
            action,
            observation,
            idle_all=idle_all,
            feed_all=feed_all,
            care_all=care_all,
            care_goose=care_goose,
            wheat_fert=wheat_fert,
        )
    return agent
