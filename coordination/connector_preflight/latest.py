"""Latest-generation policy overlay for connector preflight evidence.

The base engine validates every supplied row. This overlay narrows decision
semantics to the newest complete, unfiltered GitHub+Slack discovery so an older
catalog or action result cannot overrule newer provider evidence.

The normalized JSON is caller-authored and its SHA-256 fields are integrity
pointers, not provider authentication. Consequently this compiler never grants
a NO_WRITE_RAIL blocker from those rows alone.
"""
from __future__ import annotations

import os
import stat
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import core as _core

_BASE_EVALUATE = getattr(
    _core, "_CONNECTOR_PREFLIGHT_BASE_EVALUATE", _core.evaluate
)
_core._CONNECTOR_PREFLIGHT_BASE_EVALUATE = _BASE_EVALUATE
_BASE_COMPILE_AT = getattr(
    _core, "_CONNECTOR_PREFLIGHT_BASE_COMPILE_AT", _core.compile_at
)
_core._CONNECTOR_PREFLIGHT_BASE_COMPILE_AT = _BASE_COMPILE_AT
MAX_FILE_BYTES = _core.MAX_FILE_BYTES
HOST_CURRENT_MAX_AGE_SECONDS = 3600


def _prepare_latest(
    normalized: dict[str, Any],
) -> tuple[dict[str, Any], list[str], dict[str, Any] | None]:
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
        if row["complete"]
        and row["query"] is None
        and set(row["paths"]) == all_connectors
    ]
    if not qualified:
        return prepared, sorted(set(overlay_reasons)), None

    latest_completed_at = max(row["completed_at"] for row in qualified)
    latest_rows = [
        row for row in qualified if row["completed_at"] == latest_completed_at
    ]
    if len({_core.canonical_json(row["actions"]) for row in latest_rows}) > 1:
        overlay_reasons.append("LATEST_DISCOVERY_CATALOG_CONFLICT")

    # The conflict above forces HOLD. request_id is only a deterministic
    # tie-breaker for the packet bytes, never an authority selector.
    winner = max(latest_rows, key=lambda row: row["request_id"])
    removed_ids = {
        row["request_id"]
        for row in qualified
        if row["request_id"] != winner["request_id"]
    }
    prepared["discoveries"] = [
        row
        for row in prepared["discoveries"]
        if row["request_id"] not in removed_ids
    ]
    prepared["attempts"] = [
        row
        for row in prepared["attempts"]
        if row["discovery_request_id"] not in removed_ids
    ]

    _, attempt_conflicts = _latest_action_attempts(prepared, winner)
    overlay_reasons.extend(attempt_conflicts)
    return prepared, sorted(set(overlay_reasons)), winner


