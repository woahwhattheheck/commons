"""Deterministic UArk historical replay and process-time current checks."""
from __future__ import annotations

import copy
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CORE_PATH = Path(__file__).with_name("_qualifier_core.py").resolve()
_SPEC = importlib.util.spec_from_file_location(
    "uark_rfp09112026_qualifier_historical_core", _CORE_PATH
)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"cannot load UArk qualifier core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

InputError = _core.InputError
canonical_json = _core.canonical_json
sha256_obj = _core.sha256_obj
read_json_file = _core.read_json_file

CURRENT_VERIFICATION_SCHEMA = "uark-rfp09112026-current-verification/v1"
CURRENT_AUTHORITY_MODE = "ISOLATED_CLI_PROCESS_UTC"
ADDENDUM_RECHECK_BOUNDARY_UTC = "2026-10-06T05:00:00Z"
_PACKET_FIELDS = frozenset({
    "schema", "operation", "owner", "model", "evaluated_at_utc", "buyer",
    "rfp_number", "question_deadline_utc", "proposal_deadline_utc",
    "last_planned_addendum_date", "internal_workshare_target_usd",
    "price_boundary", "source_generation", "candidate", "decision",
    "packet_receipt_sha256",
})


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InputError("current authority clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _refresh_receipts(packet: dict[str, Any]) -> dict[str, Any]:
    decision = packet["decision"]
    decision.pop("decision_receipt_sha256", None)
    decision["decision_receipt_sha256"] = sha256_obj(decision)
    packet.pop("packet_receipt_sha256", None)
    packet["packet_receipt_sha256"] = sha256_obj(packet)
    return packet


def _apply_temporal_policy(packet: dict[str, Any]) -> dict[str, Any]:
    evaluated = _dt(packet["evaluated_at_utc"])
    source_checked = _dt(packet["source_generation"]["hogbid_checked_at_utc"])
    recheck_boundary = _dt(ADDENDUM_RECHECK_BOUNDARY_UTC)
    blockers: list[str] = []
    if evaluated < source_checked:
        blockers.append("EVALUATION_PRECEDES_SOURCE_CAPTURE")
    if (
        evaluated >= recheck_boundary
        and source_checked < recheck_boundary
        and packet["source_generation"]["addenda_state"] == "NONE_LISTED"
    ):
        blockers.append("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED")
    if not blockers:
        return packet
    decision = packet["decision"]
    merged = list(decision["blockers"])
    for blocker in blockers:
        if blocker not in merged:
            merged.append(blocker)
    decision["blockers"] = merged
    if decision["status"] != "NO_BID":
        decision["status"] = "HOLD"
    decision["submission_ready"] = False
    return _refresh_receipts(packet)


def compile_historical(intake: Any) -> dict[str, Any]:
    """Explicit-time deterministic replay; never CURRENT authority."""
    return _apply_temporal_policy(_core.compile_qualification(intake))


def verify_packet_historical(packet: Any) -> bool:
    """Verify bytes and semantics at the packet's declared replay instant."""
    if not isinstance(packet, dict) or set(packet) != _PACKET_FIELDS:
        raise InputError("packet schema mismatch")
    receipt = packet.get("packet_receipt_sha256")
    if not isinstance(receipt, str) or not _core.SHA_RE.fullmatch(receipt):
        raise InputError("packet receipt invalid")
    unsigned = copy.deepcopy(packet)
    unsigned.pop("packet_receipt_sha256")
    if sha256_obj(unsigned) != receipt:
        raise InputError("packet receipt mismatch")
    expected = compile_historical({
        "schema": _core.SCHEMA,
        "evaluated_at_utc": packet["evaluated_at_utc"],
        "source_generation": packet["source_generation"],
        "candidate": packet["candidate"],
    })
    if packet != expected:
        raise InputError("packet semantic verification failed")
    return True


def _decision_body(decision: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(decision)
    value.pop("decision_receipt_sha256", None)
    return value


def _compile_at_now(intake: Any, now: datetime) -> dict[str, Any]:
    if not isinstance(intake, dict):
        raise InputError("intake must be an object")
    stamped = copy.deepcopy(intake)
    stamped["evaluated_at_utc"] = utc_text(now)
    return compile_historical(stamped)


def _verify_at_now(packet: Any, now: datetime) -> dict[str, Any]:
    verify_packet_historical(packet)
    if _dt(packet["evaluated_at_utc"]) > now:
        raise InputError("packet evaluation time is ahead of process UTC")
    current = compile_historical({
        "schema": _core.SCHEMA,
        "evaluated_at_utc": utc_text(now),
        "source_generation": packet["source_generation"],
        "candidate": packet["candidate"],
    })
    if _decision_body(packet["decision"]) != _decision_body(current["decision"]):
        raise InputError("packet decision is no longer current")
    verification = {
        "schema": CURRENT_VERIFICATION_SCHEMA,
        "authority_mode": CURRENT_AUTHORITY_MODE,
        "verified_at_utc": utc_text(now),
        "packet_receipt_sha256": packet["packet_receipt_sha256"],
        "current_decision_receipt_sha256": current["decision"][
            "decision_receipt_sha256"
        ],
        "decision_status": current["decision"]["status"],
        "current": True,
        "external_actions_authorized": False,
    }
    verification["verification_receipt_sha256"] = sha256_obj(verification)
    return verification
