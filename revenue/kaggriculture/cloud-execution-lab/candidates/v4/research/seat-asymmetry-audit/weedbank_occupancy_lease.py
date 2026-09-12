#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""TITAN V4 WEEDBANK successor: reversible occupancy-lease admission.

Research only. This module does not select actions or target the hidden episode
seed. It turns Gemini/Antigravity's blanket empty-structure "action bank" into
an explicit expected-action gate under the canonical TOWNRNG boundary.

Official engine source facts used by this surface:
- BUILD_COOP / BUILD_PASTURE require ``tile is None`` and occupy that tile.
- DIG returns an empty structure to ``None`` but cannot remove a placed animal.
- EOD weed RNG draws occur only on ``None`` tiles.
- the same EOD RNG stream continues into public shop unlock selection.

The caller remains responsible for route reachability and current-policy
opportunity costs. No value is assigned to a hidden-seed prediction.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

DEFAULT_WEED_SPAWN_CHANCE = 0.005
ENVIRONMENT_PATH_DIVERGED = "ENVIRONMENT_PATH_DIVERGED"
RNG_CURSOR_NEUTRAL_CONTROL = "RNG_CURSOR_NEUTRAL_CONTROL"
RNG_CURSOR_EXPOSED_NO_DIVERGENCE = "RNG_CURSOR_EXPOSED_NO_DIVERGENCE"
UNEXPLAINED_ENVIRONMENT_DIVERGENCE = "UNEXPLAINED_ENVIRONMENT_DIVERGENCE"


def _plain_nonnegative_number(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _plain_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def daily_clear_expected_weed_events_avoided(
    occupied_eods: Any,
    weed_spawn_chance: Any = DEFAULT_WEED_SPAWN_CHANCE,
) -> float | None:
    """Expected avoided weed spawns if the baseline clears weeds every day."""
    days = _plain_nonnegative_int(occupied_eods)
    chance = _plain_nonnegative_number(weed_spawn_chance)
    if days is None or chance is None or chance > 1:
        return None
    return days * chance


def occupancy_lease_gate(
    *,
    current_tile: Any,
    structure_kind: Any,
    structure_will_remain_empty: Any,
    build_reachable: Any,
    dig_reachable: Any,
    dig_reserved_before_reuse: Any,
    tile_needed_before_dig: Any,
    occupied_eods: Any,
    weed_spawn_chance: Any = DEFAULT_WEED_SPAWN_CHANCE,
    weed_clear_action_cost: Any = 1,
    route_action_cost_per_weed: Any = 0,
    build_action_opportunity_cost: Any = 1,
    dig_action_opportunity_cost: Any = 1,
    temporary_tile_opportunity_cost: Any = 0,
) -> dict[str, Any]:
    """Expected-action gate for an empty COOP/PASTURE occupancy lease.

    The lease can only survive when the tile is currently empty, BUILD and the
    eventual reclamation DIG are reachable, the structure remains animal-free,
    and reclamation is explicitly reserved before the tile is needed again.

    The expected weed/routing benefit must strictly exceed BUILD + DIG +
    temporary-tile opportunity cost. There is deliberately no ``seed`` input:
    TOWNRNG shop-path effects are measured separately, never used as hidden-seed
    targeting authority.
    """
    base = {
        "decision_authority": False,
        "hidden_seed_targeting_allowed": False,
    }

    if current_tile is not None:
        return base | {"admitted": False, "reason": "tile-not-empty"}
    if structure_kind not in ("COOP", "PASTURE"):
        return base | {"admitted": False, "reason": "unsupported-structure"}
    if type(structure_will_remain_empty) is not bool or not structure_will_remain_empty:
        return base | {"admitted": False, "reason": "structure-not-empty-lease"}

    for name, value in (
        ("build_reachable", build_reachable),
        ("dig_reachable", dig_reachable),
        ("dig_reserved_before_reuse", dig_reserved_before_reuse),
        ("tile_needed_before_dig", tile_needed_before_dig),
    ):
        if type(value) is not bool:
            return base | {"admitted": False, "reason": f"malformed-{name}"}

    if not build_reachable:
        return base | {"admitted": False, "reason": "build-unreachable"}
    if not dig_reachable:
        return base | {"admitted": False, "reason": "dig-unreachable"}
    if not dig_reserved_before_reuse:
        return base | {"admitted": False, "reason": "no-reclamation-obligation"}
    if tile_needed_before_dig:
        return base | {"admitted": False, "reason": "tile-needed-before-reclamation"}

    days = _plain_nonnegative_int(occupied_eods)
    chance = _plain_nonnegative_number(weed_spawn_chance)
    weed_cost = _plain_nonnegative_number(weed_clear_action_cost)
    route_cost = _plain_nonnegative_number(route_action_cost_per_weed)
    build_cost = _plain_nonnegative_number(build_action_opportunity_cost)
    dig_cost = _plain_nonnegative_number(dig_action_opportunity_cost)
    tile_cost = _plain_nonnegative_number(temporary_tile_opportunity_cost)
    if (
        days is None
        or chance is None
        or chance > 1
        or weed_cost is None
        or route_cost is None
        or build_cost is None
        or dig_cost is None
        or tile_cost is None
    ):
        return base | {"admitted": False, "reason": "malformed-economics"}

    expected_events = days * chance
    expected_benefit = expected_events * (weed_cost + route_cost)
    action_cost = build_cost + dig_cost + tile_cost
    margin = expected_benefit - action_cost
    admitted = margin > 0
    return base | {
        "admitted": admitted,
        "reason": (
            "positive-expected-action-margin"
            if admitted
            else "expected-action-dominated"
        ),
        "occupied_eods": days,
        "expected_weed_events_avoided": expected_events,
        "expected_action_benefit": expected_benefit,
        "lease_action_and_tile_cost": action_cost,
        "expected_action_margin": margin,
    }


def environment_path_classification(
    *,
    baseline_unlocked_shops: Sequence[str],
    candidate_unlocked_shops: Sequence[str],
    baseline_total_empty_tiles: Any,
    candidate_total_empty_tiles: Any,
) -> str:
    """Apply TOWNRNG's public-environment divergence gate to a lease pair."""
    baseline_empty = _plain_nonnegative_int(baseline_total_empty_tiles)
    candidate_empty = _plain_nonnegative_int(candidate_total_empty_tiles)
    if baseline_empty is None or candidate_empty is None:
        raise ValueError("empty-tile counts must be plain nonnegative ints")

    baseline = tuple(baseline_unlocked_shops)
    candidate = tuple(candidate_unlocked_shops)
    if baseline != candidate:
        if baseline_empty != candidate_empty:
            return ENVIRONMENT_PATH_DIVERGED
        return UNEXPLAINED_ENVIRONMENT_DIVERGENCE
    if baseline_empty == candidate_empty:
        return RNG_CURSOR_NEUTRAL_CONTROL
    return RNG_CURSOR_EXPOSED_NO_DIVERGENCE
