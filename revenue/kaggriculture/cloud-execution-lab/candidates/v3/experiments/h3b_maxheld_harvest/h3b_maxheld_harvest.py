# SPDX-License-Identifier: Apache-2.0
"""H3b experiment: prioritize a V233 sheep harvest only at a proven cap-loss seam.

The official interpreter caps SHEEP yield at six units.  This experiment does not
broadly move HARVEST ahead of FEED or CARE.  It only reprioritizes one of V233's
existing sheep-worker tasks when every sheep in that worker's assigned block is
already fed and cared, the worker is not carrying WOOL/FERTILIZER home, and at
least one sheep is due to produce at tonight's refresh with enough held yield to
lose units to ``max_held``.

The transform is intentionally post-policy and default-off.  When any proof is
missing, malformed, nonstandard, or inconsistent with V233's same-call work
snapshot, the exact parent action object is returned.
"""
from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

SHEEP_FIRST_YIELD_DAY = 6
SHEEP_INTERVAL = 3
SHEEP_MAX_HELD = 6
STANDARD_CONFIG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}

telemetry = Counter()
_MISSING = object()


def _cfg(configuration: Any, name: str, default: Any) -> Any:
    if configuration is None:
        return default
    try:
        if isinstance(configuration, dict):
            return configuration.get(name, default)
        return getattr(configuration, name, default)
    except Exception:
        return _MISSING


def _standard_configuration(configuration: Any) -> bool:
    for name, expected in STANDARD_CONFIG.items():
        actual = _cfg(configuration, name, expected)
        if actual is _MISSING or type(actual) is not type(expected) or actual != expected:
            return False
    return True


def _strict_sheep(tile: Any):
    if not isinstance(tile, dict) or tile.get("animal") != "SHEEP":
        return None
    placed = tile.get("placed_day", _MISSING)
    units = tile.get("yield_units", _MISSING)
    fed = tile.get("fed_today", _MISSING)
    cared = tile.get("cared_today", _MISSING)
    bonus = tile.get("pending_care_bonus", _MISSING)
    if type(placed) is not int or placed < 0:
        return None
    if type(units) is not int or not 0 <= units <= SHEEP_MAX_HELD:
        return None
    if type(fed) is not bool or type(cared) is not bool:
        return None
    if type(bonus) is not int or bonus < 0:
        return None
    return placed, units, fed, cared, bonus


def _overflow_at_next_refresh(tile: Any, day: int) -> int | None:
    state = _strict_sheep(tile)
    if state is None:
        return None
    placed, units, fed, _cared, bonus = state
    next_day = day + 1
    days_since_first = next_day - placed - SHEEP_FIRST_YIELD_DAY
    if days_since_first < 0 or days_since_first % SHEEP_INTERVAL != 0:
        return 0
    produced = 1 + (bonus if fed else 0)
    # Harvesting cannot make room when there is no held yield to remove.
    if units <= 0:
        return 0
    return max(0, units + produced - SHEEP_MAX_HELD)


def _commands(action: dict[str, Any]):
    farmer = action.get("farmer") or ["PASS"]
    hands = list(action.get("hands") or [])
    if not isinstance(farmer, list) or any(not isinstance(command, list) for command in hands):
        return None
    return [farmer, *hands]


