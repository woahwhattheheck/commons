"""Latest-generation policy overlay for connector preflight evidence.

The base engine validates every supplied row. This overlay narrows decision
semantics to the newest complete, unfiltered GitHub+Slack discovery so an older
catalog or action result cannot overrule newer provider evidence.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from . import core as _core

_BASE_EVALUATE = _core.evaluate


def _prepare_latest(normalized: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    prepared = deepcopy(normalized)
    overlay_reasons: list[str] = []
    access_by_identity: dict[tuple[str, str], str] = {}
    for discovery in prepared["discoveries"]:
        for action in discovery["actions"]:
            identity = (action["connector"], action["name"])
            previous = access_by_identity.get(identity)
            if previous is not None and previous != action["access"]:
                overlay_reasons.append(
                    f"ACTION_ACCESS_CONFLICT_{action['connector']}_{action['name']}"
                )
            access_by_identity[identity] = action["access"]
    all_connectors = set(_core.CONNECTORS)
    qualified = [
        row
        for row in prepared["discoveries"]
        if row["complete"] and row["query"] is None and set(row["paths"]) == all_connectors
    ]
    if not qualified:
        return prepared, sorted(set(overlay_reasons))

    latest_completed_at = max(row["completed_at"] for row in qualified)
    latest_rows = [row for row in qualified if row["completed_at"] == latest_completed_at]
    catalog_conflict = len({_core.canonical_json(row["actions"]) for row in latest_rows}) > 1
    if catalog_conflict:
        overlay_reasons.append("LATEST_DISCOVERY_CATALOG_CONFLICT")
    winner = max(latest_rows, key=lambda row: row["request_id"])
    removed_ids = {row["request_id"] for row in qualified if row["request_id"] != winner["request_id"]}
    prepared["discoveries"] = [
        row for row in prepared["discoveries"] if row["request_id"] not in removed_ids
    ]
    prepared["attempts"] = [
        row for row in prepared["attempts"] if row["discovery_request_id"] not in removed_ids
    ]
    return prepared, sorted(set(overlay_reasons))


def evaluate(normalized: dict[str, Any], evaluated_at: datetime, mode: str) -> dict[str, Any]:
    prepared, overlay_reasons = _prepare_latest(normalized)
    packet = _BASE_EVALUATE(prepared, evaluated_at, mode)
    if overlay_reasons:
        packet["overall_state"] = "HOLD"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = sorted(set(packet["reasons"] + overlay_reasons))
    return packet


# compile_at and compile_current resolve evaluate from the base module at runtime.
# Install the overlay once, then re-export the public surface.
_core.evaluate = evaluate

PreflightError = _core.PreflightError
compile_at = _core.compile_at
compile_current = _core.compile_current
strict_loads = _core.strict_loads
verify_current = _core.verify_current
verify_integrity = _core.verify_integrity
read_json_file = _core.read_json_file
write_json_exclusive = _core.write_json_exclusive

__all__ = [
    "PreflightError",
    "compile_at",
    "compile_current",
    "evaluate",
    "strict_loads",
    "verify_current",
    "verify_integrity",
    "read_json_file",
    "write_json_exclusive",
]
