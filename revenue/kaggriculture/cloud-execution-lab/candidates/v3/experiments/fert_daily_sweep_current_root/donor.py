# SPDX-License-Identifier: Apache-2.0
"""R04 lane B5 "fert-daily-sweep": collect each day's free fertilizer with idle workers.

Attaches in r04_full_router.v3_agent between POLICY_AGENT and the ROW_ORDER block,
behind the TITAN-CONFIG.json key r04_fert_daily_sweep (default False). Every animal
tile sets ``fertilizer_available = True`` once per day and the flag is a boolean:
a unit not collected before the next daily transition evaporates and never stacks.
The published shop-router tapes already collect while passing through, and the V218
layer sweeps terminally at steps 712-718, but any PASS (idle) worker standing on an
animal tile whose flag is still set is a free unit the route leaves to evaporate.

When the r04_full_router.FERT_DAILY_SWEEP module flag is on, every worker whose
command is exactly ["PASS"] is considered for two rewrites; no other command is
ever touched, so higher-value tape work is never displaced:

  collect - the worker stands on a tile with an animal and
            ``fertilizer_available`` set: the PASS becomes ["COLLECT_FERTILIZER"].
            The worker does not move, so the tape's position-dependent route is
            undisturbed and the next step's orders apply normally. Two workers on
            the same tile in one step collect only once (the second collection
            would be an engine no-op); the tile is claimed per step.
  deliver - the worker is beside the shed, holds FERTILIZER, holds no animal
            items (a DROP would otherwise strand a tape-planned PLACE), and the
            tape plans no FERTILIZE or FEED for that worker for the rest of the
            day (both consume worker inventory): the PASS becomes ["DROP"], which
            moves the worker's cargo into the shed the same step. Delivery is
            authorized only when strict current shed + every parent DROP cargo +
            every new DROP cargo fits the engine-resolved shedCapacity supplied by
            the caller. If capacity or inventory evidence is malformed, all new
            DROPs fail closed to PASS. This needs the route tape; when tape is None
            the deliver half is skipped and only collection runs. Fertilizer that
            is not dropped same-day still reaches the shed through the tape's own
            DROP rows or the end-of-day inventory sweep.

Early sale needs no new market rows: with the V3.1 default r04_sale_fertilizer on,
the E184 sale window's reserve_sales already advances the tape's planned
FERTILIZER SELL rows whenever projected shed stock exists, and fertilizer's price
curve only falls as market supply accumulates, so same-day shed delivery is what
routes the units into early sales. The lane adds no market rows itself and never
exceeds the market-order budget.

The layer never raises: any unexpected observation shape leaves the action
unchanged. Standard library only.
"""

from __future__ import annotations

_PASS = ["PASS"]
_COLLECT = ["COLLECT_FERTILIZER"]
_DROP = ["DROP"]
_DEFAULT_SHED_CAPACITY = 100

# Worker-inventory consumers the deliver half must not starve: FERTILIZE takes
# FERTILIZER, FEED takes WHEAT. (PLACE takes animal items; those are excluded by
# the no-animals-in-inventory rule instead.)
_INVENTORY_WORK = ("FERTILIZE", "FEED")

# Animal item keys, mirroring the engine's ANIMALS. A worker holding one of these
# beside the shed is waiting on a tape-planned PLACE, never a DROP candidate.
_ANIMALS = ("GOOSE", "COW", "SHEEP")

# Marker for "no tile could be read under this worker" (malformed observation or
# an out-of-range position). Distinct from a None tile, on which nothing happens.
_UNKNOWN = object()


def _fresh_report():
    return {
        "steps_active": 0,
        "collected": 0,
        "dropped": 0,
        "collect_skipped_claimed": 0,
        "drop_skipped_guard": 0,
    }


# Module-level report: steps where the layer ran, units collected/dropped, and
# guard skips. reset() restores the zeros (for tests).
report = _fresh_report()


def reset():
    """Restore the module-level report counters to zero."""
    report.clear()
    report.update(_fresh_report())


def get_report():
    """Return a copy of the module-level report counters."""
    return dict(report)


def _worker_tile(tiles, position):
    """Return the tile under a worker, or _UNKNOWN when it cannot be read.

    Out-of-range positions are unknowable (Python negative indices would
    otherwise silently wrap to a real tile); a worker whose tile is unknowable
    keeps its PASS.
    """
    try:
        x, y = position
        if isinstance(x, bool) or isinstance(y, bool):
            return _UNKNOWN
        if not isinstance(x, int) or not isinstance(y, int):
            return _UNKNOWN
        if y < 0 or y >= len(tiles):
            return _UNKNOWN
        row = tiles[y]
        if x < 0 or x >= len(row):
            return _UNKNOWN
        return row[x]
    except Exception:
        return _UNKNOWN


def _beside_shed(tiles, position):
    """True when the worker stands on a shed-access tile."""
    try:
        center = len(tiles) // 2
        x, y = position
        return x in (center - 1, center) and y in (center - 1, center)
    except Exception:
        return False


