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


def _signature(farm):
    if not isinstance(farm, dict):
        return None
    if any(key not in farm for key in _SIGNATURE_KEYS):
        return None
    # Copy only public, strategy-structural fields.  The copy prevents later
    # mutation of the shared observation object from changing a recorded sig.
    return {key: copy.deepcopy(farm[key]) for key in _SIGNATURE_KEYS}


def mirror_certificate(observation):
    """Return (certified, streak, reason) and update continuity state.

    Certification requires exactly two public farms, a literal integer player
    id in {0,1}, a literal integer step, exact JSON-type/value equality of the
    structural farm signatures, and eight consecutive callbacks.  Any gap,
    rewind, mismatch or malformed structure fails closed to horizon 8.
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
            streak = prior.get("streak", 0) if _strict_int(prior.get("streak")) else 0

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

        # R04/E184 reads SALE_HORIZON at call time, but it is a module global.
        # Scope the experimental value to this one parent callback so another
        # arm/control sharing the imported module cannot inherit H10.  Finally
        # also protects the shared module if the parent raises.
        prior_horizon = r04.SALE_HORIZON
        r04.SALE_HORIZON = selected
        try:
            return parent(observation, configuration)
        finally:
            r04.SALE_HORIZON = prior_horizon

    adaptive_agent.__name__ = "b11_mirror_adaptive_agent"
    return adaptive_agent
