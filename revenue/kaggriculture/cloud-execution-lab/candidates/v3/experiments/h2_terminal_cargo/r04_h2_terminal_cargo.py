# SPDX-License-Identifier: Apache-2.0
"""V3.1 H2 experiment: deadline return for terminal worker cargo.

This is a default-off live-R04 experiment, not a packaged policy change.  The
published R04 policy already liquidates shed stock on LAST_STEP, and that
liquidation drops worker inventory only when the worker is already on one of
the central shed cells.  H2 protects only the logistics predecessor: when a
worker carrying a product is one movement deadline (or one turn of slack) from
missing that terminal drop, route it toward the nearest shed cell and keep it
there.  Market rows are never changed here; the existing parent liquidation
remains the only terminal sale mechanism.

The wrapper deliberately does not harvest, water, pick up, choose sale
quantities, reorder market rows, or create sale-window debt.  Cargo that is
already too far away to reach the shed by LAST_STEP is left untouched rather
than sacrificing work for an impossible return.
"""

from __future__ import annotations

import copy

import r04_full_router as base

KEY = "r04_terminal_cargo_return"
TERMINAL_CARGO_RETURN = False
FIRST_STEP = 696


def _positions(observation):
    farm = observation["farms"][observation["player"]]
    return [farm["farmer"], *farm["hands"]]


def _nearest_shed_cell(position, tiles):
    center = len(tiles) // 2
    cells = ((center - 1, center - 1), (center, center - 1),
             (center - 1, center), (center, center))
    pos = tuple(position)
    return min(cells, key=lambda cell: (
        abs(pos[0] - cell[0]) + abs(pos[1] - cell[1]), cell))


def _product_units(inventory):
    return sum(max(0, int(inventory.get(item, 0))) for item in base.PRODUCTS)


def protect_terminal_cargo(action, observation, enabled=False, first_step=FIRST_STEP):
    """Return ``(action, changed_workers, protected_units)`` for H2.

    Disabled/ineligible calls return the exact input object.  A worker is
    eligible only if product cargo is physically able to reach a shed cell by
    LAST_STEP and is at the point where at most one turn of schedule slack
    remains.  The worker then walks toward the nearest shed cell.  Once there,
    H2 replaces only a command that would move/work away with PASS so the
    unchanged R04 LAST_STEP liquidation can DROP and SELL the cargo.
    """
    if not enabled:
        return action, 0, 0

    step = int(observation["step"])
    first_step = int(first_step)
    if first_step < 0:
        raise ValueError("first_step must be non-negative")
    if step < first_step or step >= base.LAST_STEP:
        return action, 0, 0

    player = int(observation["player"])
    farm = observation["farms"][player]
    private = observation["private"]
    positions = _positions(observation)
    inventories = private.get("inventories") or []
    commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    if len(commands) < len(positions):
        commands += [["PASS"] for _ in range(len(positions) - len(commands))]

    remaining = base.LAST_STEP - step
    replacements = {}
    protected_units = 0

    for worker in range(min(len(positions), len(inventories))):
        inventory = inventories[worker] or {}
        units = _product_units(inventory)
        if units <= 0:
            continue

        position = tuple(positions[worker])
        home = _nearest_shed_cell(position, farm["tiles"])
        distance = abs(position[0] - home[0]) + abs(position[1] - home[1])

        # Already impossible: do not burn the final actions on a return that
        # cannot reach a shed cell before the parent's terminal liquidation.
        if distance > remaining:
            continue
        # More than one full turn of schedule slack remains.
        if distance + 1 < remaining:
            continue

        if distance:
            replacement = base._v219_walk(position, home)
            if replacement is None:
                continue
        else:
            current = commands[worker]
            operation = current[0] if current else "PASS"
            # Preserve actions that already keep/unload the worker at home.
            if operation in ("PASS", "DROP", "PLACE"):
                continue
            replacement = ["PASS"]

        if replacement != commands[worker]:
            replacements[worker] = list(replacement)
            protected_units += units

    if not replacements:
        return action, 0, 0

    result = copy.deepcopy(action)
    result_commands = [result.get("farmer") or ["PASS"], *(result.get("hands") or [])]
    if len(result_commands) < len(positions):
        result_commands += [["PASS"] for _ in range(len(positions) - len(result_commands))]
    for worker, replacement in replacements.items():
        result_commands[worker] = replacement
    result["farmer"], result["hands"] = result_commands[0], result_commands[1:]
    return result, len(replacements), protected_units


H2_REPORT = {
    "terminal_cargo_activations": 0,
    "terminal_cargo_workers": 0,
    "terminal_cargo_units": 0,
}


def h2_agent(observation, configuration=None):
    """Exact live V3.1 parent plus the default-off H2 worker-return wrapper."""
    action = base.v3_agent(observation, configuration)
    if not TERMINAL_CARGO_RETURN:
        return action
    result, changed, units = protect_terminal_cargo(
        action, observation, enabled=True, first_step=FIRST_STEP)
    if changed:
        H2_REPORT["terminal_cargo_activations"] += 1
        H2_REPORT["terminal_cargo_workers"] += changed
        H2_REPORT["terminal_cargo_units"] += units
    return result


h2_agent.telemetry = H2_REPORT


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None, terminal_cargo_return=None,
            terminal_cargo_first_step=None):
    """Configure exact parent R04 parameters and return the H2 experiment agent."""
    global TERMINAL_CARGO_RETURN, FIRST_STEP
    base.install(host, horizon, opening, row_order, evening_flush,
                 sale_fertilizer, cattle_early)
    if terminal_cargo_return is not None:
        TERMINAL_CARGO_RETURN = bool(terminal_cargo_return)
    if terminal_cargo_first_step is not None:
        terminal_cargo_first_step = int(terminal_cargo_first_step)
        if terminal_cargo_first_step < 0 or terminal_cargo_first_step >= base.LAST_STEP:
            raise ValueError("terminal_cargo_first_step must be in [0, LAST_STEP)")
        FIRST_STEP = terminal_cargo_first_step
    return h2_agent