def _latest_action_attempts(
    prepared: dict[str, Any],
    winner: dict[str, Any] | None,
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    if winner is None:
        return {}, []

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in prepared["attempts"]:
        if (
            row["discovery_request_id"] != winner["request_id"]
            or row["access"] != "WRITE"
        ):
            continue
        grouped.setdefault((row["connector"], row["action"]), []).append(row)

    latest: dict[tuple[str, str], dict[str, Any]] = {}
    conflicts: list[str] = []
    for identity, rows in grouped.items():
        latest_at = max(row["attempted_at"] for row in rows)
        generation = [row for row in rows if row["attempted_at"] == latest_at]
        results = {row["result"] for row in generation}
        if len(results) > 1:
            conflicts.append(
                f"LATEST_ATTEMPT_CONFLICT_{identity[0]}_{identity[1]}"
            )
        latest[identity] = max(generation, key=lambda row: row["attempt_id"])
    return latest, sorted(set(conflicts))


def _derive_latest_write_truth(
    packet: dict[str, Any],
    prepared: dict[str, Any],
    winner: dict[str, Any] | None,
) -> bool:
    """Replace base historical reduction with latest-generation-only truth.

    Returns True only when both connector rows would otherwise support a
    NO_WRITE_RAIL blocker. The caller-authored carrier cannot authenticate that
    conclusion, so the caller converts that candidate to HOLD.
    """
    if winner is None:
        packet["authority"]["provider_evidence_authenticated"] = False
        return False

    latest, _ = _latest_action_attempts(prepared, winner)
    blocker_candidates: dict[str, bool] = {}
    for connector_row in packet["connectors"]:
        connector = connector_row["connector"]
        required = prepared["policy"]["required_actions"][connector]
        writes = {
            action["name"]
            for action in winner["actions"]
            if action["connector"] == connector and action["access"] == "WRITE"
        }
        latest_for_connector = {
            action: row
            for (row_connector, action), row in latest.items()
            if row_connector == connector and action in writes
        }
        read_failures = [
            row
            for row in prepared["attempts"]
            if row["connector"] == connector
            and row["access"] == "READ"
            and row["result"] != "SUCCESS"
        ]

        reasons: list[str] = []
        blocker_candidate = False
        if not writes:
            state = "DISCOVERED_READ_ONLY"
            reasons.append("COMPLETE_DISCOVERY_REPORTS_NO_WRITE_ACTIONS")
            blocker_candidate = packet["claim"] == "NO_WRITE_RAIL"
        elif any(
            row["result"] == "SUCCESS" for row in latest_for_connector.values()
        ):
            state = "WRITE_RAIL_CONFIRMED"
            reasons.append("LATEST_WRITE_ACTION_SUCCEEDED")
        elif not latest_for_connector:
            state = (
                "WRITE_ATTEMPT_REQUIRED"
                if packet["claim"] == "NO_WRITE_RAIL"
                else "WRITE_ACTIONS_EXPOSED"
            )
            reasons.append("RELEVANT_WRITE_ATTEMPT_MISSING")
        elif set(latest_for_connector) != writes:
            state = (
                "WRITE_ATTEMPT_REQUIRED"
                if packet["claim"] == "NO_WRITE_RAIL"
                else "WRITE_ACTIONS_EXPOSED"
            )
            reasons.append("EXPOSED_WRITE_ACTIONS_REMAIN_UNPROVEN")
        elif all(
            row["result"] == "UNAVAILABLE"
            for row in latest_for_connector.values()
        ):
            state = "WRITE_ATTEMPT_FAILED"
            reasons.append("ALL_EXPOSED_WRITE_ACTIONS_UNAVAILABLE")
            blocker_candidate = packet["claim"] == "NO_WRITE_RAIL"
        else:
            state = "WRITE_ATTEMPT_FAILED"
            reasons.append("WRITE_FAILURE_DOES_NOT_PROVE_RAIL_ABSENCE")

        if read_failures:
            reasons.append("READ_FAILURE_DOES_NOT_PROVE_WRITE_ABSENCE")
        if blocker_candidate:
            reasons.append("CALLER_EVIDENCE_IS_NOT_PROVIDER_AUTHENTICATION")

        connector_row.clear()
        connector_row.update(
            {
                "connector": connector,
                "state": state,
                "required_write_actions": required,
                "exposed_required_write_actions": sorted(
                    set(required) & writes
                ),
                "blocker_supported": False,
                "reasons": sorted(set(reasons)),
            }
        )
        blocker_candidates[connector] = blocker_candidate

    packet["authority"]["provider_evidence_authenticated"] = False
    return (
        packet["claim"] == "NO_WRITE_RAIL"
        and all(blocker_candidates.get(connector, False) for connector in _core.CONNECTORS)
    )


def _recompute_overall(
    packet: dict[str, Any], overlay_reasons: list[str]
) -> None:
    if overlay_reasons:
        packet["overall_state"] = "HOLD"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = sorted(
            set(packet["reasons"] + overlay_reasons)
        )
        return
    if packet["overall_state"] == "HOLD":
        packet["work_blocked_claim_supported"] = False
        return

    rows = packet["connectors"]
    if all(row["state"] == "WRITE_RAIL_CONFIRMED" for row in rows):
        packet["overall_state"] = "WRITE_RAIL_CONFIRMED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = ["GITHUB_AND_SLACK_WRITE_RAILS_CONFIRMED"]
    elif any(row["state"] == "WRITE_ATTEMPT_REQUIRED" for row in rows):
        packet["overall_state"] = "WRITE_ATTEMPT_REQUIRED"
        packet["work_blocked_claim_supported"] = False
        packet["reasons"] = [
            "NO_WRITE_RAIL_CLAIM_REQUIRES_RELEVANT_WRITE_ATTEMPTS"
        ]
    elif any(
        row["state"]
        in {
            "WRITE_ACTIONS_EXPOSED",
            "WRITE_ATTEMPT_FAILED",
            "WRITE_RAIL_CONFIRMED",
        }
        for row in rows
    ):
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
        packet["reasons"] = [
            "CALLER_EVIDENCE_IS_NOT_PROVIDER_AUTHENTICATION"
        ]


def _current_generation_reasons(
    prepared: dict[str, Any],
    winner: dict[str, Any] | None,
    evaluated_at: datetime,
    mode: str,
) -> list[str]:
    if mode != "CURRENT" or winner is None:
        return []

    effective_max_age = min(
        prepared["policy"]["max_age_seconds"],
        HOST_CURRENT_MAX_AGE_SECONDS,
    )
    reasons: list[str] = []
    discovery_age = int(
        (
            evaluated_at
            - _core.parse_utc(winner["completed_at"])
        ).total_seconds()
    )
    if discovery_age > effective_max_age:
        reasons.append("CONTROLLING_DISCOVERY_STALE")

    latest, _ = _latest_action_attempts(prepared, winner)
    for (connector, action), row in latest.items():
        age = int(
            (
                evaluated_at
                - _core.parse_utc(row["attempted_at"])
            ).total_seconds()
        )
        if age > effective_max_age:
            reasons.append(
                f"LATEST_WRITE_ATTEMPT_STALE_{connector}_{action}"
            )
    return sorted(set(reasons))


def evaluate(
    normalized: dict[str, Any],
    evaluated_at: datetime,
    mode: str,
) -> dict[str, Any]:
    prepared, overlay_reasons, winner = _prepare_latest(normalized)
    overlay_reasons.extend(
        _current_generation_reasons(
            prepared, winner, evaluated_at, mode
        )
    )
    packet = _BASE_EVALUATE(prepared, evaluated_at, mode)
    unauthenticated_blocker = _derive_latest_write_truth(
        packet, prepared, winner
    )
    if unauthenticated_blocker:
        overlay_reasons.append(
            "CALLER_EVIDENCE_CANNOT_SUPPORT_NO_WRITE_RAIL"
        )
    _recompute_overall(packet, sorted(set(overlay_reasons)))
    return packet


def compile_at(raw: Any, evaluated_at: datetime) -> dict[str, Any]:
    """Compile a deterministic historical-integrity receipt.

    Explicit caller time is never a CURRENT authority path.
    """
    return _BASE_COMPILE_AT(
        raw, evaluated_at, mode="HISTORICAL_INTEGRITY_ONLY"
    )


def _compile_current_at(
    raw: Any, evaluated_at: datetime
) -> dict[str, Any]:
    evaluated = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    return _BASE_COMPILE_AT(raw, evaluated, mode="CURRENT")


def compile_current(raw: Any) -> dict[str, Any]:
    """Compile current capability truth using process-owned UTC only."""
    return _compile_current_at(raw, _core.utc_now())


def verify_integrity(raw: Any, bundle: Any) -> bool:
    try:
        supplied = _core._validate_bundle_shape(bundle)
        packet = supplied["packet"]
        if type(packet) is not dict:
            return False
        evaluated = _core.parse_utc(
            packet.get("evaluated_at"),
            "$bundle.packet.evaluated_at",
        )
        mode = packet.get("evaluation_mode")
        if mode not in _core.MODES:
            return False
        rebuilt = _BASE_COMPILE_AT(raw, evaluated, mode=mode)
        return _core.canonical_json(rebuilt) == _core.canonical_json(
            supplied
        )
    except (
        _core.PreflightError,
        KeyError,
        TypeError,
        ValueError,
        RecursionError,
    ):
        return False


def _verify_current_at(
    raw: Any,
    bundle: Any,
    evaluated_at: datetime,
) -> dict[str, Any]:
    integrity = verify_integrity(raw, bundle)
    evaluated = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    result: dict[str, Any] = {
        "schema": "commons.connector-preflight-verification/v1",
        "integrity_valid": integrity,
        "current_valid": False,
        "evaluated_at": _core.format_utc(evaluated),
        "current_state": "INVALID",
        "reasons": [],
    }
    if not integrity:
        result["reasons"] = ["BUNDLE_INTEGRITY_INVALID"]
        return result
    try:
        current_bundle = _compile_current_at(raw, evaluated)
    except _core.PreflightError as exc:
        result["current_state"] = "STALE_OR_INVALID"
        result["reasons"] = [str(exc)]
        return result

    original_packet = _core._validate_bundle_shape(bundle)["packet"]
    current_packet = current_bundle["packet"]
    current = (
        _core._semantic_projection(original_packet)
        == _core._semantic_projection(current_packet)
    )
    result["current_valid"] = current
    result["current_state"] = current_packet["overall_state"]
    result["reasons"] = [] if current else ["CURRENT_SEMANTICS_DRIFTED"]
    return result


def verify_current(raw: Any, bundle: Any) -> dict[str, Any]:
    """Verify current capability truth using process-owned UTC only."""
    return _verify_current_at(raw, bundle, _core.utc_now())


def _generation(info: Any) -> tuple[int, ...]:
    return (
        int(info.st_mode),
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_nlink),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
    )


