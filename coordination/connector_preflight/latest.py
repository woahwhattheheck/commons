"""Latest-generation policy overlay for connector preflight evidence.

The base engine validates every supplied row. This overlay narrows decision
semantics to the newest complete, unfiltered GitHub+Slack discovery so an older
catalog or action result cannot overrule newer provider evidence.
"""
from __future__ import annotations

import os
import stat
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from . import core as _core

_BASE_EVALUATE = _core.evaluate
MAX_FILE_BYTES = _core.MAX_FILE_BYTES


def _prepare_latest(normalized: dict[str, Any]) -> tuple[dict[str, Any], list[str], dict[str, Any] | None]:
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
        return prepared, sorted(set(overlay_reasons)), None

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
    return prepared, sorted(set(overlay_reasons)), winner


def _latest_write_truth(packet: dict[str, Any], prepared: dict[str, Any], winner: dict[str, Any] | None) -> None:
    if winner is None:
        return
    attempts = [
        row
        for row in prepared["attempts"]
        if row["discovery_request_id"] == winner["request_id"] and row["access"] == "WRITE"
    ]
    for connector_row in packet["connectors"]:
        connector = connector_row["connector"]
        writes = {
            action["name"]
            for action in winner["actions"]
            if action["connector"] == connector and action["access"] == "WRITE"
        }
        latest_by_action: dict[str, dict[str, Any]] = {}
        for row in attempts:
            if row["connector"] != connector or row["action"] not in writes:
                continue
            previous = latest_by_action.get(row["action"])
            if previous is None or (row["attempted_at"], row["attempt_id"]) > (
                previous["attempted_at"],
                previous["attempt_id"],
            ):
                latest_by_action[row["action"]] = row
        if any(row["result"] == "SUCCESS" for row in latest_by_action.values()):
            connector_row["state"] = "WRITE_RAIL_CONFIRMED"
            connector_row["blocker_supported"] = False
            connector_row["reasons"] = sorted(set(connector_row["reasons"] + ["WRITE_ACTION_SUCCEEDED"]))
            continue
        if writes and connector_row["state"] == "DISCOVERED_READ_ONLY":
            connector_row["state"] = (
                "WRITE_ATTEMPT_REQUIRED" if packet["claim"] == "NO_WRITE_RAIL" else "WRITE_ACTIONS_EXPOSED"
            )
            connector_row["blocker_supported"] = False
            connector_row["reasons"] = sorted(
                set(connector_row["reasons"] + ["OTHER_WRITE_ACTIONS_EXPOSED_REQUIRED_PROBE_MISSING"])
            )
        if connector_row["blocker_supported"]:
            unavailable = {
                action for action, row in latest_by_action.items() if row["result"] == "UNAVAILABLE"
            }
            untested_or_nonterminal = writes - unavailable
            if untested_or_nonterminal:
                connector_row["blocker_supported"] = False
                connector_row["state"] = "WRITE_ATTEMPT_REQUIRED"
                connector_row["reasons"] = sorted(
                    set(connector_row["reasons"] + ["EXPOSED_WRITE_ACTIONS_REMAIN_UNPROVEN"])
                )


def _recompute_overall(packet: dict[str, Any], overlay_reasons: list[str]) -> None:
    if overlay_reasons:
        packet["overall_state"] = "HOLD"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = sorted(set(packet["reasons"] + overlay_reasons))
        return
    if packet["overall_state"] == "HOLD":
        packet["work_blocked_claim_supported"] = False
        return
    rows = packet["connectors"]
    if packet["claim"] == "NO_WRITE_RAIL" and all(row["blocker_supported"] for row in rows):
        packet["overall_state"] = "BLOCKER_SUPPORTED"
        packet["work_blocked_claim_supported"] = True
        packet["reasons"] = ["COMPLETE_EVIDENCE_SUPPORTS_NO_WRITE_RAIL"]
    elif all(row["state"] == "WRITE_RAIL_CONFIRMED" for row in rows):
        packet["overall_state"] = "WRITE_RAIL_CONFIRMED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["GITHUB_AND_SLACK_WRITE_RAILS_CONFIRMED"]
    elif any(row["state"] == "WRITE_ATTEMPT_REQUIRED" for row in rows):
        packet["overall_state"] = "WRITE_ATTEMPT_REQUIRED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["NO_WRITE_RAIL_CLAIM_REQUIRES_RELEVANT_WRITE_ATTEMPTS"]
    elif any(row["state"] in {"WRITE_ACTIONS_EXPOSED", "WRITE_ATTEMPT_FAILED", "WRITE_RAIL_CONFIRMED"} for row in rows):
        packet["overall_state"] = "WRITE_ACTIONS_EXPOSED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["WRITE_CAPABILITY_PRESENT_OR_NOT_DISPROVEN"]
    elif any(row["state"] == "NOT_DISCOVERED" for row in rows):
        packet["overall_state"] = "NOT_DISCOVERED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["COMPLETE_DISCOVERY_REQUIRED"]
    else:
        packet["overall_state"] = "DISCOVERED_READ_ONLY"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["REQUIRED_WRITE_ACTIONS_NOT_EXPOSED"]


def evaluate(normalized: dict[str, Any], evaluated_at: datetime, mode: str) -> dict[str, Any]:
    prepared, overlay_reasons, winner = _prepare_latest(normalized)
    packet = _BASE_EVALUATE(prepared, evaluated_at, mode)
    _latest_write_truth(packet, prepared, winner)
    _recompute_overall(packet, overlay_reasons)
    return packet


def read_json_file(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> Any:
    """Open once, nonblocking/no-follow where available, then require regular."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise _core.PreflightError(f"cannot open input: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise _core.PreflightError("input must be a regular file")
        if info.st_size > max_bytes:
            raise _core.PreflightError("input exceeds size limit")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise _core.PreflightError("input grew beyond size limit")
    finally:
        os.close(fd)
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise _core.PreflightError("input is not strict UTF-8") from exc
    return _core.strict_loads(text)


# compile_at and compile_current resolve evaluate from the base module at runtime.
# Install overlays once, then re-export the public surface.
_core.evaluate = evaluate
_core.read_json_file = read_json_file

PreflightError = _core.PreflightError
compile_at = _core.compile_at
compile_current = _core.compile_current
strict_loads = _core.strict_loads
verify_current = _core.verify_current
verify_integrity = _core.verify_integrity
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
