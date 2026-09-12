# SPDX-License-Identifier: Apache-2.0
"""CF1: recover one expiring fertilizer from a provably empty COW HARVEST.

Default OFF. At the final pre-EOD action, replace exactly one empty HARVEST
with COLLECT_FERTILIZER. A whole-farm capacity bound protects existing cargo.
The outer whole-agent seam must see the reconstructed fertilizer hand.
No profitable outcome or future-stock safety is implied by this local theorem.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any

STANDARD = {
    'episodeSteps': 720,
    'turnsPerDay': 24,
    'boardSize': 10,
    'shedCapacity': 100,
    'maxMarketOrdersPerTurn': 10,
}
PRODUCTS = frozenset(('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON',
                      'EGG', 'MILK', 'WOOL', 'FERTILIZER'))
# These commands cannot increase total own shed + carried cargo. The one
# admitted HARVEST is separately proved empty. Other HARVEST/COLLECT rows veto.
NONPRODUCING = frozenset(('PASS', 'NORTH', 'SOUTH', 'EAST', 'WEST', 'DROP',
                         'WATER', 'FEED', 'CARE', 'FERTILIZE', 'DIG',
                         'BUILD_COOP', 'BUILD_PASTURE'))
telemetry = Counter()
_MISSING = object()


def _standard(configuration: Any) -> bool:
    for key, expected in STANDARD.items():
        try:
            value = configuration.get(key, _MISSING) if isinstance(configuration, dict) else getattr(configuration, key, _MISSING)
        except Exception:
            return False
        if type(value) is not int or value != expected:
            return False
    return True


def _inventory_total(value: Any):
    if not isinstance(value, dict):
        return None
    total = 0
    for item, quantity in value.items():
        if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
            return None
        total += quantity
    return total


def _ready_cow(tile: Any, day: int) -> bool:
    if not isinstance(tile, dict) or tile.get('kind') != 'PASTURE' or tile.get('animal') != 'COW':
        return False
    for field in ('fed_today', 'cared_today', 'fertilizer_available'):
        if tile.get(field) is not True:
            return False
    units = tile.get('yield_units')
    placed = tile.get('placed_day')
    unfed = tile.get('consecutive_unfed')
    bonus = tile.get('pending_care_bonus')
    return (type(units) is int and units == 0
            and type(placed) is int and 0 <= placed <= day
            and type(unfed) is int and 0 <= unfed <= 1
            and type(bonus) is int and bonus >= 0)


def apply_cow_fert_salvage(action: Any, observation: Any, configuration: Any, *, enabled=False):
    """Return exact parent on OFF/no-match; otherwise rewrite one dead unit row."""
    if enabled is not True or not _standard(configuration):
        return action
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action
    step, player = observation.get('step'), observation.get('player')
    if type(step) is not int or not 0 <= step <= 695 or step % 24 != 23:
        return action
    if type(player) is not int or player not in (0, 1):
        return action
    farms, private = observation.get('farms'), observation.get('private')
    if not isinstance(farms, list) or len(farms) != 2 or not isinstance(private, dict):
        return action
    farm = farms[player]
    if not isinstance(farm, dict):
        return action
    farmer, hands, tiles = farm.get('farmer'), farm.get('hands'), farm.get('tiles')
    commands, market = action.get('hands'), action.get('market')
    if not isinstance(hands, list) or not isinstance(commands, list) or not isinstance(market, list):
        return action
    if not isinstance(tiles, list) or len(tiles) != 10 or any(not isinstance(row, list) or len(row) != 10 for row in tiles):
        return action
    positions = [farmer, *hands]
    rows = [action.get('farmer'), *commands]
    inventories, shed = private.get('inventories'), private.get('shed')
    if (len(rows) != len(positions) or not isinstance(inventories, list)
            or len(inventories) != len(positions)):
        return action
    # Aliased Python fixtures are not ordinary JSON observations. Do not let a
    # sibling DROP access the selected actor's newly collected unit before EOD.
    if len({id(x) for x in [shed, *inventories]}) != len(inventories) + 1:
        return action
    total = _inventory_total(shed)
    if total is None:
        return action
    for inventory in inventories:
        quantity = _inventory_total(inventory)
        if quantity is None:
            return action
        total += quantity
    if total + 1 > 100:
        return action

    # Exact raw executable prefix, without compaction. SELL realizes before
    # EOD deposit, so the extra carried fertilizer cannot change these orders.
    for row in market[:10]:
        if row == []:
            continue
        if (not isinstance(row, list) or len(row) != 3 or row[0] != 'SELL'
                or not isinstance(row[1], str) or row[1] not in PRODUCTS
                or type(row[2]) is not int or row[2] <= 0):
            return action

    sites = []
    selected = None
    for actor, (position, command) in enumerate(zip(positions, rows)):
        if (not isinstance(position, list) or len(position) != 2
                or any(type(v) is not int or not 0 <= v < 10 for v in position)
                or not isinstance(command, list) or len(command) != 1
                or not isinstance(command[0], str)):
            return action
        x, y = position
        sites.append((x, y))
        if command == ['HARVEST']:
            if selected is not None or not _ready_cow(tiles[y][x], step // 24):
                return action
            selected = actor
        elif command[0] not in NONPRODUCING:
            return action
    if selected is None or sites.count(sites[selected]) != 1:
        return action

    result = copy.deepcopy(action)
    if selected == 0:
        result['farmer'] = ['COLLECT_FERTILIZER']
    else:
        result['hands'][selected - 1] = ['COLLECT_FERTILIZER']
    telemetry['activations'] += 1
    telemetry['fertilizer_units_recovered'] += 1
    return result


def install(parent, *, enabled=False):
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        return apply_cow_fert_salvage(action, observation, configuration, enabled=enabled)
    agent.telemetry = telemetry
    return agent