def read_json_file(
    path: Path, *, max_bytes: int = MAX_FILE_BYTES
) -> Any:
    """Read one retained regular-file generation through a stable pathname."""
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
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise _core.PreflightError("input must be a regular file")
        if before.st_size > max_bytes:
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

        after = os.fstat(fd)
        if _generation(after) != _generation(before):
            raise _core.PreflightError(
                "input generation changed while being read"
            )
        try:
            visible = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            raise _core.PreflightError(
                f"input pathname disappeared during read: {exc}"
            ) from exc
        if not stat.S_ISREG(visible.st_mode):
            raise _core.PreflightError(
                "input pathname no longer names a regular file"
            )
        if (visible.st_dev, visible.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise _core.PreflightError(
                "input pathname was replaced during read"
            )
        if _generation(visible) != _generation(before):
            raise _core.PreflightError(
                "input pathname generation changed during read"
            )
    finally:
        os.close(fd)

    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise _core.PreflightError(
            "input is not strict UTF-8"
        ) from exc
    return _core.strict_loads(text)


# Install the policy overlay and public authority boundary once per import.
_core.evaluate = evaluate
_core.compile_at = compile_at
_core._compile_current_at = _compile_current_at
_core.compile_current = compile_current
_core.verify_integrity = verify_integrity
_core._verify_current_at = _verify_current_at
_core.verify_current = verify_current
_core.read_json_file = read_json_file

PreflightError = _core.PreflightError
strict_loads = _core.strict_loads
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
