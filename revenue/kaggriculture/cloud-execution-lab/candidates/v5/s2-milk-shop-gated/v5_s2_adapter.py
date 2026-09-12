# SPDX-License-Identifier: Apache-2.0
"""Current-V5 adapter for the authenticated V3.1 S2 sheep-swap donor.

The adapter owns no producer. It consumes the already-selected V5 action and the
current FrozenSelected controller tape, then delegates only to the recovered S2
transaction. Any unsupported ABI shape fails closed to the exact selected object.
"""
from __future__ import annotations

import copy
from typing import Any

import r04_s2_sheep_swap as donor

DONOR_BLOB_SHA1 = "84b025aa9ead6bf362445ad9c3e97598c175c5fd"
DONOR_RECOVERY_COMMIT = "a04e0f0a0f2cb466f33ae89fd84bfbb6165c396e"


def _current_route(agent: Any, step: int) -> list[dict[str, Any]] | None:
    features = getattr(agent, "features", None)
    if features is None or getattr(features, "consumer", None) != "frozen":
        return None
    if getattr(features, "terminal_route", None) is not False:
        return None
    controller = getattr(agent, "controller", None)
    routes = getattr(controller, "R", None)
    cur = getattr(controller, "cur", None)
    if not isinstance(routes, (list, tuple)) or type(cur) is not int:
        return None
    if not (0 <= cur < len(routes)):
        return None
    route = routes[cur]
    if not isinstance(route, list) or type(step) is not int or not (0 <= step < len(route)):
        return None
    if not all(isinstance(row, dict) for row in route):
        return None
    return route


def _market_prefix_supported(selected: dict[str, Any], configuration: Any) -> bool:
    if not isinstance(configuration, dict):
        return False
    max_orders = configuration.get("maxMarketOrdersPerTurn")
    if type(max_orders) is not int or max_orders != donor.MAX_ORDERS:
        return False
    market = selected.get("market", [])
    return isinstance(market, list) and len(market) <= max_orders


def _worker_change_allowed(before: Any, after: Any) -> bool:
    if before == after:
        return True
    if not (isinstance(before, list) and isinstance(after, list)):
        return False
    if len(before) != len(after) or len(before) < 2:
        return False
    if before[0] != after[0] or before[0] not in ("PICKUP", "PLACE"):
        return False
    return before[1] == "COW" and after[1] == "SHEEP" and before[2:] == after[2:]


def _market_change_allowed(before: Any, after: Any) -> bool:
    if not (isinstance(before, list) and isinstance(after, list)) or len(before) != len(after):
        return False
    animal_rewrites = 0
    for left, right in zip(before, after):
        if left == right:
            continue
        if not (isinstance(left, list) and isinstance(right, list)):
            return False
        if (len(left) >= 3 and len(right) == len(left)
                and left[0] == right[0] == "BUY_ANIMAL"
                and left[1] == "COW" and right[1] == "SHEEP"
                and left[2:] == right[2:]):
            animal_rewrites += 1
            if animal_rewrites > 1:
                return False
            continue
        if (len(left) >= 3 and len(right) == len(left)
                and left[:2] == right[:2] == ["SELL", "WOOL"]
                and type(left[2]) is int and type(right[2]) is int
                and right[2] >= left[2] and left[3:] == right[3:]):
            continue
        return False
    return True


def _delta_allowed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if not isinstance(after, dict) or set(after) != set(before):
        return False
    for key in before:
        if key in ("farmer", "hands", "market"):
            continue
        if before[key] != after[key]:
            return False
    if not _worker_change_allowed(before.get("farmer"), after.get("farmer")):
        return False
    left_hands = before.get("hands", [])
    right_hands = after.get("hands", [])
    if not (isinstance(left_hands, list) and isinstance(right_hands, list)
            and len(left_hands) == len(right_hands)):
        return False
    if any(not _worker_change_allowed(left, right)
           for left, right in zip(left_hands, right_hands)):
        return False
    return _market_change_allowed(before.get("market", []), after.get("market", []))


def apply_current_v5(
    agent: Any,
    observation: dict[str, Any],
    configuration: Any,
    selected: dict[str, Any],
    *,
    enabled: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply S2 at the current selected-action boundary; fail closed on ABI drift."""
    if type(enabled) is not bool:
        raise TypeError("enabled must be bool")
    if not enabled:
        return selected, {"applied": False, "reason": "disabled"}
    if not isinstance(observation, dict) or not isinstance(selected, dict):
        return selected, {"applied": False, "reason": "unsupported-shape"}
    step = observation.get("step")
    route = _current_route(agent, step)
    if route is None:
        return selected, {"applied": False, "reason": "unsupported-current-route"}
    if not _market_prefix_supported(selected, configuration):
        return selected, {"applied": False, "reason": "unsupported-market-prefix"}

    state = getattr(agent, "_v5_s2_state", None)
    if not isinstance(state, dict):
        state = donor.new_state()
        setattr(agent, "_v5_s2_state", state)
    checkpoint = copy.deepcopy(state)
    returned = donor.apply_s2_swap(
        observation,
        selected,
        state,
        enabled=True,
        configuration=configuration,
        native_tape=route,
    )
    # The donor deep-copies a valid selected action before proving its narrow
    # mutation. Canonical V5 no-ops must still preserve the exact selected
    # object/bytes rather than publishing an equal-but-new copy.
    if returned == selected:
        return selected, {"applied": False, "reason": "donor-noop", "state": copy.deepcopy(state)}
    if not _delta_allowed(selected, returned):
        state.clear()
        state.update(checkpoint)
        return selected, {"applied": False, "reason": "adapter-delta-rejected"}
    return returned, {
        "applied": True,
        "reason": "accepted",
        "state": copy.deepcopy(state),
        "donor_blob_sha1": DONOR_BLOB_SHA1,
    }