def reprioritize(action: dict[str, Any], observation: dict[str, Any], configuration=None, *, enabled=False):
    """Return H3b action, preserving exact parent identity when the theorem is absent."""
    if not enabled:
        return action
    if not _standard_configuration(configuration):
        telemetry["nonstandard_configuration"] += 1
        return action
    try:
        step = observation["step"]
        player = observation["player"]
        if type(step) is not int or type(player) is not int or player < 0:
            return action
        day = step // 24
        # The final day has special V233 cargo-return timing and no useful post-season refresh.
        if day < 12 or day >= 29:
            return action
        farm = observation["farms"][player]
        private = observation["private"]
        tiles = farm["tiles"]
        positions = [farm["farmer"], *(farm.get("hands") or [])]
        inventories = private["inventories"]
        state = base._V233_STATES.get(player)
    except (KeyError, TypeError, IndexError, AttributeError):
        return action

    if not isinstance(state, dict) or not state.get("committed") or state.get("last_step") != step:
        return action
    workers = state.get("workers")
    work = state.get("work")
    if not isinstance(workers, dict) or not isinstance(work, dict):
        return action
    commands = _commands(action)
    if commands is None:
        return action

    replacements: list[tuple[int, list[str], int]] = []
    for actor, targets in workers.items():
        if type(actor) is not int or actor <= 0 or actor >= len(positions) or actor >= len(inventories):
            return action
        if not isinstance(targets, list) or not targets:
            return action
        snapshot = work.get(actor)
        if not isinstance(snapshot, dict) or snapshot.get("step") != step:
            return action
        parent_command = snapshot.get("command")
        if not isinstance(parent_command, list) or commands[actor] != parent_command:
            # A later layer changed the worker or the V233 accounting snapshot is ambiguous.
            return action
        inventory = inventories[actor]
        if not isinstance(inventory, dict):
            return action
        if any(type(inventory.get(item, 0)) is not int or inventory.get(item, 0) < 0
               for item in ("WOOL", "FERTILIZER")):
            return action
        if inventory.get("WOOL", 0) or inventory.get("FERTILIZER", 0):
            # Preserve V233's cargo-return priority exactly.
            continue

        parsed = []
        for order, target in enumerate(targets):
            if (not isinstance(target, (list, tuple)) or len(target) != 2
                    or type(target[0]) is not int or type(target[1]) is not int):
                return action
            x, y = target
            if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
                return action
            sheep = _strict_sheep(tiles[y][x])
            if sheep is None:
                # Never trade setup/placement/dig work for H3b.
                parsed = []
                break
            placed, units, fed, cared, bonus = sheep
            if not fed or not cared:
                # Never trade survival or the CARE+FEED compounding bonus for H3b.
                parsed = []
                break
            overflow = _overflow_at_next_refresh(tiles[y][x], day)
            if overflow is None:
                return action
            parsed.append((order, (x, y), units, overflow, placed, bonus))
        if not parsed:
            continue

        urgent = [row for row in parsed if row[3] > 0]
        if not urgent:
            continue
        pos = positions[actor]
        if (not isinstance(pos, (list, tuple)) or len(pos) != 2
                or type(pos[0]) is not int or type(pos[1]) is not int):
            return action
        urgent.sort(key=lambda row: (-row[3], abs(pos[0] - row[1][0]) + abs(pos[1] - row[1][1]), row[0]))
        _order, target, _units, overflow, _placed, _bonus = urgent[0]
        desired = base._v219_walk(tuple(pos), target) or ["HARVEST"]
        if commands[actor] == desired:
            telemetry["already_prioritized"] += 1
            continue
        replacements.append((actor, desired, overflow))

    if not replacements:
        return action

    result = copy.deepcopy(action)
    result_commands = [result.get("farmer") or ["PASS"], *(result.get("hands") or [])]
    for actor, desired, overflow in replacements:
        if actor >= len(result_commands):
            return action
        result_commands[actor] = list(desired)
    result["farmer"], result["hands"] = result_commands[0], result_commands[1:]

    # Keep V233's next-callback physical-harvest credit accounting aligned with the
    # command we actually emitted.  Do this only after all fail-closed checks pass.
    for actor, desired, overflow in replacements:
        work[actor]["command"] = list(desired)
        telemetry["overrides"] += 1
        telemetry["overflow_units_at_risk"] += overflow
    return result


def install(parent, *, enabled=False):
    """Wrap an already-configured parent agent; OFF is exact parent output identity."""
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        return reprioritize(action, observation, configuration, enabled=enabled)

    agent.telemetry = telemetry
    return agent
