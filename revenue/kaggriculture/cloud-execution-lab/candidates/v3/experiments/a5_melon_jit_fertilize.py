#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A5 experiment: spend an existing PASS on an exact MELON yield-window fertilizer seam.

The official engine makes FERTILIZE consume one carried fertilizer and cover the current
three-day interval; an annual crop WATER inside its yield window then adds two units
instead of one while covered.  This helper deliberately does *not* route a worker,
purchase fertilizer, hire, or alter market rows.  It may replace only a literal selected
PASS when the same worker's next authored command is literal WATER, the worker stays in
the same day, is already standing on an uncovered MELON inside the yield window, already
carries fertilizer, has enough yield-cap headroom for fertilizer to increase that WATER,
and has no inherited repair queue debt.

"Next authored" is intentionally weaker than "next actual action": later dynamic overlays
can still override a tape row.  The experiment reports this exact evidence boundary and
requires paired execution before any promotion claim.
"""
from __future__ import annotations

from typing import Any, Iterable

TURNS_PER_DAY = 24
MELON_MAX_YIELD_DAY = 12
MELON_WINDOW_START = (MELON_MAX_YIELD_DAY + 1) // 2  # 6
MELON_MAX_YIELD = 6


def _literal(command: Any, op: str) -> bool:
    return isinstance(command, list) and command == [op]


def _commands(action: Any) -> list[Any] | None:
    if not isinstance(action, dict):
        return None
    farmer = action.get("farmer")
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        return None
    return [farmer, *hands]


def _strict_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _worker_state(observation: dict[str, Any], worker: int):
    player = observation.get("player")
    farms = observation.get("farms")
    private = observation.get("private")
    if type(player) is not int or not isinstance(farms, list) or not (0 <= player < len(farms)):
        return None
    if not isinstance(private, dict):
        return None
    farm = farms[player]
    if not isinstance(farm, dict):
        return None
    farmer = farm.get("farmer")
    hands = farm.get("hands", [])
    tiles = farm.get("tiles")
    inventories = private.get("inventories")
    if not isinstance(hands, list) or not isinstance(tiles, list) or not isinstance(inventories, list):
        return None
    positions = [farmer, *hands]
    if not (0 <= worker < len(positions) and worker < len(inventories)):
        return None
    position = positions[worker]
    inventory = inventories[worker]
    if (
        not isinstance(position, list)
        or len(position) != 2
        or type(position[0]) is not int
        or type(position[1]) is not int
        or not isinstance(inventory, dict)
    ):
        return None
    x, y = position
    if not (0 <= y < len(tiles) and isinstance(tiles[y], list) and 0 <= x < len(tiles[y])):
        return None
    return tiles[y][x], inventory, (x, y)


def _melon_qualifies(tile: Any, inventory: dict[str, Any], day: int) -> tuple[bool, str]:
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or tile.get("crop") != "MELON":
        return False, "not_melon"

    fertilizer = _strict_nonnegative_int(inventory.get("FERTILIZER", 0))
    planted_day = tile.get("planted_day")
    yield_units = _strict_nonnegative_int(tile.get("yield_units"))
    fertilized_until = tile.get("fertilized_until_day")
    watered_today = tile.get("watered_today")
    if fertilizer is None or fertilizer <= 0:
        return False, "no_fertilizer"
    if type(planted_day) is not int or type(fertilized_until) is not int or type(watered_today) is not bool:
        return False, "malformed_tile"
    if yield_units is None:
        return False, "malformed_yield"
    if watered_today:
        return False, "already_watered"
    if fertilized_until >= day:
        return False, "already_covered"

    # Fertilizer is useful only if it changes the next WATER result.  Near the cap,
    # baseline +1 and fertilized +2 can collapse to the same capped yield; spending
    # a PASS and one fertilizer there is pure opportunity cost.
    baseline_after_water = min(MELON_MAX_YIELD, yield_units + 1)
    fertilized_after_water = min(MELON_MAX_YIELD, yield_units + 2)
    if fertilized_after_water <= baseline_after_water:
        return False, "no_marginal_yield"

    age = day - planted_day
    if not (MELON_WINDOW_START <= age <= MELON_MAX_YIELD_DAY):
        return False, "outside_yield_window"
    return True, "eligible"


def apply_melon_jit_fertilize(
    action: Any,
    observation: Any,
    next_authored: Any,
    *,
    blocked_workers: Iterable[int] = (),
    enabled: bool = False,
) -> tuple[Any, tuple[dict[str, Any], ...]]:
    """Return ``(action, activations)``; all no-match paths preserve object identity."""
    if not enabled or not isinstance(action, dict) or not isinstance(observation, dict):
        return action, ()
    step = observation.get("step")
    if type(step) is not int or step < 0:
        return action, ()
    next_step = step + 1
    # Same-day authored WATER only; do not predict the dawn reset or route-plan boundary.
    if step // TURNS_PER_DAY != next_step // TURNS_PER_DAY:
        return action, ()

    selected = _commands(action)
    following = _commands(next_authored)
    if selected is None or following is None:
        return action, ()

    blocked: set[int] = set()
    for worker in blocked_workers:
        if type(worker) is not int or worker < 0:
            return action, ()
        blocked.add(worker)

    day = step // TURNS_PER_DAY
    matches: list[tuple[int, tuple[int, int], int, int]] = []
    claimed_positions: set[tuple[int, int]] = set()
    for worker in range(min(len(selected), len(following))):
        if worker in blocked:
            continue
        if not _literal(selected[worker], "PASS") or not _literal(following[worker], "WATER"):
            continue
        state = _worker_state(observation, worker)
        if state is None:
            continue
        tile, inventory, position = state
        if position in claimed_positions:
            continue
        ok, _ = _melon_qualifies(tile, inventory, day)
        if not ok:
            continue
        fertilizer = inventory["FERTILIZER"]
        age = day - tile["planted_day"]
        matches.append((worker, position, fertilizer, age))
        claimed_positions.add(position)

    if not matches:
        return action, ()

    out = dict(action)
    original_hands = action.get("hands", [])
    hands_copy = None
    activations: list[dict[str, Any]] = []
    for worker, position, fertilizer, age in matches:
        if worker == 0:
            out["farmer"] = ["FERTILIZE"]
        else:
            if not isinstance(original_hands, list) or worker - 1 >= len(original_hands):
                continue
            if hands_copy is None:
                hands_copy = [list(command) if isinstance(command, list) else command for command in original_hands]
                out["hands"] = hands_copy
            hands_copy[worker - 1] = ["FERTILIZE"]
        activations.append({
            "step": step,
            "worker": worker,
            "crop": "MELON",
            "position": [position[0], position[1]],
            "age_days": age,
            "fertilizer_before": fertilizer,
            "authored_water_step": next_step,
            "reason": "literal_pass_before_same_worker_authored_melon_yield_water",
        })

    if not activations:
        return action, ()
    return out, tuple(activations)
