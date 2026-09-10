# SPDX-License-Identifier: Apache-2.0
"""Instrumented hosted-panel entry; not a submission or release entrypoint."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import candidate as _candidate

HERE = Path(__file__).resolve().parent
_EVENT_DIRECTORY = HERE / "panel-events"
_SEEN = set()


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _record(observation, action):
    instance = getattr(_candidate._BASE, "_INSTANCE", None)
    diagnostics = getattr(instance, "diagnostics", {}) if instance is not None else {}
    report = diagnostics.get("day10_fertilizer_liquidity")
    if not isinstance(report, dict):
        return
    reason = report.get("reason")
    step = int(observation.get("step", -1))
    # Retain every changed action and one witness for each decline reason per
    # worker.  This proves both reachability and why a conservative arm stayed
    # dormant without writing hundreds of duplicate rows.
    key = (reason, bool(report.get("changed")))
    if not report.get("changed") and key in _SEEN:
        return
    _SEEN.add(key)
    payload = {
        "schema": "titan-day10-fertilizer-liquidity-event/v1",
        "pid": os.getpid(),
        "step": step,
        "player": int(observation.get("player", -1)),
        "changed": bool(report.get("changed")),
        "reason": reason,
        "quantity": report.get("final_quantity", report.get("quantity", 0)),
        "report": report,
        "action_sha256": hashlib.sha256(_encoded(action)).hexdigest(),
    }
    _EVENT_DIRECTORY.mkdir(exist_ok=True)
    path = _EVENT_DIRECTORY / f"worker-{os.getpid()}.jsonl"
    with path.open("ab") as handle:
        handle.write(_encoded(payload) + b"\n")


def agent(observation, configuration=None):
    action = _candidate.agent(observation, configuration)
    try:
        _record(observation, action)
    except (OSError, TypeError, ValueError, OverflowError):
        # Telemetry is evidence-only and may never take the game down.
        pass
    return action


__all__ = ["agent"]
