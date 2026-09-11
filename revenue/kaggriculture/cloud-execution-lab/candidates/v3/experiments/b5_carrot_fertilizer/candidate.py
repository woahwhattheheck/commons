# SPDX-License-Identifier: Apache-2.0
"""B5 evaluation arm: opportunistic no-detour CARROT fertilization.

This experiment is outside ``overlay/**`` and therefore cannot alter the deterministic
V3 package or submission defaults. It pins the live V3.1 R04 baseline, then replaces
only an already-authored literal PASS with FERTILIZE when that worker is already standing
on a CARROT plant, already carrying fertilizer, and the tile is not fertilized through
the next two days. Malformed or non-canonical state fails closed to the parent action.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
MODULE_ROOT = OVERLAY if OVERLAY.is_dir() else V3_ROOT
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import r04_full_router as base  # noqa: E402

LIVE_BASELINE = {
    "horizon": 8,
    "opening": 0,
    "row_order": True,
    "evening_flush": True,
    "sale_fertilizer": True,
    "cattle_early": True,
}
_BASE_AGENT = base.install(**LIVE_BASELINE)
REPORT = {"carrot_fertilize_requests": 0}


def _int(value):
    """Engine integers only; bool/float/string coercions are not evidence."""
    return type(value) is int


def _eligible(tile, inventory, day):
    """True only for a carried-fertilizer CARROT top-up with canonical integer state."""
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


def _actor_rows_valid(commands, positions, inventories, tiles):
    """Validate every actor before any replacement is collected.

    The transform is whole-action fail-closed: a malformed later hand may not
    leave an earlier farmer/hand rewrite behind.  Parent R04 emits list-valued
    worker commands with a string opcode, public positions are two exact ints
    inside the visible board, and each actor has a dict inventory.
    """
    for command, position, inventory in zip(commands, positions, inventories):
        if not isinstance(command, list) or not command or type(command[0]) is not str:
            return False
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 2
            or not _int(position[0])
            or not _int(position[1])
        ):
            return False
        if not isinstance(inventory, dict):
            return False
        x, y = position
        if y < 0 or y >= len(tiles) or not isinstance(tiles[y], list) or x < 0 or x >= len(tiles[y]):
            return False
    return True


def apply_carrot_fertilizer(observation, action):
    """Replace eligible literal PASS rows; malformed inputs preserve parent identity."""
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
    if not _actor_rows_valid(commands, positions, inventories, tiles):
        return action

    day = step // 24
    claimed = set()
    replacements = {}
    for actor, (command, position, inventory) in enumerate(zip(commands, positions, inventories)):
        if command != ["PASS"]:
            continue
        x, y = position
        if (x, y) in claimed:
            continue
        tile = tiles[y][x]
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
    REPORT["carrot_fertilize_requests"] += len(replacements)
    return result


def agent(observation, configuration=None):
    return apply_carrot_fertilizer(observation, _BASE_AGENT(observation, configuration))


agent.telemetry = REPORT
