#!/usr/bin/env python3
"""Fail-closed qualification engine for FTS 080252-2026.

This tool does not submit anything. It only evaluates whether an internal
pre-market-engagement packet is ready for owner review. Buyer questionnaire
bytes must be supplied and digest-bound before any READY state is possible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

NOTICE_ID = "080252-2026"
OCID = "ocds-h6vhtk-06ea51"
ATAMIS_REF = "C467704"
SCHEMA_VERSION = 1
MAX_SOURCE_AGE_DAYS = 30
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CAPABILITY_STATES = {"PROVEN", "PARTNER_CURABLE", "MISSING", "UNKNOWN", "NOT_APPLICABLE"}
FORBIDDEN_AUTHORITY_FLAGS = {
    "buyer_contact",
    "portal_registration",
    "questionnaire_submission",
    "pricing_commitment",
    "staffing_commitment",
    "clinical_certification_claim",
    "contract_acceptance",
    "spend",
    "revenue_claim",
}

ROUTES: dict[str, tuple[str, ...]] = {
    "PRIME_LIMS": (
        "clinical_pathology_lims_product",
        "nhs_pathology_scale",
        "clinical_safety_case",
        "regulatory_pathology_compliance",
        "epr_national_system_integrations",
        "migration_at_scale",
        "implementation_training_support",
        "commercial_delivery_capacity",
    ),
    "TEAMING_INTEGRATION_SPECIALIST": (
        "integration_engineering",
        "migration_reconciliation",
        "interface_test_harness",
        "security_data_governance",
        "deterministic_acceptance",
    ),
    "TEAMING_VALIDATION_EVIDENCE": (
        "deterministic_acceptance",
        "migration_reconciliation",
        "data_lineage_evidence",
        "interface_test_harness",
        "human_release_controls",
    ),
}
TEAMING_ROUTES = {"TEAMING_INTEGRATION_SPECIALIST", "TEAMING_VALIDATION_EVIDENCE"}


class QualificationError(ValueError):
    """Invalid or unsafe qualification input."""


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def load_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except UnicodeDecodeError as exc:
        raise QualificationError(f"{label}:NOT_UTF8") from exc
    except json.JSONDecodeError as exc:
        raise QualificationError(f"{label}:INVALID_JSON:{exc.msg}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{label}:ROOT_MUST_BE_OBJECT")
    return value


def load_json_path(path: Path, label: str) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes(), label)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_str(obj: dict[str, Any], key: str, *, nonempty: bool = True) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise QualificationError(f"{key}:MUST_BE_STRING")
    return value


def _require_bool(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key)
    if type(value) is not bool:  # bool is an int subclass: exact type is deliberate.
        raise QualificationError(f"{key}:MUST_BE_BOOL")
    return value


def _require_int(obj: dict[str, Any], key: str, *, minimum: int | None = None) -> int:
    value = obj.get(key)
    if type(value) is not int:
        raise QualificationError(f"{key}:MUST_BE_INT_NOT_BOOL")
    if minimum is not None and value < minimum:
        raise QualificationError(f"{key}:BELOW_MINIMUM")
    return value


def _parse_dt(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label}:INVALID_DATETIME") from exc
    if parsed.tzinfo is None:
        raise QualificationError(f"{label}:TIMEZONE_REQUIRED")
    return parsed


def _validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_SHA256")
    return value


def validate_source_ledger(source: dict[str, Any], *, questionnaire_bytes: bytes | None) -> dict[str, Any]:
    if _require_int(source, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("source.schema_version:UNSUPPORTED")
    if _require_str(source, "notice_id") != NOTICE_ID:
        raise QualificationError("source.notice_id:MISMATCH")
    if _require_str(source, "ocid") != OCID:
        raise QualificationError("source.ocid:MISMATCH")
    if _require_str(source, "atamis_contract_reference") != ATAMIS_REF:
        raise QualificationError("source.atamis_contract_reference:MISMATCH")
    _require_int(source, "estimated_value_gbp_ex_vat", minimum=1)
    checked_at = _parse_dt(_require_str(source, "checked_at"), "source.checked_at")
    deadline = _parse_dt(_require_str(source, "response_deadline"), "source.response_deadline")
    questionnaire = source.get("questionnaire")
    if not isinstance(questionnaire, dict):
        raise QualificationError("source.questionnaire:MUST_BE_OBJECT")
    acquired = _require_bool(questionnaire, "acquired")
    reviewed = _require_bool(questionnaire, "reviewed")
    declared_sha = questionnaire.get("sha256")
    state = _require_str(questionnaire, "state")
    actual_sha: str | None = None
    if not acquired:
        if reviewed:
            raise QualificationError("source.questionnaire:REVIEWED_WITHOUT_ACQUISITION")
        if declared_sha is not None:
            raise QualificationError("source.questionnaire:SHA_WITHOUT_ACQUISITION")
        if state != "QUESTIONNAIRE_NOT_ACQUIRED":
            raise QualificationError("source.questionnaire:STATE_MISMATCH")
        if questionnaire_bytes is not None:
            raise QualificationError("source.questionnaire:BYTES_PRESENT_BUT_NOT_ACQUIRED")
    else:
        declared = _validate_sha(declared_sha, "source.questionnaire.sha256")
        if state not in {"QUESTIONNAIRE_ACQUIRED_UNREVIEWED", "QUESTIONNAIRE_ACQUIRED_REVIEWED"}:
            raise QualificationError("source.questionnaire:STATE_MISMATCH")
        if reviewed and state != "QUESTIONNAIRE_ACQUIRED_REVIEWED":
            raise QualificationError("source.questionnaire:REVIEW_STATE_MISMATCH")
        if not reviewed and state != "QUESTIONNAIRE_ACQUIRED_UNREVIEWED":
            raise QualificationError("source.questionnaire:REVIEW_STATE_MISMATCH")
        if questionnaire_bytes is not None:
            actual_sha = sha256_bytes(questionnaire_bytes)
            if actual_sha != declared:
                raise QualificationError("QUESTIONNAIRE_DIGEST_MISMATCH")
    return {
        "checked_at": checked_at,
        "deadline": deadline,
        "questionnaire_acquired": acquired,
        "questionnaire_reviewed": reviewed,
        "questionnaire_declared_sha256": declared_sha,
        "questionnaire_actual_sha256": actual_sha,
    }


def validate_manifest(manifest: dict[str, Any], source_raw: bytes) -> dict[str, Any]:
    if _require_int(manifest, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("manifest.schema_version:UNSUPPORTED")
    if _require_str(manifest, "notice_id") != NOTICE_ID:
        raise QualificationError("manifest.notice_id:MISMATCH")
    expected_source_sha = _validate_sha(manifest.get("source_ledger_sha256"), "manifest.source_ledger_sha256")
    actual_source_sha = sha256_bytes(source_raw)
    if actual_source_sha != expected_source_sha:
        raise QualificationError("SOURCE_LEDGER_DIGEST_MISMATCH")
    route = _require_str(manifest, "route")
    if route not in ROUTES:
        raise QualificationError("manifest.route:UNSUPPORTED")
    evaluated_at = _parse_dt(_require_str(manifest, "evaluated_at"), "manifest.evaluated_at")
    partner_prime_confirmed = _require_bool(manifest, "partner_prime_confirmed")

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise QualificationError("manifest.authority:MUST_BE_OBJECT")
    missing_flags = FORBIDDEN_AUTHORITY_FLAGS - authority.keys()
    if missing_flags:
        raise QualificationError("manifest.authority:MISSING_FLAGS:" + ",".join(sorted(missing_flags)))
    unexpected = authority.keys() - FORBIDDEN_AUTHORITY_FLAGS
    if unexpected:
        raise QualificationError("manifest.authority:UNKNOWN_FLAGS:" + ",".join(sorted(unexpected)))
    escalated = [name for name in sorted(FORBIDDEN_AUTHORITY_FLAGS) if _require_bool(authority, name)]
    if escalated:
        raise QualificationError("AUTHORITY_ESCALATION_FORBIDDEN:" + ",".join(escalated))

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        raise QualificationError("manifest.capabilities:MUST_BE_OBJECT")
    normalized: dict[str, dict[str, Any]] = {}
    for name, record in capabilities.items():
        if not isinstance(name, str) or not name:
            raise QualificationError("manifest.capabilities:INVALID_NAME")
        if not isinstance(record, dict):
            raise QualificationError(f"capability.{name}:MUST_BE_OBJECT")
        status = _require_str(record, "status")
        if status not in CAPABILITY_STATES:
            raise QualificationError(f"capability.{name}:INVALID_STATUS")
        refs = record.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise QualificationError(f"capability.{name}:INVALID_EVIDENCE_REFS")
        if status == "PROVEN" and not refs:
            raise QualificationError(f"capability.{name}:PROVEN_REQUIRES_EVIDENCE")
        normalized[name] = {"status": status, "evidence_refs": list(refs)}

    return {
        "route": route,
        "evaluated_at": evaluated_at,
        "partner_prime_confirmed": partner_prime_confirmed,
        "capabilities": normalized,
        "source_sha256": actual_source_sha,
    }


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return (json.dumps(self.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def evaluate(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    questionnaire_bytes: bytes | None = None,
) -> Evaluation:
    source_state = validate_source_ledger(source, questionnaire_bytes=questionnaire_bytes)
    manifest_state = validate_manifest(manifest, source_raw)

    age_seconds = (manifest_state["evaluated_at"] - source_state["checked_at"]).total_seconds()
    if age_seconds < 0:
        raise QualificationError("manifest.evaluated_at:BEFORE_SOURCE_CHECK")
    source_age_days = age_seconds // 86400

    route = manifest_state["route"]
    capabilities = manifest_state["capabilities"]
    required = ROUTES[route]
    missing_records: list[dict[str, str]] = []
    for gate in required:
        record = capabilities.get(gate)
        if record is None:
            missing_records.append({"gate": gate, "status": "UNDECLARED"})
        elif record["status"] != "PROVEN":
            missing_records.append({"gate": gate, "status": record["status"]})

    if source_age_days > MAX_SOURCE_AGE_DAYS:
        state = "HOLD_SOURCE_STALE"
    elif not source_state["questionnaire_acquired"]:
        state = "HOLD_QUESTIONNAIRE_REQUIRED"
    elif questionnaire_bytes is None:
        state = "HOLD_QUESTIONNAIRE_FILE_REQUIRED"
    elif not source_state["questionnaire_reviewed"]:
        state = "HOLD_QUESTIONNAIRE_REVIEW"
    elif missing_records:
        state = "HOLD_EVIDENCE_GAPS"
    elif route in TEAMING_ROUTES and not manifest_state["partner_prime_confirmed"]:
        state = "HOLD_PARTNER_REQUIRED"
    else:
        state = "READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "ocid": OCID,
        "atamis_contract_reference": ATAMIS_REF,
        "route": route,
        "state": state,
        "source_age_days": int(source_age_days),
        "source_ledger_sha256": manifest_state["source_sha256"],
        "questionnaire_acquired": source_state["questionnaire_acquired"],
        "questionnaire_reviewed": source_state["questionnaire_reviewed"],
        "questionnaire_sha256": source_state["questionnaire_declared_sha256"],
        "partner_prime_confirmed": manifest_state["partner_prime_confirmed"],
        "missing_required_capabilities": missing_records,
        "authority": "INTERNAL_QUALIFICATION_ONLY",
        "buyer_submission_authorized": False,
        "evaluated_at": manifest_state["evaluated_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return Evaluation(state=state, exit_code=0 if state == "READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW" else 3, payload=payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source-ledger", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument("--questionnaire", type=Path, default=None, help="buyer questionnaire bytes; required for READY")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        source_raw = args.source_ledger.read_bytes()
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_path(args.manifest, "manifest")
        questionnaire_bytes = args.questionnaire.read_bytes() if args.questionnaire else None
        result = evaluate(manifest, source, source_raw, questionnaire_bytes=questionnaire_bytes)
    except (OSError, QualificationError) as exc:
        payload = {"state": "INVALID_INPUT", "error": str(exc), "buyer_submission_authorized": False}
        sys.stderr.buffer.write((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        return 2

    encoded = result.bytes()
    if args.output:
        args.output.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
