# SPDX-License-Identifier: Apache-2.0
"""B5 evaluation arm: opportunistic no-detour CARROT fertilization.

This experiment is outside ``overlay/**`` and therefore cannot alter the deterministic
V3 package or submission defaults.  It pins the live V3.1 R04 baseline, then replaces
only an already-idle PASS with FERTILIZE when that worker is already standing on a
CARROT plant, already carrying fertilizer, and the tile is not fertilized through the
next two days.  No pathing, buying, hiring, market, or non-idle worker command changes.
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


def _strict_position(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and type(value[0]) is int
        and type(value[1]) is int
    )


def _eligible(tile, inventory, day):
    """True only for a carried-fertilizer CARROT top-up with three-day coverage."""
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or tile.get("crop") != "CARROT":
        return False
    if not isinstance(inventory, dict):
        return False
    fertilizer = inventory.get("FERTILIZER", 0)
    if type(fertilizer) is not int or fertilizer <= 0:
        return False
    if "fertilized_until_day" not in tile:
        return False
    covered_through = tile["fertilized_until_day"]
    return type(covered_through) is int and covered_through < day + 2


def apply_carrot_fertilizer(observation, action):
    """Replace eligible literal PASS rows; malformed state preserves parent identity."""
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or step < 0 or type(player) is not int or player < 0:
        return action

    farms = observation.get("farms")
    private = observation.get("private")
    if not isinstance(farms, list) or player >= len(farms) or not isinstance(private, dict):
        return action
    farm = farms[player]
    if not isinstance(farm, dict):
        return action
    tiles = farm.get("tiles")
    farmer_position = farm.get("farmer")
    hand_positions = farm.get("hands")
    inventories = private.get("inventories")
    if (
        not isinstance(tiles, list)
        or not _strict_position(farmer_position)
        or not isinstance(hand_positions, list)
        or not all(_strict_position(position) for position in hand_positions)
        or not isinstance(inventories, list)
    ):
        return action

    if "farmer" not in action or "hands" not in action:
        return action
    farmer_command = action["farmer"]
    hand_commands = action["hands"]
    if (
        not isinstance(farmer_command, list)
        or not farmer_command
        or not isinstance(hand_commands, list)
        or len(hand_commands) != len(hand_positions)
        or not all(isinstance(command, list) and command for command in hand_commands)
    ):
        return action

    positions = [farmer_position, *hand_positions]
    commands = [farmer_command, *hand_commands]
    if len(inventories) < len(positions) or any(
        not isinstance(inventories[actor], dict) for actor in range(len(positions))
    ):
        return action

    day = step // 24
    claimed = set()
    changed = False
    for actor, (command, position) in enumerate(zip(commands, positions)):
        if command != ["PASS"]:
            continue
        x, y = position
        if not (0 <= y < len(tiles)):
            continue
        row = tiles[y]
        if not isinstance(row, list) or not (0 <= x < len(row)):
            continue
        if (x, y) in claimed:
            continue
        tile = row[x]
        if not _eligible(tile, inventories[actor], day):
            continue
        commands[actor] = ["FERTILIZE"]
        claimed.add((x, y))
        REPORT["carrot_fertilize_requests"] += 1
        changed = True

    if not changed:
        return action
    result = copy.deepcopy(action)
    result["farmer"] = commands[0]
    result["hands"] = commands[1:]
    return result


def agent(observation, configuration=None):
    return apply_carrot_fertilizer(observation, _BASE_AGENT(observation, configuration))


agent.telemetry = REPORT
