from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from revenue.streaming_rendition_release_gate.gate import HOLD, RELEASE_READY, SCHEMA as GATE_SCHEMA, validate_packets

SCHEMA = "streaming-rendition-qa-pilot/v1"
DIAGNOSTIC = "DIAGNOSTIC"
INTEGRATION = "INTEGRATION"
TIERS = {
    DIAGNOSTIC: {
        "fixed_price_usd": 2500,
        "scope": "metadata QA diagnostic and findings report",
    },
    INTEGRATION: {
        "fixed_price_usd": 7500,
        "scope": "diagnostic plus integration into the buyer's rendition handoff workflow",
    },
}

_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_INTAKE_KEYS = {"schema", "pilot_id", "customer_ref", "tier", "packets"}


class IntakeError(ValueError):
    pass


def _ref(value: Any, where: str) -> str:
    if not isinstance(value, str) or _REF_RE.fullmatch(value) is None:
        raise IntakeError(f"{where}: expected 1-128 chars from [A-Za-z0-9._:/-]")
    return value


def validate_intake(intake: Any) -> dict[str, Any]:
    if not isinstance(intake, dict):
        raise IntakeError("intake: expected object")
    keys = set(intake)
    if keys != _INTAKE_KEYS:
        missing = sorted(_INTAKE_KEYS - keys)
        extra = sorted(keys - _INTAKE_KEYS)
        raise IntakeError(f"intake: key mismatch missing={missing} extra={extra}")
    if intake["schema"] != SCHEMA:
        raise IntakeError("intake.schema: unsupported schema")
    _ref(intake["pilot_id"], "intake.pilot_id")
    _ref(intake["customer_ref"], "intake.customer_ref")
    tier = intake["tier"]
    if not isinstance(tier, str) or tier not in TIERS:
        raise IntakeError(f"intake.tier: expected one of {sorted(TIERS)}")
    packets = intake["packets"]
    if not isinstance(packets, list) or not packets:
        raise IntakeError("intake.packets: expected non-empty array")
    if len(packets) > 5000:
        raise IntakeError("intake.packets: maximum 5000 packets per pilot receipt")
    return intake


def _reason_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        reason = row.get("reason", "<missing>")
        counts[reason] = counts.get(reason, 0) + 1
    return {reason: counts[reason] for reason in sorted(counts)}


def compile_pilot(intake: Any) -> dict[str, Any]:
    data = validate_intake(intake)
    gate = validate_packets(data["packets"])
    rows = gate["results"]
    ready = sum(row.get("status") == RELEASE_READY for row in rows)
    hold = sum(row.get("status") == HOLD for row in rows)
    unknown = len(rows) - ready - hold
    if unknown:
        raise IntakeError(f"gate.results: {unknown} row(s) have unsupported status")

    tier = data["tier"]
    terms = TIERS[tier]
    decision = "PASS_TO_MEDIA_OPS" if hold == 0 else "REMEDIATE_METADATA"
    report = {
        "schema": SCHEMA,
        "pilot_id": data["pilot_id"],
        "customer_ref": data["customer_ref"],
        "tier": tier,
        "source_gate_schema": GATE_SCHEMA,
        "source_projection_sha256": gate["projection_sha256"],
        "decision": decision,
        "summary": {
            "total": len(rows),
            "release_ready": ready,
            "hold": hold,
        },
        "reason_counts": _reason_counts(rows),
        "findings": rows,
        "commercial": {
            "fixed_price_usd": terms["fixed_price_usd"],
            "scope": terms["scope"],
            "payment_expectation": "paid kickoff via seller-approved invoice or payment link",
        },
        "authority": (
            "QA evidence only. Media operations retain rights, content, release, scheduling, "
            "DRM-secret, transcoding, CDN, and publishing authority."
        ),
    }
    return report


def canonical_report_bytes(report: Any) -> bytes:
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise IntakeError("report: expected compiled streaming rendition QA pilot report")
    return (json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def compile_receipt(intake: Any) -> dict[str, Any]:
    report = compile_pilot(intake)
    report_bytes = canonical_report_bytes(report)
    return {
        "report": report,
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "report_bytes": report_bytes,
    }


__all__ = [
    "DIAGNOSTIC",
    "INTEGRATION",
    "IntakeError",
    "SCHEMA",
    "TIERS",
    "canonical_report_bytes",
    "compile_pilot",
    "compile_receipt",
    "validate_intake",
]
