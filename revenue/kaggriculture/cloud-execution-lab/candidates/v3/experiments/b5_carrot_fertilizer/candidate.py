# SPDX-License-Identifier: Apache-2.0
"""B5 evaluation arm: opportunistic no-detour CARROT fertilization.

This experiment is outside ``overlay/**`` and therefore cannot alter the deterministic
V3 package or submission defaults. It pins the live V3.1 R04 baseline, then replaces
only an already-idle literal PASS with FERTILIZE when that worker is already standing
on a CARROT plant, already carries fertilizer, and the tile is not fertilized through
the next two days. Malformed or type-ambiguous state preserves the parent action.
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


def _strict_int(value):
    """Return exact JSON integer values only; bool/float/string are malformed here."""
    return value if type(value) is int else None


def _eligible(tile, inventory, day):
    """True only for an exactly typed carried-fertilizer CARROT top-up."""
    if type(tile) is not dict or type(inventory) is not dict:
        return False
    if tile.get("kind") != "PLANT" or tile.get("crop") != "CARROT":
        return False
    fertilizer = _strict_int(inventory.get("FERTILIZER", 0))
    coverage = _strict_int(tile.get("fertilized_until_day"))
    return (
        fertilizer is not None
        and fertilizer > 0
        and coverage is not None
        and coverage < day + 2
    )


def apply_carrot_fertilizer(observation, action):
    """Replace exact PASS rows; malformed/ambiguous state returns exact parent identity."""
    if type(observation) is not dict or type(action) is not dict:
        return action

    player = _strict_int(observation.get("player"))
    step = _strict_int(observation.get("step"))
    if player is None or player < 0 or step is None or step < 0:
        return action

    farms = observation.get("farms")
    private = observation.get("private")
    if type(farms) is not list or player >= len(farms) or type(private) is not dict:
        return action
    farm = farms[player]
    if type(farm) is not dict:
        return action

    tiles = farm.get("tiles")
    farmer_position = farm.get("farmer")
    hand_positions = farm.get("hands")
    inventories = private.get("inventories")
    farmer_command = action.get("farmer")
    hand_commands = action.get("hands")
    if (
        type(tiles) is not list
        or type(farmer_position) is not list
        or type(hand_positions) is not list
        or type(inventories) is not list
        or type(farmer_command) is not list
        or type(hand_commands) is not list
    ):
        return action

    positions = [farmer_position, *hand_positions]
    commands = [farmer_command, *hand_commands]
    if len(commands) != len(positions) or len(inventories) != len(positions):
        return action

    # Validate actor coordinates/inventory shapes before mutating any row. A malformed
    # unrelated hand must not partially admit a transform for another actor.
    actor_cells = []
    for position, inventory in zip(positions, inventories):
        if type(position) is not list or len(position) < 2 or type(inventory) is not dict:
            return action
        x = _strict_int(position[0])
        y = _strict_int(position[1])
        if x is None or y is None or y < 0 or y >= len(tiles):
            return action
        row = tiles[y]
        if type(row) is not list or x < 0 or x >= len(row):
            return action
        actor_cells.append((x, y, row[x]))

    day = step // 24
    claimed = set()
    changed = False
    next_commands = list(commands)

    for actor, (command, inventory, cell) in enumerate(zip(commands, inventories, actor_cells)):
        # Do not synthesize a PASS from missing/falsey/malformed command rows.
        if command != ["PASS"]:
            continue
        x, y, tile = cell
        if (x, y) in claimed or not _eligible(tile, inventory, day):
            continue
        next_commands[actor] = ["FERTILIZE"]
        claimed.add((x, y))
        REPORT["carrot_fertilize_requests"] += 1
        changed = True

    if not changed:
        return action
    result = copy.deepcopy(action)
    result["farmer"] = next_commands[0]
    result["hands"] = next_commands[1:]
    return result


def agent(observation, configuration=None):
    return apply_carrot_fertilizer(observation, _BASE_AGENT(observation, configuration))


agent.telemetry = REPORT
