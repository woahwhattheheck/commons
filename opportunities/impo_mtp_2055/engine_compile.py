"""Receipt compilation and exact verification for IMPO MTP 2055 readiness."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any

from .engine_core import (
    DISPOSITION_ORDER,
    ENGINE_VERSION,
    PacketVerificationError,
    STAGE_ORDER,
    canonical_json_bytes,
    sha256_hex,
)
from .engine_evidence import (
    _authority_rows,
    _capability_rows,
    _document_rows,
    _pricing_rows,
    _project_rows,
)
from .engine_organization import _organization_rows, _team_rows
from .engine_render import _status, render_markdown
from .engine_source import _source_rows
from .schema import validate_input

HISTORICAL_INTEGRITY_ONLY = "HISTORICAL_INTEGRITY_ONLY"
CURRENT_PROCESS_UTC = "CURRENT_PROCESS_UTC"
CURRENT_RECEIPT_MAX_AGE = timedelta(minutes=5)
CURRENT_FUTURE_SKEW = timedelta(seconds=5)


def _normalized_with_as_of(value: Any, as_of: datetime) -> dict[str, Any]:
    candidate = copy.deepcopy(value)
    if not isinstance(candidate, dict):
        # Preserve the schema validator as the canonical type/error boundary.
        return validate_input(candidate)
    candidate["as_of"] = as_of.isoformat()
    return validate_input(candidate)


def _base_receipt(packet: dict[str, Any]) -> dict[str, Any]:
    input_sha = sha256_hex(canonical_json_bytes(packet))
    rows = (
        _source_rows(packet)
        + _organization_rows(packet)
        + _team_rows(packet)
        + _project_rows(packet)
        + _capability_rows(packet)
        + _document_rows(packet)
        + _pricing_rows(packet)
        + _authority_rows(packet)
    )
    rows.sort(
        key=lambda row: (
            STAGE_ORDER[row["stage"]],
            row["id"],
            DISPOSITION_ORDER[row["disposition"]],
        )
    )
    identifiers = [row["id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError("compiler produced duplicate gate ids")
    counts = {key: sum(row["disposition"] == key for row in rows) for key in DISPOSITION_ORDER}
    status = _status(rows)
    # This package is deliberately owner-review only. Candidate assertions can
    # never authenticate external authority or mint a submission-ready state.
    if status == "SUBMISSION_READY":
        status = "OWNER_REVIEW_READY"
    return {
        "schema_version": packet["schema_version"],
        "engine_version": ENGINE_VERSION,
        "input_sha256": input_sha,
        "as_of": packet["as_of"],
        "opportunity": packet["opportunity"],
        "source_checks": packet["source_checks"],
        "status": status,
        "submission_ready": False,
        "evidence_authority": "CANDIDATE_ASSERTIONS_ONLY",
        "external_authority_authenticated": False,
        "counts": counts,
        "gates": rows,
        "pricing": {
            "tasks": packet["pricing"]["tasks"],
            "total_minor": packet["pricing"]["stated_total_minor"],
            "commercial_approval": packet["pricing"]["commercial_approval"],
        },
        "authority": packet["authority"],
        "owner_notes": packet["owner_notes"],
    }


def _finish_receipt(packet: dict[str, Any], *, evaluation_mode: str) -> tuple[dict[str, Any], str]:
    receipt = _base_receipt(packet)
    receipt["evaluation_mode"] = evaluation_mode
    receipt["receipt_sha256"] = sha256_hex(canonical_json_bytes(receipt))
    markdown = render_markdown(receipt)
    return receipt, markdown


def compile_packet(value: Any) -> tuple[dict[str, Any], str]:
    """Compile an explicit-time historical owner-review artifact.

    The caller controls ``as_of`` in this mode. The receipt is therefore labeled
    historical integrity only and is never current or external authority.
    """
    packet = validate_input(value)
    return _finish_receipt(packet, evaluation_mode=HISTORICAL_INTEGRITY_ONLY)


def compile_current(value: Any) -> tuple[dict[str, Any], str]:
    """Compile a current owner-review artifact using process-owned UTC."""
    now = datetime.now(timezone.utc)
    packet = _normalized_with_as_of(value, now)
    return _finish_receipt(packet, evaluation_mode=CURRENT_PROCESS_UTC)


def _verify_exact(
    value: Any,
    receipt: Any,
    markdown: Any,
    *,
    expected_mode: str,
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise PacketVerificationError("receipt must be a JSON object")
    if not isinstance(markdown, str):
        raise PacketVerificationError("markdown must be text")
    if receipt.get("evaluation_mode") != expected_mode:
        raise PacketVerificationError(
            f"receipt evaluation_mode must be {expected_mode}"
        )

    if expected_mode == HISTORICAL_INTEGRITY_ONLY:
        packet = validate_input(value)
    else:
        raw_as_of = receipt.get("as_of")
        if not isinstance(raw_as_of, str):
            raise PacketVerificationError("current receipt as_of must be text")
        try:
            recorded = datetime.fromisoformat(raw_as_of)
        except ValueError as exc:
            raise PacketVerificationError("current receipt as_of is invalid") from exc
        if recorded.tzinfo is None or recorded.utcoffset() is None:
            raise PacketVerificationError("current receipt as_of must be timezone-aware")
        packet = _normalized_with_as_of(value, recorded)

    expected_receipt, expected_markdown = _finish_receipt(
        packet,
        evaluation_mode=expected_mode,
    )
    if canonical_json_bytes(receipt) != canonical_json_bytes(expected_receipt):
        raise PacketVerificationError("receipt differs from deterministic recompilation")
    if markdown.encode("utf-8") != expected_markdown.encode("utf-8"):
        raise PacketVerificationError("Markdown differs from deterministic recompilation")
    provided_digest = receipt.get("receipt_sha256")
    detached = dict(receipt)
    detached.pop("receipt_sha256", None)
    expected_digest = sha256_hex(canonical_json_bytes(detached))
    if provided_digest != expected_digest:
        raise PacketVerificationError("receipt_sha256 is invalid")
    return expected_receipt


def verify_packet(value: Any, receipt: Any, markdown: Any) -> bool:
    """Verify an explicit-time historical receipt exactly."""
    _verify_exact(
        value,
        receipt,
        markdown,
        expected_mode=HISTORICAL_INTEGRITY_ONLY,
    )
    return True


def _current_projection(receipt: dict[str, Any]) -> tuple[Any, ...]:
    gates = tuple(
        (row["id"], row["disposition"], row["blocking"])
        for row in receipt["gates"]
    )
    return (
        receipt["status"],
        receipt["submission_ready"],
        gates,
    )


def verify_current(value: Any, receipt: Any, markdown: Any) -> bool:
    """Verify exact bytes plus current process-time readiness semantics."""
    expected = _verify_exact(
        value,
        receipt,
        markdown,
        expected_mode=CURRENT_PROCESS_UTC,
    )
    recorded = datetime.fromisoformat(expected["as_of"])
    now = datetime.now(timezone.utc)
    recorded_utc = recorded.astimezone(timezone.utc)
    if recorded_utc - now > CURRENT_FUTURE_SKEW:
        raise PacketVerificationError("current receipt is dated in the future")
    if now - recorded_utc > CURRENT_RECEIPT_MAX_AGE:
        raise PacketVerificationError("current receipt is too old for current verification")

    fresh_packet = _normalized_with_as_of(value, now)
    fresh_receipt, _ = _finish_receipt(
        fresh_packet,
        evaluation_mode=CURRENT_PROCESS_UTC,
    )
    if _current_projection(fresh_receipt) != _current_projection(expected):
        raise PacketVerificationError(
            "current readiness changed since the receipt was compiled"
        )
    return True
