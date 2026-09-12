# SPDX-License-Identifier: Apache-2.0
"""Committed-route + retry-safe composition entrypoint for V219.

``v219_current.py`` remains the donor-port theorem.  This canonical adapter adds
only current-runtime authority and idempotence:

* the route snapshot comes from the landed shared current-route-witness seam,
  keyed by the entrypoint's explicit ``completed_route_id``; raw
  ``controller.cur`` is never consulted;
* exact standard configuration keys must be present;
* an identical repeated callback at one step replays the prior V219 result
  without consuming pending state twice, while any same-step input or route
  authority conflict fails closed.

The shared witness's full-route capture primitive is used deliberately rather
than a bounded future window: V219 remains active through public step 718, where
there is no step+1 row from which ``bind_current_route_window`` could construct a
window.  Authority semantics are still exactly the witness seam's stable
``controller.R[completed_route_id]`` capture and digest.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import v219_current as core

_WITNESS_MODULE_NAME = "_titan_v5_current_route_witness_for_v219"
_WITNESS_PATH = (
    Path(__file__).resolve().parent.parent
    / "current-route-witness"
    / "current_route_witness.py"
)
_STANDARD_CONFIG = {
    "boardSize": core.BOARD_SIZE,
    "turnsPerDay": core.TURNS_PER_DAY,
    "shedCapacity": core.SHED_CAPACITY,
    "maxMarketOrdersPerTurn": core.MAX_ORDERS,
    "farmHandCostMult": 1,
}


def new_state() -> dict[str, Any]:
    return core.new_state()


def _identity(selected: Any, state: Any, reason: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    return (
        copy.deepcopy(selected),
        copy.deepcopy(state) if isinstance(state, dict) else core.new_state(),
        {"applied": False, "reason": reason},
    )


def _strict_standard_config(configuration: Any) -> bool:
    if not isinstance(configuration, dict):
        return False
    for key, expected in _STANDARD_CONFIG.items():
        if key not in configuration:
            return False
        actual = configuration[key]
        if type(actual) is not int or actual != expected:
            return False
    return True


def _load_witness_module() -> Any | None:
    existing = sys.modules.get(_WITNESS_MODULE_NAME)
    if existing is not None:
        return existing
    try:
        spec = importlib.util.spec_from_file_location(_WITNESS_MODULE_NAME, _WITNESS_PATH)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[_WITNESS_MODULE_NAME] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        sys.modules.pop(_WITNESS_MODULE_NAME, None)
        return None


def _committed_route_authority(
    controller: Any,
    completed_route_id: Any,
) -> tuple[str, str, list[Any], str] | None:
    witness = _load_witness_module()
    capture = None if witness is None else getattr(witness, "_capture_route", None)
    if not callable(capture):
        return None
    try:
        captured = capture(controller, completed_route_id)
    except Exception:
        return None
    if not isinstance(captured, tuple) or len(captured) != 4:
        return None
    route_id, controller_type, route_snapshot, route_sha256 = captured
    if (
        type(route_id) is not str
        or not route_id
        or type(controller_type) is not str
        or not controller_type
        or not isinstance(route_snapshot, list)
        or type(route_sha256) is not str
        or len(route_sha256) != 64
    ):
        return None
    # Defense in depth: the donor core must independently agree with the shared
    # witness digest before any selected action can be changed.
    if core._bind_route(route_snapshot, route_sha256) is None:
        return None
    return route_id, controller_type, route_snapshot, route_sha256


def _canonical_digest(value: Any) -> str | None:
    try:
        rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        recovered = json.loads(rendered)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if recovered != value:
        return None
    return hashlib.sha256(rendered.encode("ascii")).hexdigest()


def _call_key(
    observation: Any,
    selected: Any,
    configuration: Any,
    *,
    enabled: Any,
    route_id: str,
    controller_type: str,
    route_snapshot: Any,
    route_sha256: str,
) -> str | None:
    return _canonical_digest({
        "observation": observation,
        "selected": selected,
        "configuration": configuration,
        "enabled": enabled,
        "route_id": route_id,
        "controller_type": controller_type,
        "route_snapshot": route_snapshot,
        "route_sha256": route_sha256,
    })


def apply(
    observation: Any,
    selected: Any,
    configuration: Any,
    *,
    enabled: Any,
    controller: Any,
    completed_route_id: Any,
    state: Any = None,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Run V219 against one explicitly committed producer route.

    Callers provide the controller solely so the shared witness can authenticate
    ``R[completed_route_id]``. They cannot inject a route snapshot or digest.
    """
    stable = copy.deepcopy(state) if isinstance(state, dict) else core.new_state()
    if enabled is not True:
        return _identity(selected, stable, "disabled")
    if not _strict_standard_config(configuration):
        return _identity(selected, stable, "unsupported-config")

    authority = _committed_route_authority(controller, completed_route_id)
    if authority is None:
        return _identity(selected, stable, "route-authority")
    route_id, controller_type, route_snapshot, route_sha256 = authority

    step = observation.get("step") if isinstance(observation, dict) else None
    key = _call_key(
        observation,
        selected,
        configuration,
        enabled=enabled,
        route_id=route_id,
        controller_type=controller_type,
        route_snapshot=route_snapshot,
        route_sha256=route_sha256,
    )

    retry = stable.get("_retry") if isinstance(stable.get("_retry"), dict) else None
    if retry is not None and type(step) is int and retry.get("step") == step:
        if key is not None and retry.get("call_key") == key:
            replay = copy.deepcopy(retry.get("action"))
            if isinstance(replay, dict):
                report = copy.deepcopy(retry.get("report")) if isinstance(retry.get("report"), dict) else {}
                report["applied"] = replay != selected
                report["reason"] = "same-step-replay"
                report["replayed"] = True
                return replay, stable, report
        return copy.deepcopy(selected), stable, {
            "applied": False,
            "reason": "same-step-conflict",
            "replayed": False,
        }

    action, later, report = core.apply(
        observation,
        selected,
        configuration,
        enabled=True,
        route_snapshot=route_snapshot,
        route_sha256=route_sha256,
        state=stable,
    )
    if key is not None and type(step) is int and isinstance(later, dict):
        later = copy.deepcopy(later)
        later["_retry"] = {
            "step": step,
            "call_key": key,
            "action": copy.deepcopy(action),
            "report": copy.deepcopy(report),
        }
    if isinstance(report, dict):
        report = copy.deepcopy(report)
        report["committed_route_id"] = route_id
        report["committed_controller_type"] = controller_type
    return action, later, report


# Public constants used by focused contracts/composers.
LAST_STEP = core.LAST_STEP
QUALIFY_STEP = core.QUALIFY_STEP
