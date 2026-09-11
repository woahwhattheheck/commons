# SPDX-License-Identifier: Apache-2.0
"""B5 evaluation arm: opportunistic no-detour CARROT fertilization.

This experiment is outside ``overlay/**`` and therefore cannot alter the deterministic
V3 package or submission defaults. It pins the live V3.1 R04 baseline, then replaces
only an existing literal PASS with FERTILIZE when that worker is already standing on a
CARROT plant, already carrying fertilizer, and the tile is not fertilized through the
next two days. No pathing, buying, hiring, market, or non-idle worker command changes.

The predicate is deliberately fail-closed: malformed/ambiguous action or observation
state never gets normalized into eligibility. In particular, Python bool/float/string
values are not accepted as engine integer evidence, and a falsey/missing command is not
invented as PASS.
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


def _strict_position(position):
    """Return an exact integer coordinate pair, rejecting bool/float/string aliases."""
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        return None
    x, y = position
    if type(x) is not int or type(y) is not int:
        return None
    return x, y


def _eligible(tile, inventory, day):
    """True only for a carried-fertilizer CARROT top-up with proven coverage state."""
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or tile.get("crop") != "CARROT":
        return False
    if not isinstance(inventory, dict):
        return False

    fertilizer = inventory.get("FERTILIZER", 0)
    if type(fertilizer) is not int or fertilizer <= 0:
        return False

    if "fertilized_until_day" not in tile:
        return False
    fertilized_until = tile["fertilized_until_day"]
    if type(fertilized_until) is not int:
        return False
    return fertilized_until < day + 2


def apply_carrot_fertilizer(observation, action):
    """Replace eligible literal PASS rows; malformed proof preserves exact parent identity."""
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action

    player = observation.get("player")
    step = observation.get("step")
    if type(player) is not int or player < 0 or type(step) is not int or step < 0:
        return action
    day = step // 24

    farms = observation.get("farms")
    private = observation.get("private")
    if not isinstance(farms, list) or player >= len(farms) or not isinstance(private, dict):
        return action
    farm = farms[player]
    if not isinstance(farm, dict):
        return action

    tiles = farm.get("tiles")
    farm_hands = farm.get("hands")
    farmer_position = farm.get("farmer")
    inventories = private.get("inventories")
    if not isinstance(tiles, list) or not isinstance(farm_hands, list) or not isinstance(inventories, list):
        return action

    # Require explicit command structure. Never reinterpret missing/falsey rows as PASS.
    if "farmer" not in action or "hands" not in action:
        return action
    farmer_command = action["farmer"]
    hand_commands = action["hands"]
    if not isinstance(farmer_command, list) or not isinstance(hand_commands, list):
        return action
    if any(not isinstance(command, list) for command in hand_commands):
        return action

    positions = [farmer_position, *farm_hands]
    commands = [farmer_command, *hand_commands]
    if len(positions) != len(commands) or len(inventories) != len(commands):
        return action

    # Validate the complete worker-state carrier before mutating any one actor. This keeps
    # a malformed sibling worker from turning a partially interpreted observation into an
    # apparently valid mutation.
    normalized_positions = []
    for position, inventory in zip(positions, inventories):
        coordinate = _strict_position(position)
        if coordinate is None or not isinstance(inventory, dict):
            return action
        normalized_positions.append(coordinate)

    claimed = set()
    replacements = {}
    for actor, (command, (x, y), inventory) in enumerate(
        zip(commands, normalized_positions, inventories)
    ):
        if command != ["PASS"]:
            continue
        if y < 0 or y >= len(tiles):
            continue
        row = tiles[y]
        if not isinstance(row, list) or x < 0 or x >= len(row):
            continue
        if (x, y) in claimed:
            continue
        tile = row[x]
        if not _eligible(tile, inventory, day):
            continue
        replacements[actor] = ["FERTILIZE"]
        claimed.add((x, y))

    if not replacements:
        return action

    result = copy.deepcopy(action)
    if 0 in replacements:
        result["farmer"] = replacements[0]
    for actor, replacement in replacements.items():
        if actor > 0:
            result["hands"][actor - 1] = replacement
    REPORT["carrot_fertilize_requests"] += len(replacements)
    return result


def agent(observation, configuration=None):
    return apply_carrot_fertilizer(observation, _BASE_AGENT(observation, configuration))


agent.telemetry = REPORT
