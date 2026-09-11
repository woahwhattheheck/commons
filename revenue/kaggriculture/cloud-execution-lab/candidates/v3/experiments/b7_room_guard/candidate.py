"""TITAN V3.1 B7 practice arm: fail-closed shed-room guard.

The frozen R04 stack already gives V226/V233 dynamic wheat purchases explicit shed-capacity
checks. V219's optional fertilizer purchase is budget-guarded but has no analogous room check.
B7 tests only that narrow asymmetry. It is disabled by default and lives outside overlay/**.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402


B7_ENABLED = False
V219_FERTILIZER_ROW = ["BUY_PRODUCT", "FERTILIZER", 10]
B7_REPORT = {
    "calls": 0,
    "v219_fertilizer_requests_seen": 0,
    "activations": 0,
    "guarded_rows": 0,
    "guarded_units": 0,
    "insufficient_room": 0,
    "native_collision_declines": 0,
    "ambiguous_row_declines": 0,
    "other_overflow_declines": 0,
    "configuration_declines": 0,
}


def reset_b7_report() -> None:
    for key in B7_REPORT:
        B7_REPORT[key] = 0


def _configuration_is_default(configuration) -> bool:
    if configuration is None:
        return True
    return int(configuration.get("shedCapacity", base.SHED_CAPACITY)) == base.SHED_CAPACITY


def _incoming_shed_units(market) -> int:
    total = 0
    for row in market:
        if not row or len(row) < 3 or row[0] not in ("BUY_PRODUCT", "BUY_ANIMAL"):
            continue
        total += max(0, int(row[2]))
    return total


def _current_v219_state(player: int):
    states = getattr(base, "_V219_STATES", None)
    return states.get(player) if isinstance(states, dict) else None


def _native_market(policy, player: int, step: int):
    """Return the exact authored market rows for the currently selected route, or None.

    B7 needs this only to prove that an identical fertilizer row is not already native. If
    route custody is unavailable, the guard refuses to act rather than guessing provenance.
    """
    if policy is None:
        return None
    players = getattr(policy, "players", None)
    tapes = getattr(policy, "tapes", None)
    if not isinstance(players, dict) or tapes is None:
        return None
    state = players.get(player)
    if state is None or not hasattr(state, "plan"):
        return None
    try:
        return tapes[int(state.plan)][step].get("market") or []
    except (IndexError, KeyError, TypeError, AttributeError, ValueError):
        return None


def room_guard(
    observation,
    action,
    *,
    enabled=None,
    policy=None,
    v219_state=None,
    configuration=None,
):
    """Blank one proven V219 fertilizer-buy row when it alone exceeds shed capacity.

    The transform is deliberately narrower than a generic purchase-capacity rewrite:
    * V219 must expose a same-step pending request with ``fertilizer=True``;
    * the frozen route tape must contain no identical fertilizer row;
    * the final action must contain exactly one identical row;
    * every other BUY_PRODUCT/BUY_ANIMAL unit must fit after current farm commands;
    * adding V219's ten fertilizer units must be the sole reason capacity is exceeded.

    The guarded row becomes ``[]`` rather than being removed, preserving every later market
    row's execution index. Same-turn SELL proceeds are intentionally not credited, matching
    the conservative capacity accounting already used by V233.
    """
    B7_REPORT["calls"] += 1
    if enabled is None:
        enabled = B7_ENABLED
    if not enabled:
        return action
    if not _configuration_is_default(configuration):
        B7_REPORT["configuration_declines"] += 1
        return action

    step = int(observation["step"])
    player = int(observation["player"])
    if v219_state is None:
        v219_state = _current_v219_state(player)
    pending = v219_state.get("pending") if isinstance(v219_state, dict) else None
    if not (isinstance(pending, dict)
            and int(pending.get("step", -1)) == step
            and bool(pending.get("fertilizer"))):
        return action
    B7_REPORT["v219_fertilizer_requests_seen"] += 1

    if policy is None:
        policy = getattr(base, "_POLICY", None)
    native_market = _native_market(policy, player, step)
    if native_market is None:
        B7_REPORT["native_collision_declines"] += 1
        return action
    if any(list(row) == V219_FERTILIZER_ROW for row in native_market if row):
        B7_REPORT["native_collision_declines"] += 1
        return action

    market = action.get("market") or []
    matches = [index for index, row in enumerate(market)
               if row and list(row) == V219_FERTILIZER_ROW]
    if len(matches) != 1:
        B7_REPORT["ambiguous_row_declines"] += 1
        return action

    view = base.FarmView(observation)
    projected = base.projected_shed(action, view)
    stock = sum(max(0, int(quantity)) for quantity in projected.values())
    incoming = _incoming_shed_units(market)
    fertilizer_units = V219_FERTILIZER_ROW[2]
    without_v219 = incoming - fertilizer_units

    # Fail closed if some other purchase set already overflows; B7 only owns V219's row.
    if stock + without_v219 > base.SHED_CAPACITY:
        B7_REPORT["other_overflow_declines"] += 1
        return action
    if stock + incoming <= base.SHED_CAPACITY:
        return action

    B7_REPORT["insufficient_room"] += 1
    result = copy.deepcopy(action)
    result["market"][matches[0]] = []
    B7_REPORT["activations"] += 1
    B7_REPORT["guarded_rows"] += 1
    B7_REPORT["guarded_units"] += fertilizer_units
    return result


def agent(observation, configuration=None):
    parent = base.agent(observation, configuration)
    return room_guard(observation, parent, configuration=configuration)


agent.telemetry = B7_REPORT
