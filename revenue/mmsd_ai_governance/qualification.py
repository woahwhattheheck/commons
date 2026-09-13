#!/usr/bin/env python3
"""Truth-bound qualification gate for the MMSD AI governance RFP.

This module deliberately cannot authorize a proposal submission. It compiles a deterministic
readiness receipt from owner-provided evidence and fail-closes when mandatory procurement
facts or company qualification evidence remain unknown.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "mmsd.ai-governance.qualification/v1"
READY = "READY_FOR_OWNER_PROPOSAL_REVIEW"
HOLD = "HOLD_QUALIFICATION_GATES"
NO_GO = "NO_GO_CONFIRMED_GATE_FAILURE"

ALLOWED = {"CONFIRMED", "UNKNOWN", "NOT_APPLICABLE", "FAILED"}
REQUIRED_GATES = (
    "official_pdf_obtained",
    "submission_items_verified",
    "evaluation_criteria_verified",
    "references_requirement_verified",
    "references_satisfied",
    "insurance_requirement_verified",
    "insurance_satisfied_or_bindable",
    "prime_team_rules_verified",
    "public_record_sanitization_complete",
    "technical_scope_supported",
    "delivery_capacity_supported",
    "price_authorized",
)
FAIL_HARD_GATES = {
    "references_satisfied",
    "insurance_satisfied_or_bindable",
    "technical_scope_supported",
    "delivery_capacity_supported",
}

class QualificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _plain_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualificationError(f"{field}: object required")
    return value


def _text(value: Any, field: str, *, max_len: int = 500) -> str:
    if not isinstance(value, str):
        raise QualificationError(f"{field}: text required")
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > max_len:
        raise QualificationError(f"{field}: invalid length")
    return normalized


def _digest(value: Any, field: str) -> str:
    text = _text(value, field, max_len=64)
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise QualificationError(f"{field}: lowercase sha256 required")
    return text


def _timestamp(value: Any, field: str) -> str:
    text = _text(value, field, max_len=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{field}: invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise QualificationError(f"{field}: timezone required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _evidence(entry: Any, field: str) -> dict[str, str]:
    item = _plain_dict(entry, field)
    if set(item) != {"status", "evidence_ref", "evidence_digest", "note"}:
        raise QualificationError(f"{field}: exact keys required")
    status = _text(item["status"], f"{field}.status", max_len=32)
    if status not in ALLOWED:
        raise QualificationError(f"{field}.status: invalid")
    evidence_ref = _text(item["evidence_ref"], f"{field}.evidence_ref", max_len=180)
    evidence_digest = _digest(item["evidence_digest"], f"{field}.evidence_digest")
    note = _text(item["note"], f"{field}.note", max_len=500)
    return {
        "status": status,
        "evidence_ref": evidence_ref,
        "evidence_digest": evidence_digest,
        "note": note,
    }


def compile_readiness(request: Any) -> dict[str, Any]:
    root = _plain_dict(request, "request")
    if set(root) != {"schema_version", "opportunity_id", "compiled_at", "gates"}:
        raise QualificationError("request: exact keys required")
    if root["schema_version"] != SCHEMA:
        raise QualificationError("schema_version: mismatch")
    if root["opportunity_id"] != "MMSD-AI-GOVERNANCE-RFP-20260913":
        raise QualificationError("opportunity_id: mismatch")
    compiled_at = _timestamp(root["compiled_at"], "compiled_at")
    gates_raw = _plain_dict(root["gates"], "gates")
    if set(gates_raw) != set(REQUIRED_GATES):
        missing = sorted(set(REQUIRED_GATES) - set(gates_raw))
        extra = sorted(set(gates_raw) - set(REQUIRED_GATES))
        raise QualificationError(f"gates: exact keys required missing={missing} extra={extra}")
    gates = {name: _evidence(gates_raw[name], f"gates.{name}") for name in REQUIRED_GATES}

    failed = sorted(name for name, gate in gates.items() if gate["status"] == "FAILED")
    unknown = sorted(name for name, gate in gates.items() if gate["status"] == "UNKNOWN")
    hard_failed = sorted(name for name in failed if name in FAIL_HARD_GATES)

    if hard_failed:
        status = NO_GO
        reasons = [f"HARD_GATE_FAILED:{name}" for name in hard_failed]
    elif failed or unknown:
        status = HOLD
        reasons = [*(f"FAILED:{name}" for name in failed), *(f"UNKNOWN:{name}" for name in unknown)]
    else:
        status = READY
        reasons = ["ALL_REQUIRED_GATES_RESOLVED"]

    normalized_request = {
        "schema_version": SCHEMA,
        "opportunity_id": root["opportunity_id"],
        "compiled_at": compiled_at,
        "gates": gates,
    }
    request_digest = sha256(normalized_request)
    receipt_core = {
        "schema_version": SCHEMA,
        "opportunity_id": root["opportunity_id"],
        "status": status,
        "reason_codes": reasons,
        "request_digest": request_digest,
        "compiled_at": compiled_at,
        "authorities": {
            "submit_proposal": False,
            "contact_buyer": False,
            "set_price": False,
            "sign_contract": False,
            "bind_insurance": False,
            "claim_reference": False,
            "claim_award": False,
            "recognize_revenue": False,
        },
    }
    return {"request": normalized_request, "receipt": {**receipt_core, "receipt_digest": sha256(receipt_core)}}


def verify_package(package: Any) -> dict[str, Any]:
    root = _plain_dict(package, "package")
    if set(root) != {"request", "receipt"}:
        raise QualificationError("package: exact keys required")
    rebuilt = compile_readiness(root["request"])
    if canonical_json(root["receipt"]) != canonical_json(rebuilt["receipt"]):
        raise QualificationError("receipt: mismatch")
    return {
        "valid": True,
        "status": root["receipt"]["status"],
        "request_digest": root["receipt"]["request_digest"],
        "receipt_digest": root["receipt"]["receipt_digest"],
    }


def load_json(path: str | Path) -> Any:
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise QualificationError("input: too large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QualificationError("input: invalid utf-8") from exc
    return json.loads(text)
