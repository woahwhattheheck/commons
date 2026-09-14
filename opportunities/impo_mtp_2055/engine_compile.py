"""Receipt compilation and exact verification for IMPO MTP 2055 readiness."""

from __future__ import annotations

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

def compile_packet(value: Any) -> tuple[dict[str, Any], str]:
    packet = validate_input(value)
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
    receipt: dict[str, Any] = {
        "schema_version": packet["schema_version"],
        "engine_version": ENGINE_VERSION,
        "input_sha256": input_sha,
        "as_of": packet["as_of"],
        "opportunity": packet["opportunity"],
        "source_checks": packet["source_checks"],
        "status": status,
        "submission_ready": status == "SUBMISSION_READY",
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
    receipt["receipt_sha256"] = sha256_hex(canonical_json_bytes(receipt))
    markdown = render_markdown(receipt)
    return receipt, markdown


def verify_packet(value: Any, receipt: Any, markdown: Any) -> bool:
    if not isinstance(receipt, dict):
        raise PacketVerificationError("receipt must be a JSON object")
    if not isinstance(markdown, str):
        raise PacketVerificationError("markdown must be text")
    expected_receipt, expected_markdown = compile_packet(value)
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
    return True
