# SPDX-License-Identifier: Apache-2.0
"""Retry-safe composition entrypoint for the V219 current-ABI core.

The core is deliberately kept as the donor-port theorem. This wrapper adds one
current-runtime property only: an identical repeated callback at the same step
must return the exact previously-computed V219 action without consuming pending
state a second time. A same-step callback with different inputs fails closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import v219_current as core


def new_state() -> dict[str, Any]:
    return core.new_state()


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
    route_snapshot: Any,
    route_sha256: Any,
) -> str | None:
    return _canonical_digest({
        "observation": observation,
        "selected": selected,
        "configuration": configuration,
        "enabled": enabled,
        "route_snapshot": route_snapshot,
        "route_sha256": route_sha256,
    })


def apply(
    observation: Any,
    selected: Any,
    configuration: Any,
    *,
    enabled: Any,
    route_snapshot: Any,
    route_sha256: Any,
    state: Any = None,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Run V219 with exact same-step replay and conflicting-retry fail-closed."""
    stable = copy.deepcopy(state) if isinstance(state, dict) else core.new_state()
    step = observation.get("step") if isinstance(observation, dict) else None
    key = _call_key(
        observation,
        selected,
        configuration,
        enabled=enabled,
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
        enabled=enabled,
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
    return action, later, report


# Public constants used by focused contracts/composers.
LAST_STEP = core.LAST_STEP
QUALIFY_STEP = core.QUALIFY_STEP
