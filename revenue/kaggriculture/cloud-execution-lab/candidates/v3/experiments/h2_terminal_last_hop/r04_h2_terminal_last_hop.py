# SPDX-License-Identifier: Apache-2.0
"""H2 experiment: rescue terminal product cargo only on a proven last-hop idle seam.

Frozen V3.1's parent liquidation runs at step 718.  It DROPs worker inventory only
for workers already beside the shed, then sells the projected shed.  Therefore a
worker that enters step 718 one tile away with product cargo has no remaining action
that can monetize that cargo.

This experiment is intentionally much narrower than an older unpublished H2 draft.
It changes exactly one worker command only when all of these are proven at step 717:

* the parent's command for that worker is literal PASS;
* the worker holds positive product cargo and is exactly one legal move from a free
  shed-adjacent cell;
* no other worker is moving this turn;
* every other worker command is storage-neutral / non-producing (no HARVEST or
  COLLECT_FERTILIZER), and every market row is SELL-only, so current private stock is
  a conservative upper bound on stock that can exist at liquidation;
* current shed stock plus every worker's carried product cargo fits the standard
  100-unit shed, preventing the official DROP overflow/destruction edge case; and
* the observation/configuration shapes and scalar types are exact standard forms.

The wrapper never changes market rows, sale-window debt, prices, worker work before
step 717, or step-718 liquidation.  Any ambiguity returns the exact parent action
object.  It is default-OFF and requires an exact-interpreter activation/realization
census before score spend.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Mapping, Sequence

import r04_full_router as base


STANDARD_CONFIG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}
RESCUE_STEP = 717
SAFE_OTHER_WORK = {
    "PASS", "DROP", "PLACE", "PICKUP", "CARE", "FEED", "WATER", "DIG",
    "PLANT", "BUILD_COOP", "BUILD_PASTURE",
}
_MISSING = object()

telemetry = Counter()


def _exact_config_value(configuration: Any, name: str):
    if isinstance(configuration, Mapping):
        return configuration[name] if name in configuration else _MISSING
    if configuration is None:
        return _MISSING
    try:
        return getattr(configuration, name)
    except Exception:
        return _MISSING


def _standard_configuration(configuration: Any) -> bool:
    for name, expected in STANDARD_CONFIG.items():
        actual = _exact_config_value(configuration, name)
        if type(actual) is not int or actual != expected:
            return False
    return True


def _strict_coord(value: Any, size: int):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    x, y = value
    if type(x) is not int or type(y) is not int:
        return None
    if not 0 <= x < size or not 0 <= y < size:
        return None
    return (x, y)


def _shed_cells(size: int):
    center = size // 2
    return (
        (center - 1, center - 1),
        (center, center - 1),
        (center - 1, center),
        (center, center),
    )


def _strict_inventory(inventory: Any):
    """Return product-unit total; positive non-product cargo is ambiguous -> None."""
    if not isinstance(inventory, Mapping):
        return None
    total = 0
    for item, quantity in inventory.items():
        if type(quantity) is not int or quantity < 0:
            return None
        if quantity == 0:
            continue
        if item not in base.PRODUCTS:
            return None
        total += quantity
    return total


def _strict_shed_total(shed: Any):
    if not isinstance(shed, Mapping):
        return None
    total = 0
    for _item, quantity in shed.items():
        if type(quantity) is not int or quantity < 0:
            return None
        total += quantity
    return total


def _strict_commands(action: Any, hand_count: int):
    if not isinstance(action, Mapping):
        return None
    farmer = action.get("farmer", _MISSING)
    hands = action.get("hands", _MISSING)
    if not isinstance(farmer, list) or not farmer or not isinstance(hands, list):
        return None
    if len(hands) != hand_count:
        return None
    commands = [farmer, *hands]
    for command in commands:
        if not isinstance(command, list) or not command or not isinstance(command[0], str):
            return None
    return commands


def _sell_only_market(action: Mapping[str, Any]) -> bool:
    market = action.get("market", _MISSING)
    if not isinstance(market, list):
        return False
    for row in market:
        if row in (None, []):
            continue
        if not isinstance(row, list) or not row or row[0] != "SELL":
            return False
        if len(row) < 3 or row[1] not in base.PRODUCTS:
            return False
        if type(row[2]) is not int or row[2] < 0:
            return False
    return True


def rescue_last_hop(action: Any, observation: Any, configuration: Any, *, enabled: bool):
    """Return ``(action, actor, protected_units)``; exact identity on every no-op path."""
    if type(enabled) is not bool:
        raise TypeError("enabled must be a bool")
    if not enabled:
        return action, None, 0
    if not _standard_configuration(configuration):
        telemetry["nonstandard_configuration"] += 1
        return action, None, 0
    if not isinstance(observation, Mapping):
        return action, None, 0

    step = observation.get("step", _MISSING)
    player = observation.get("player", _MISSING)
    if type(step) is not int or step != RESCUE_STEP:
        return action, None, 0
    if type(player) is not int or player not in (0, 1):
        return action, None, 0

    farms = observation.get("farms", _MISSING)
    private = observation.get("private", _MISSING)
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        return action, None, 0
    if not isinstance(private, Mapping) or not isinstance(farms[player], Mapping):
        return action, None, 0
    farm = farms[player]

    size = STANDARD_CONFIG["boardSize"]
    tiles = farm.get("tiles", _MISSING)
    hands = farm.get("hands", _MISSING)
    if not isinstance(tiles, list) or len(tiles) != size:
        return action, None, 0
    if any(not isinstance(row, list) or len(row) != size for row in tiles):
        return action, None, 0
    if not isinstance(hands, list):
        return action, None, 0

    positions = [_strict_coord(farm.get("farmer", _MISSING), size)]
    positions.extend(_strict_coord(position, size) for position in hands)
    if any(position is None for position in positions):
        return action, None, 0

    inventories = private.get("inventories", _MISSING)
    if not isinstance(inventories, list) or len(inventories) != len(positions):
        return action, None, 0
    cargo = [_strict_inventory(inventory) for inventory in inventories]
    if any(units is None for units in cargo):
        return action, None, 0
    shed_total = _strict_shed_total(private.get("shed", _MISSING))
    if shed_total is None:
        return action, None, 0
    if shed_total + sum(cargo) > STANDARD_CONFIG["shedCapacity"]:
        telemetry["capacity_ambiguous"] += 1
        return action, None, 0

    commands = _strict_commands(action, len(hands))
    if commands is None or not _sell_only_market(action):
        return action, None, 0

    # Any other move can race for the same shed cell.  HARVEST/COLLECT can create
    # additional product after our capacity census.  Both cases fail closed.
    for command in commands:
        if command[0] == "MOVE":
            return action, None, 0
        if command[0] not in SAFE_OTHER_WORK:
            return action, None, 0

    occupied = set(positions)
    shed_cells = _shed_cells(size)
    candidates = []
    for actor, (position, units, command) in enumerate(zip(positions, cargo, commands)):
        if units <= 0 or command != ["PASS"]:
            continue
        if position in shed_cells:
            # Parent step-718 liquidation will already DROP this cargo.
            continue
        free_last_hops = [
            cell for cell in shed_cells
            if cell not in occupied
            and abs(position[0] - cell[0]) + abs(position[1] - cell[1]) == 1
        ]
        if not free_last_hops:
            continue
        target = min(free_last_hops)
        replacement = base._v219_walk(position, target)
        if not isinstance(replacement, list) or not replacement or replacement[0] != "MOVE":
            continue
        candidates.append((actor, units, target, replacement))

    if not candidates:
        return action, None, 0

    # One deterministic rescue only.  This makes target occupancy and capacity proofs
    # independent of multi-worker movement resolution.
    actor, units, _target, replacement = min(candidates, key=lambda row: row[0])
    result = copy.deepcopy(action)
    result_commands = [result["farmer"], *result["hands"]]
    result_commands[actor] = list(replacement)
    result["farmer"], result["hands"] = result_commands[0], result_commands[1:]
    telemetry["activations"] += 1
    telemetry["protected_units"] += units
    telemetry["farmer_activations" if actor == 0 else "hand_activations"] += 1
    return result, actor, units


def install(parent, *, enabled: bool = False):
    """Wrap an already-configured parent.  Disabled output is exact parent identity."""
    if type(enabled) is not bool:
        raise TypeError("enabled must be a bool")

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        result, _actor, _units = rescue_last_hop(
            action, observation, configuration, enabled=enabled
        )
        return result

    agent.telemetry = telemetry
    return agent
