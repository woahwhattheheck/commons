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


def _eligible(tile, inventory, day):
    """True only for a carried-fertilizer CARROT top-up with three-day coverage."""
    return (
        isinstance(tile, dict)
        and tile.get("kind") == "PLANT"
        and tile.get("crop") == "CARROT"
        and int(inventory.get("FERTILIZER", 0)) > 0
        and int(tile.get("fertilized_until_day", -1)) < day + 2
    )


def apply_carrot_fertilizer(observation, action):
    """Replace eligible PASS rows without touching the caller's action object."""
    player = int(observation["player"])
    day = int(observation["step"]) // 24
    farm = observation["farms"][player]
    private = observation["private"]
    inventories = private.get("inventories") or []
    positions = [farm["farmer"], *(farm.get("hands") or [])]
    commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    claimed = set()
    changed = False

    for actor, (command, position) in enumerate(zip(commands, positions)):
        if command != ["PASS"] or actor >= len(inventories):
            continue
        try:
            x, y = int(position[0]), int(position[1])
            if not (0 <= y < len(farm["tiles"]) and 0 <= x < len(farm["tiles"][y])):
                continue
            if (x, y) in claimed:
                continue
            tile = farm["tiles"][y][x]
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if not _eligible(tile, inventories[actor] or {}, day):
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
