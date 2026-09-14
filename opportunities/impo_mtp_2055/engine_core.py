"""Deterministic, fail-closed bid-readiness compilation for IMPO MTP 2055."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

ENGINE_VERSION = "1.0.0"
SOURCE_FRESH = timedelta(hours=24)
SOURCE_STALE = timedelta(days=7)

STAGE_ORDER = {"SOURCE": 0, "SUBMISSION": 1, "COMMERCIAL": 2, "AWARD": 3, "AUTHORITY": 4}
DISPOSITION_ORDER = {"BLOCKED": 0, "AT_RISK": 1, "DEFERRED": 2, "READY": 3}


class PacketVerificationError(ValueError):
    """Raised when a compiled receipt or Markdown packet does not verify exactly."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _row(
    identifier: str,
    stage: str,
    title: str,
    disposition: str,
    reason: str,
    *,
    blocking: bool,
    evidence_reference: str | None = None,
) -> dict[str, Any]:
    if stage not in STAGE_ORDER:
        raise RuntimeError(f"unknown stage {stage}")
    if disposition not in DISPOSITION_ORDER:
        raise RuntimeError(f"unknown disposition {disposition}")
    return {
        "id": identifier,
        "stage": stage,
        "title": title,
        "disposition": disposition,
        "blocking": bool(blocking),
        "reason": reason,
        "evidence_reference": evidence_reference,
    }


def _candidate_note(prefix: str, note: Any) -> str:
    if note:
        return f"{prefix} Candidate note: {note}"
    return prefix


def _evidence_row(
    identifier: str,
    stage: str,
    title: str,
    evidence: dict[str, Any],
    *,
    mandatory: bool = True,
    missing_disposition: str | None = None,
    missing_reason: str | None = None,
) -> dict[str, Any]:
    state = evidence["state"]
    reference = evidence["reference"]
    note = evidence["note"]
    if state == "VERIFIED":
        return _row(
            identifier,
            stage,
            title,
            "READY",
            _candidate_note(
                "Candidate input marks this evidence VERIFIED; this package does not independently authenticate it.",
                note,
            ),
            blocking=False,
            evidence_reference=reference,
        )
    if state == "NOT_APPLICABLE":
        if mandatory:
            return _row(
                identifier,
                stage,
                title,
                "BLOCKED",
                _candidate_note(
                    "Candidate input marks a mandatory requirement not applicable.",
                    note,
                ),
                blocking=True,
            )
        return _row(
            identifier,
            stage,
            title,
            "DEFERRED",
            _candidate_note(
                "Candidate input marks this non-mandatory requirement not applicable.",
                note,
            ),
            blocking=False,
        )
    disposition = missing_disposition or ("BLOCKED" if mandatory else "DEFERRED")
    blocking = mandatory and disposition == "BLOCKED"
    reason = missing_reason or _candidate_note(f"Candidate evidence state is {state}.", note)
    return _row(identifier, stage, title, disposition, reason, blocking=blocking)
