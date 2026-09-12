# SPDX-License-Identifier: Apache-2.0
"""Default-OFF V5 candidate: same-tick one-shot harvest -> replant relay.

Pinned Kaggriculture applies unit actions sequentially (farmer, then hands) after
one atomic PLANT-demand check.  HARVEST of a mature non-ongoing crop clears its
tile immediately.  Therefore a later co-located PASS hand can legally PLANT the
same crop on the newly-empty tile in the same tick when an extra seed already
exists at tick start.

This module is research-only.  It changes no market rows, creates no seed, and
makes no profitability claim; matched current-line evidence is required before
any runtime hook is considered.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

# Source-pinned engine constants intentionally copied into this isolated
# candidate boundary; focused tests bind the behavior to canonical mechanics.
NON_ONGOING = frozenset({"WHEAT", "CARROT", "MELON"})
FIRST_YIELD_DAY = {"WHEAT": 2, "CARROT": 2, "MELON": 10}


def _identity(selected: Any, reason: str, **extra):
    report = {"changed": False, "reason": reason}
    report.update(extra)
    return selected, report


def _plain_nonnegative(value: Any) -> bool:
    return type(value) is int and value >= 0


def _plain_positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _plant_demand(actions: list[Any], crop: str) -> int:
    # Mirrors interpreter() demand grammar for this crop: every list PLANT row
    # with matching second field counts before any unit action executes.
    return sum(
        1
        for action in actions
        if isinstance(action, list)
        and len(action) >= 2
        and action[0] == "PLANT"
        and action[1] == crop
    )


def transform(
    selected: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
):
    """Rewrite one later co-located PASS hand to PLANT the harvested crop.

    Admission is intentionally conservative:
    - exact standard 10x10 / 24-turn public state;
    - farmer is selected HARVEST on a mature, positive-yield, non-ongoing crop;
    - exactly one hand starts on that farmer tile and its selected action is PASS;
    - no other hand starts on that tile, so no later same-tile unit mutation can
      interfere with the relay;
    - a plain-positive extra same-crop seed exists beyond every already-selected
      same-crop PLANT request, satisfying the engine's pre-unit atomic seed gate.

    Only that PASS hand is rewritten.  Market bytes and every other action are
    preserved exactly.
    """
    cfg = {} if configuration is None else configuration
    if not isinstance(selected, dict) or not isinstance(observation, Mapping) or not isinstance(cfg, Mapping):
        return _identity(selected, "malformed_input")

    player = observation.get("player")
    step = observation.get("step")
    if type(player) is not int or player not in (0, 1) or not _plain_nonnegative(step):
        return _identity(selected, "malformed_public_identity")

    board_size = cfg.get("boardSize", 10)
    turns_per_day = cfg.get("turnsPerDay", 24)
    if type(board_size) is not int or board_size != 10 or type(turns_per_day) is not int or turns_per_day != 24:
        return _identity(selected, "outside_standard_config")
    day = step // turns_per_day

    farms = observation.get("farms")
    private = observation.get("private")
    if not isinstance(farms, list) or len(farms) != 2 or not isinstance(private, Mapping):
        return _identity(selected, "malformed_private_state")
    farm = farms[player]
    if not isinstance(farm, Mapping):
        return _identity(selected, "malformed_private_state")
    farmer = farm.get("farmer")
    hands = farm.get("hands")
    tiles = farm.get("tiles")
    seeds = private.get("seeds")
    if (not isinstance(farmer, list) or len(farmer) != 2
            or not isinstance(hands, list) or not isinstance(tiles, list)
            or not isinstance(seeds, Mapping)):
        return _identity(selected, "malformed_private_state")
    if any(type(v) is not int for v in farmer):
        return _identity(selected, "malformed_actor_position")
    fx, fy = farmer
    if not (0 <= fx < board_size and 0 <= fy < board_size) or len(tiles) != board_size:
        return _identity(selected, "malformed_board")
    if any(not isinstance(row, list) or len(row) != board_size for row in tiles):
        return _identity(selected, "malformed_board")

    farmer_action = selected.get("farmer")
    hand_actions = selected.get("hands")
    market = selected.get("market")
    if (not isinstance(farmer_action, list) or not farmer_action
            or farmer_action[0] != "HARVEST"
            or not isinstance(hand_actions, list) or not isinstance(market, list)
            or len(hand_actions) != len(hands)):
        return _identity(selected, "selected_shape_or_farmer_action")

    tile = tiles[fy][fx]
    if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
        return _identity(selected, "farmer_not_on_plant")
    crop = tile.get("crop")
    if crop not in NON_ONGOING:
        return _identity(selected, "ongoing_or_unknown_crop")
    yield_units = tile.get("yield_units")
    planted_day = tile.get("planted_day")
    if not _plain_positive(yield_units) or type(planted_day) is not int:
        return _identity(selected, "not_harvestable")
    if day - planted_day < FIRST_YIELD_DAY[crop]:
        return _identity(selected, "immature_crop")

    colocated = []
    for index, (position, action) in enumerate(zip(hands, hand_actions)):
        if not (isinstance(position, list) and len(position) == 2 and all(type(v) is int for v in position)):
            return _identity(selected, "malformed_actor_position")
        if position == farmer:
            colocated.append((index, action))
    if len(colocated) != 1:
        return _identity(selected, "ambiguous_colocated_hands")
    hand_index, hand_action = colocated[0]
    if not isinstance(hand_action, list) or not hand_action or hand_action[0] != "PASS":
        return _identity(selected, "colocated_hand_not_pass")

    actions = [farmer_action, *hand_actions]
    existing_demand = _plant_demand(actions, crop)
    seed_count = seeds.get(crop, 0)
    if type(seed_count) is not int or seed_count < existing_demand + 1:
        return _identity(
            selected,
            "no_spare_preexisting_seed",
            crop=crop,
            seed_count=seed_count if type(seed_count) is int else None,
            existing_plant_demand=existing_demand,
        )

    result = deepcopy(selected)
    result["hands"][hand_index] = ["PLANT", crop]
    return result, {
        "changed": True,
        "reason": "same_tick_harvest_plant_relay",
        "crop": crop,
        "target": [fx, fy],
        "hand_index": hand_index,
        "seed_count_at_tick_start": seed_count,
        "existing_same_crop_plant_demand": existing_demand,
        "market_unchanged": True,
        "other_actions_unchanged": True,
        "full_game_gain_measured": False,
    }
