# SPDX-License-Identifier: Apache-2.0
"""Default-OFF V5 candidate: skip only provably redundant animal FEED actions.

The pinned engine removes an animal only after its second consecutive unfed
end-of-day. Base animal production is independent of ``fed_today``; feeding is
required for the CARE bonus. This transform therefore changes a selected FEED
to PASS only on the zero-strike leg and only when doing so cannot discard a
current or pending CARE bonus.

The module is deliberately not wired into the canonical runtime. It is an
isolated candidate for matched evaluation.
"""
from __future__ import annotations

from copy import deepcopy


def _position(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or type(value[0]) is not int or type(value[1]) is not int):
        return None
    return (value[0], value[1])


def _action_is(action, op):
    return isinstance(action, list) and bool(action) and action[0] == op


def _context(observation, selected):
    if not isinstance(observation, dict) or not isinstance(selected, dict):
        return None, "malformed_input"
    player = observation.get("player")
    farms = observation.get("farms")
    private = observation.get("private")
    if type(player) is not int or not isinstance(farms, list) or not 0 <= player < len(farms):
        return None, "malformed_public_identity"
    farm = farms[player]
    if not isinstance(farm, dict) or not isinstance(private, dict):
        return None, "malformed_private_context"
    hands = farm.get("hands")
    positions = [farm.get("farmer")]
    if not isinstance(hands, list):
        return None, "malformed_unit_positions"
    positions.extend(hands)
    positions = [_position(p) for p in positions]
    if any(p is None for p in positions):
        return None, "malformed_unit_positions"

    selected_hands = selected.get("hands")
    farmer_action = selected.get("farmer")
    if not isinstance(selected_hands, list) or len(selected_hands) != len(hands):
        return None, "malformed_selected_units"
    actions = [farmer_action, *selected_hands]
    if any(not isinstance(action, list) or not action for action in actions):
        return None, "malformed_selected_units"

    inventories = private.get("inventories")
    tiles = farm.get("tiles")
    if not isinstance(inventories, list) or len(inventories) != len(positions):
        return None, "malformed_inventories"
    if not isinstance(tiles, list):
        return None, "malformed_tiles"
    return {
        "tiles": tiles,
        "positions": positions,
        "actions": actions,
        "inventories": inventories,
    }, None


def _tile_at(tiles, position):
    x, y = position
    if y < 0 or y >= len(tiles) or not isinstance(tiles[y], list):
        return None
    row = tiles[y]
    if x < 0 or x >= len(row):
        return None
    return row[x]


def apply_alternate_feed(observation, selected):
    """Return ``(action, report)`` without mutating either input.

    A FEED is suppressed only when:
    * the actor currently carries at least one WHEAT, so the edit saves a unit;
    * the actor stands on an animal whose ``consecutive_unfed`` is exactly zero;
    * the animal is not already fed or cared today;
    * no pending CARE bonus exists; and
    * no selected CARE action targets the same current tile.

    Skipping on the zero-strike leg advances the engine to one unfed day, which
    is still a live animal. The next selected FEED is left intact once the
    observation reports ``consecutive_unfed == 1``.
    """
    context, error = _context(observation, selected)
    report = {
        "changed": False,
        "reason": error or "no_eligible_feed",
        "wheat_saved": 0,
        "edits": [],
    }
    if context is None:
        return selected, report

    care_positions = {
        position
        for position, action in zip(context["positions"], context["actions"])
        if _action_is(action, "CARE")
    }
    eligible = []
    for actor, (position, action, inventory) in enumerate(
            zip(context["positions"], context["actions"], context["inventories"])):
        if not _action_is(action, "FEED") or not isinstance(inventory, dict):
            continue
        if type(inventory.get("WHEAT", 0)) is not int or inventory.get("WHEAT", 0) < 1:
            continue
        tile = _tile_at(context["tiles"], position)
        if not isinstance(tile, dict) or "animal" not in tile:
            continue
        if tile.get("consecutive_unfed") != 0:
            continue
        if tile.get("fed_today") is not False or tile.get("cared_today") is not False:
            continue
        if tile.get("pending_care_bonus", 0) != 0 or position in care_positions:
            continue
        eligible.append((actor, position, tile.get("animal")))

    if not eligible:
        return selected, report

    result = deepcopy(selected)
    edits = []
    for actor, position, animal in eligible:
        if actor == 0:
            result["farmer"] = ["PASS"]
        else:
            result["hands"][actor - 1] = ["PASS"]
        edits.append({
            "actor": actor,
            "position": list(position),
            "animal": animal,
            "from": ["FEED"],
            "to": ["PASS"],
        })
    report.update(
        changed=True,
        reason="safe_alternate_feed",
        wheat_saved=len(edits),
        edits=edits,
    )
    return result, report


transform = apply_alternate_feed