def _has_inventory_work(tape, worker, step):
    """True when the tape plans FERTILIZE/FEED for this worker later today.

    Both consume worker inventory, so a DROP now would starve them. Fails
    closed: an unreadable tape counts as "has work" and the DROP is skipped.
    """
    try:
        day_end = (int(step) // 24 + 1) * 24
        for future in range(int(step) + 1, min(day_end, len(tape))):
            planned = tape[future]
            commands = [planned.get("farmer")] + list(planned.get("hands") or [])
            if worker >= len(commands):
                continue
            command = commands[worker] or _PASS
            if command and command[0] in _INVENTORY_WORK:
                return True
        return False
    except Exception:
        return True


def _collectable(tile):
    """True when the engine's COLLECT_FERTILIZER would succeed on this tile."""
    return (
        isinstance(tile, dict)
        and "animal" in tile
        and bool(tile.get("fertilizer_available"))
    )


def _strict_nonnegative_int(value):
    return type(value) is int and value >= 0


def _strict_inventory_total(inventory):
    """Return exact cargo units, or None when capacity evidence is ambiguous."""
    if not isinstance(inventory, dict):
        return None
    total = 0
    for value in inventory.values():
        if not _strict_nonnegative_int(value):
            return None
        total += value
    return total


def _drop_capacity_safe(observation, positions, inventories, commands, candidates, shed_capacity):
    """Prove parent DROPs plus all proposed DROPs fit the configured shed.

    PICKUP actions are intentionally ignored: treating their shed release as zero is
    conservative. Existing DROP cargo is included even when its worker might fail to
    reach the shed, so a new DROP can never consume capacity a parent DROP may need.
    """
    try:
        if type(shed_capacity) is not int or shed_capacity < 0:
            return False
        private = observation.get("private")
        if not isinstance(private, dict):
            return False
        shed_total = _strict_inventory_total(private.get("shed"))
        if shed_total is None or shed_total > shed_capacity:
            return False
        if not isinstance(inventories, list) or len(commands) > len(positions):
            return False
        candidate_set = set(candidates)
        cargo_total = 0
        for index, command in enumerate(commands):
            if command != _DROP and index not in candidate_set:
                continue
            if index >= len(inventories):
                return False
            cargo = _strict_inventory_total(inventories[index])
            if cargo is None:
                return False
            cargo_total += cargo
        return shed_total + cargo_total <= shed_capacity
    except Exception:
        return False


def apply_fert_daily_sweep(observation, action, tape=None, shed_capacity=_DEFAULT_SHED_CAPACITY):
    """Rewrite idle workers into fertilizer collection/delivery; never raises.

    ``shed_capacity`` must be the exact integer capacity the engine will use for
    this game. Returns the action unchanged when capacity/observation/action is
    malformed, when nothing qualifies, or when tape is None and no collection
    applies (the deliver half needs the tape for its inventory-work guard).
    """
    try:
        return _apply(observation, action, tape, shed_capacity)
    except Exception:
        return action


def _apply(observation, action, tape, shed_capacity):
    try:
        step = int(observation["step"])
    except Exception:
        return action
    if not isinstance(action, dict):
        return action
    try:
        farm = observation["farms"][observation["player"]]
        tiles = farm["tiles"]
        positions = [farm["farmer"]] + list(farm.get("hands") or [])
        inventories = (observation.get("private") or {}).get("inventories") or []
    except Exception:
        return action
    farmer_command = action.get("farmer")
    hand_commands = action.get("hands") or []
    commands = [farmer_command] + list(hand_commands)

    report["steps_active"] += 1
    changed = False
    claimed = set()
    drop_candidates = []
    new_commands = list(commands)
    for index, (command, position) in enumerate(zip(commands, positions)):
        # Budget rule: only idle workers are ever touched. Any real command,
        # including a V218 terminal task, is left exactly as the route issued it.
        if command != _PASS:
            continue
        try:
            tile = _worker_tile(tiles, position)
        except Exception:
            continue
        if tile is _UNKNOWN:
            continue
        try:
            inventory = inventories[index] if index < len(inventories) else {}
            if not isinstance(inventory, dict):
                inventory = {}
        except Exception:
            inventory = {}
        if _collectable(tile):
            x, y = position
            if (x, y) in claimed:
                # Two actors on one tile: the engine would no-op the second
                # collection, so keep the second worker's PASS.
                report["collect_skipped_claimed"] += 1
                continue
            claimed.add((x, y))
            new_commands[index] = list(_COLLECT)
            report["collected"] += 1
            changed = True
            continue
        # Deliver half: needs the tape for the inventory-work guard.
        if tape is None:
            continue
        if not _beside_shed(tiles, position):
            continue
        fertilizer = inventory.get("FERTILIZER", 0)
        if not _strict_nonnegative_int(fertilizer) or fertilizer <= 0:
            continue
        if any(item in _ANIMALS for item in inventory):
            # A held animal is waiting on a tape-planned PLACE; a DROP would
            # strand it in the shed.
            report["drop_skipped_guard"] += 1
            continue
        if _has_inventory_work(tape, index, step):
            report["drop_skipped_guard"] += 1
            continue
        drop_candidates.append(index)

    if drop_candidates:
        if _drop_capacity_safe(observation, positions, inventories, commands, drop_candidates, shed_capacity):
            for index in drop_candidates:
                new_commands[index] = list(_DROP)
            report["dropped"] += len(drop_candidates)
            changed = True
        else:
            report["drop_skipped_guard"] += len(drop_candidates)

    if not changed:
        return action
    new_action = dict(action)
    new_action["farmer"] = new_commands[0]
    new_action["hands"] = new_commands[1:]
    return new_action
