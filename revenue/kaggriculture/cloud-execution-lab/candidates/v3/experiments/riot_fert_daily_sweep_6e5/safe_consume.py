# SPDX-License-Identifier: Apache-2.0
"""Fail-closed consumption wrapper for Riot's fert-daily-sweep donor.

The original Riot factor is preserved byte-for-byte in this directory.  This wrapper
carries the narrower source theorem that is safe to recompose later:

* exact idle workers may still collect a public daily fertilizer unit;
* synthetic DROP is disabled unless the caller supplies the exact current shedCapacity;
* a DROP is authorized only when the *entire* worker inventory fits in the shed at
  unit-action execution time;
* earlier synthetic DROPs reserve their full payload, and any earlier unit command
  other than PASS/COLLECT_FERTILIZER (or a DROP authorized by this wrapper) blocks a
  later synthetic DROP rather than guessing whether that command deposits to shed;
* same-step market SELL rows are deliberately ignored because the official engine
  executes all unit actions before market processing;
* malformed observation/action/shed/inventory/capacity evidence fails closed.

No market row is added, removed, or reordered.  Workers never move.
"""
from __future__ import annotations

import r04_fert_daily_sweep as donor

_PASS = ["PASS"]
_COLLECT = ["COLLECT_FERTILIZER"]
_DROP = ["DROP"]


def _exact_nonnegative_int(value):
    return type(value) is int and value >= 0


def _strict_total(mapping):
    if not isinstance(mapping, dict):
        return None
    total = 0
    for key, value in mapping.items():
        if not isinstance(key, str) or not _exact_nonnegative_int(value):
            return None
        total += value
    return total


def _strict_position(position, board_size):
    return (
        type(position) is list
        and len(position) == 2
        and all(type(value) is int for value in position)
        and 0 <= position[0] < board_size
        and 0 <= position[1] < board_size
    )


def _context(observation, action):
    """Return strict callback structure or None.

    Exact hand cardinality matters because the official engine executes farmer then hands
    in order; silently truncating either side would make same-step capacity reservations
    ambiguous.
    """
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return None
    try:
        player = observation["player"]
        farms = observation["farms"]
        private = observation["private"]
        step = observation["step"]
        farmer_action = action["farmer"]
        hand_actions = action["hands"]
    except (KeyError, TypeError):
        return None
    if type(player) is not int or type(step) is not int:
        return None
    if not isinstance(farms, list) or not (0 <= player < len(farms)):
        return None
    farm = farms[player]
    if not isinstance(farm, dict) or not isinstance(private, dict):
        return None
    try:
        tiles = farm["tiles"]
        farmer = farm["farmer"]
        hands = farm["hands"]
        inventories = private["inventories"]
        shed = private["shed"]
    except (KeyError, TypeError):
        return None
    if (
        not isinstance(tiles, list)
        or not tiles
        or any(not isinstance(row, list) or len(row) != len(tiles) for row in tiles)
        or not isinstance(hands, list)
        or not isinstance(hand_actions, list)
        or not isinstance(inventories, list)
        or len(hand_actions) != len(hands)
    ):
        return None
    board_size = len(tiles)
    positions = [farmer, *hands]
    if any(not _strict_position(position, board_size) for position in positions):
        return None
    commands = [farmer_action, *hand_actions]
    if any(not isinstance(command, list) or not command or not isinstance(command[0], str) for command in commands):
        return None
    shed_total = _strict_total(shed)
    if shed_total is None:
        return None
    return step, tiles, positions, inventories, shed_total, commands


def apply_fert_daily_sweep_safe(observation, action, tape=None, shed_capacity=None):
    """Apply the fail-closed collection + capacity-safe delivery theorem.

    ``shed_capacity`` is intentionally explicit.  The engine's default is configurable;
    guessing 100 here would be unsafe on custom environments.  Missing/malformed capacity
    disables only synthetic DROP; strict fertilizer collection can still proceed.
    """
    try:
        parsed = _context(observation, action)
        if parsed is None:
            return action
        step, tiles, positions, inventories, shed_total, commands = parsed

        new_commands = list(commands)
        changed = False
        claimed = set()

        # Strict collection half.  The engine field is boolean; truthy aliases do not
        # authorize source-level rewrites in this safe donor.
        for index, (command, position) in enumerate(zip(commands, positions)):
            if command != _PASS:
                continue
            tile = donor._worker_tile(tiles, position)
            if tile is donor._UNKNOWN:
                continue
            if not (
                isinstance(tile, dict)
                and tile.get("animal") in donor._ANIMALS
                and tile.get("fertilizer_available") is True
            ):
                continue
            key = (position[0], position[1])
            if key in claimed:
                continue
            claimed.add(key)
            new_commands[index] = list(_COLLECT)
            changed = True

        capacity_ok = _exact_nonnegative_int(shed_capacity)
        if tape is not None and capacity_ok and shed_total <= shed_capacity:
            reserved = 0
            prior_known_safe = True
            wrapper_drops = set()
            for index, position in enumerate(positions):
                command = new_commands[index]
                if command == _PASS and prior_known_safe:
                    inventory = inventories[index] if index < len(inventories) else None
                    payload = _strict_total(inventory)
                    if (
                        payload is not None
                        and payload > 0
                        and inventory.get("FERTILIZER", 0) > 0
                        and not any(inventory.get(animal, 0) > 0 for animal in donor._ANIMALS)
                        and donor._beside_shed(tiles, position)
                        and not donor._has_inventory_work(tape, index, step)
                    ):
                        room = shed_capacity - shed_total - reserved
                        if payload <= room:
                            new_commands[index] = list(_DROP)
                            wrapper_drops.add(index)
                            reserved += payload
                            changed = True

                # For a later worker we only rely on predecessors whose unit-action shed
                # effect is known: PASS/COLLECT do not deposit, and wrapper-authorized DROP
                # has already reserved its complete payload.  Anything else fails closed.
                final_command = new_commands[index]
                if not (
                    final_command == _PASS
                    or final_command == _COLLECT
                    or index in wrapper_drops
                ):
                    prior_known_safe = False

        if not changed:
            return action
        result = dict(action)
        result["farmer"] = new_commands[0]
        result["hands"] = new_commands[1:]
        return result
    except Exception:
        return action
