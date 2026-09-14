"""Source-generation gates for IMPO MTP 2055 readiness."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .engine_core import SOURCE_FRESH, SOURCE_STALE, _evidence_row, _row

def _source_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    opportunity = packet["opportunity"]
    source = packet["source_checks"]
    as_of = datetime.fromisoformat(packet["as_of"])
    last_checked = datetime.fromisoformat(source["last_checked_at"])
    questions_due = datetime.fromisoformat(opportunity["questions_due_at"])
    proposal_due = datetime.fromisoformat(opportunity["proposal_due_at"])
    rows: list[dict[str, Any]] = []

    digest = opportunity["source_sha256"]
    if digest is None or not source["base_rfp_bytes_verified"]:
        rows.append(
            _row(
                "SRC-001",
                "SOURCE",
                "Exact base RFP bytes and SHA-256",
                "BLOCKED",
                "The public URL is known, but exact source bytes have not been independently retrieved and hashed.",
                blocking=True,
            )
        )
    else:
        rows.append(
            _row(
                "SRC-001",
                "SOURCE",
                "Exact base RFP bytes and SHA-256",
                "READY",
                "The base RFP generation is bound to an exact SHA-256 digest.",
                blocking=False,
                evidence_reference=f"sha256:{digest}",
            )
        )

    age = as_of - last_checked
    if age < timedelta(0):
        raise RuntimeError("validated source check is in the future")
    if age <= SOURCE_FRESH:
        disposition, blocking, reason = (
            "READY",
            False,
            f"Official source was checked {int(age.total_seconds())} seconds before as_of.",
        )
    elif age <= SOURCE_STALE:
        disposition, blocking, reason = (
            "AT_RISK",
            False,
            f"Official source check is {age.days} day(s) old; refresh before final owner review.",
        )
    else:
        disposition, blocking, reason = (
            "BLOCKED",
            True,
            f"Official source check is {age.days} day(s) old and is not current enough for submission.",
        )
    rows.append(
        _row(
            "SRC-002",
            "SOURCE",
            "Current official-source check",
            disposition,
            reason,
            blocking=blocking,
            evidence_reference=source["last_checked_at"],
        )
    )

    unsigned = [item["id"] for item in source["addenda"] if not item["signed_acknowledgement"]]
    if unsigned:
        rows.append(
            _row(
                "SRC-003",
                "SOURCE",
                "All discovered addenda acknowledged",
                "BLOCKED",
                "Unsigned addenda: " + ", ".join(unsigned),
                blocking=True,
            )
        )
    else:
        rows.append(
            _row(
                "SRC-003",
                "SOURCE",
                "All discovered addenda acknowledged",
                "READY",
                f"{len(source['addenda'])} discovered addendum/addenda are acknowledged.",
                blocking=False,
            )
        )

    question_evidence = source["questions_addendum"]
    if as_of < questions_due:
        if question_evidence["state"] == "VERIFIED":
            rows.append(
                _evidence_row(
                    "SRC-004",
                    "SOURCE",
                    "Questions addendum generation",
                    question_evidence,
                )
            )
        else:
            rows.append(
                _row(
                    "SRC-004",
                    "SOURCE",
                    "Questions addendum generation",
                    "DEFERRED",
                    "The questions deadline has not yet passed; the final addendum may not exist yet and must be rechecked after publication.",
                    blocking=False,
                )
            )
    else:
        rows.append(
            _evidence_row(
                "SRC-004",
                "SOURCE",
                "Questions addendum generation",
                question_evidence,
                mandatory=True,
                missing_reason="The questions deadline has passed; the posted questions addendum must be retrieved, reviewed, and signed.",
            )
        )

    if as_of >= proposal_due:
        rows.append(
            _row(
                "SRC-005",
                "SOURCE",
                "Proposal deadline remains open",
                "BLOCKED",
                "The deterministic as_of timestamp is at or after the proposal deadline.",
                blocking=True,
            )
        )
    else:
        seconds = int((proposal_due - as_of).total_seconds())
        rows.append(
            _row(
                "SRC-005",
                "SOURCE",
                "Proposal deadline remains open",
                "READY",
                f"Proposal deadline is {seconds} seconds after as_of.",
                blocking=False,
                evidence_reference=opportunity["proposal_due_at"],
            )
        )
    return rows


