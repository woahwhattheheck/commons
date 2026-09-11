# SPDX-License-Identifier: Apache-2.0
"""B11 experiment: condition R04 sale horizon on a strict public farm mirror.

Unconditional horizon 10 is rejected: it is strongly positive against the
structurally identical V3.1 mirror and strongly negative against Arlene.  This
experiment asks a narrower question: can public farm structure certify the
mirror-like regime strongly enough to use horizon 10 only there?

Only public ``observation['farms']`` fields are inspected.  Money is
intentionally excluded from the mirror signature because sale timing itself
changes money and would make the classifier self-invalidating.  Hidden shed,
worker inventories and market orders are never read.
"""
from __future__ import annotations

import copy

import r04_full_router as r04

BASE_HORIZON = 8
MIRROR_HORIZON = 10
MIRROR_STREAK_REQUIRED = 8
_SIGNATURE_KEYS = ("tiles", "farmer", "hands", "unlocked_quadrants", "hires_today")
_VALID_QUADRANTS = {"NW", "NE", "SW", "SE"}

_TRACKERS = {}
REPORT = {
    "callbacks": 0,
    "h8_callbacks": 0,
    "h10_callbacks": 0,
    "mirror_observations": 0,
    "mismatch_observations": 0,
    "malformed_observations": 0,
    "gap_resets": 0,
    "max_mirror_streak": 0,
    "trace": [],
}


def reset_state():
    _TRACKERS.clear()
    REPORT.update(
        callbacks=0,
        h8_callbacks=0,
        h10_callbacks=0,
        mirror_observations=0,
        mismatch_observations=0,
        malformed_observations=0,
        gap_resets=0,
        max_mirror_streak=0,
        trace=[],
    )


def _json_equal(a, b):
    """Recursive JSON type+value equality; bool never aliases int."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if set(a) != set(b):
            return False
        return all(_json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    return a == b


def _strict_int(value):
    return type(value) is int


def _position(value):
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(_strict_int(coord) for coord in value)
    )


def _tiles(value):
    if not isinstance(value, list) or not value:
        return False
    width = None
    for row in value:
        if not isinstance(row, list) or not row:
            return False
        if width is None:
            width = len(row)
        elif len(row) != width:
            return False
        if any(cell is not None and not isinstance(cell, dict) for cell in row):
            return False
    return True


def _signature(farm):
    """Return a type-safe public structural signature or ``None``.

    Equality is useful as regime evidence only after each field is independently
    known to have the public engine shape.  Otherwise two equal malformed farms
    (for example ``hires_today=True`` or ``hands='same'``) could manufacture a
    mirror certificate merely by being equally malformed.
    """
    if not isinstance(farm, dict):
        return None
    if any(key not in farm for key in _SIGNATURE_KEYS):
        return None

    tiles = farm["tiles"]
    farmer = farm["farmer"]
    hands = farm["hands"]
    quadrants = farm["unlocked_quadrants"]
    hires = farm["hires_today"]
    if not _tiles(tiles) or not _position(farmer):
        return None
    if not isinstance(hands, list) or any(not _position(pos) for pos in hands):
        return None
    if (
        not isinstance(quadrants, list)
        or any(type(value) is not str or value not in _VALID_QUADRANTS for value in quadrants)
        or len(set(quadrants)) != len(quadrants)
    ):
        return None
    if not _strict_int(hires) or hires < 0:
        return None

    # Copy only public, strategy-structural fields.  The copy prevents later
    # mutation of the shared observation object from changing a recorded sig.
    return {key: copy.deepcopy(farm[key]) for key in _SIGNATURE_KEYS}


def _clear_recoverable_tracker(player):
    if _strict_int(player) and player in (0, 1):
        _TRACKERS.pop(player, None)


def mirror_certificate(observation):
    """Return (certified, streak, reason) and update continuity state.

    Certification requires exactly two public farms, a literal integer player
    id in {0,1}, a literal integer step, exact public-field schemas, recursive
    JSON-type/value equality of the structural farm signatures, and eight
    consecutive callbacks.  Any gap, rewind, mismatch or malformed structure
    fails closed to horizon 8; malformed input also clears any recoverable
    player tracker immediately rather than letting stale streak state survive.
    """
    REPORT["callbacks"] += 1
    if not isinstance(observation, dict):
        REPORT["malformed_observations"] += 1
        return False, 0, "malformed-observation"

    step = observation.get("step")
    player = observation.get("player")
    farms = observation.get("farms")
    if (
        not _strict_int(step)
        or not _strict_int(player)
        or player not in (0, 1)
        or not isinstance(farms, list)
        or len(farms) != 2
    ):
        REPORT["malformed_observations"] += 1
        _clear_recoverable_tracker(player)
        return False, 0, "malformed-envelope"

    own = _signature(farms[player])
    rival = _signature(farms[1 - player])
    if own is None or rival is None:
        REPORT["malformed_observations"] += 1
        _TRACKERS.pop(player, None)
        return False, 0, "malformed-farm"

    prior = _TRACKERS.get(player)
    streak = 0
    if prior is not None:
        last_step = prior.get("last_step")
        if not _strict_int(last_step) or step != last_step + 1:
            REPORT["gap_resets"] += 1
        else:
            prior_streak = prior.get("streak", 0)
            streak = prior_streak if _strict_int(prior_streak) and prior_streak >= 0 else 0

    mirror = _json_equal(own, rival)
    if mirror:
        streak += 1
        REPORT["mirror_observations"] += 1
    else:
        streak = 0
        REPORT["mismatch_observations"] += 1

    _TRACKERS[player] = {"last_step": step, "streak": streak}
    REPORT["max_mirror_streak"] = max(REPORT["max_mirror_streak"], streak)
    certified = mirror and streak >= MIRROR_STREAK_REQUIRED
    return certified, streak, "mirror" if certified else ("warming" if mirror else "mismatch")


def install(
    host=None,
    *,
    enabled=True,
    horizon=BASE_HORIZON,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
):
    """Bind exact V3.1 R04 knobs and optionally install the B11 conditioner."""
    if type(horizon) is not int or horizon != BASE_HORIZON:
        raise ValueError("B11 baseline horizon must be literal int 8")
    parent = r04.install(
        host,
        horizon=BASE_HORIZON,
        opening=opening,
        row_order=row_order,
        evening_flush=evening_flush,
        sale_fertilizer=sale_fertilizer,
        cattle_early=cattle_early,
    )
    if not enabled:
        return parent

    def adaptive_agent(observation, configuration=None):
        certified, streak, reason = mirror_certificate(observation)
        selected = MIRROR_HORIZON if certified else BASE_HORIZON
        if selected == MIRROR_HORIZON:
            REPORT["h10_callbacks"] += 1
        else:
            REPORT["h8_callbacks"] += 1
        if len(REPORT["trace"]) < 512:
            step = observation.get("step") if isinstance(observation, dict) else None
            REPORT["trace"].append(
                {"step": step, "horizon": selected, "streak": streak, "reason": reason}
            )

        # SALE_HORIZON is a module-global knob read synchronously by E184.  Keep
        # the selected value scoped to this one parent callback so a sibling
        # control/experiment sharing the imported r04 module cannot inherit B11
        # policy state, including when the parent raises.
        prior_horizon = r04.SALE_HORIZON
        r04.SALE_HORIZON = selected
        try:
            return parent(observation, configuration)
        finally:
            r04.SALE_HORIZON = prior_horizon

    adaptive_agent.__name__ = "b11_mirror_adaptive_agent"
    return adaptive_agent
