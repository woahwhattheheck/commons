#!/usr/bin/env python3
"""Fail-closed qualification engine for Jersey procurement DN827803."""
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

NOTICE_ID = "DN827803"
SCHEMA_VERSION = 1
MAX_SOURCE_AGE_DAYS = 30
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CAPABILITY_STATES = {"PROVEN", "PARTNER_CURABLE", "MISSING", "UNKNOWN", "NOT_APPLICABLE"}
AUTHORITY_FLAGS = {
    "portal_registration",
    "buyer_contact",
    "clarification_question",
    "tender_submission",
    "pricing_commitment",
    "staffing_commitment",
    "clinical_certification_claim",
    "contract_acceptance",
    "spend",
    "revenue_claim",
}
ROUTES: dict[str, tuple[str, ...]] = {
    "PRIME_CDR": (
        "openehr_platform_product",
        "clinical_cdr_delivery",
        "real_time_clinical_data",
        "healthcare_interoperability",
        "clinical_identity_terminology",
        "security_privacy",
        "clinical_safety",
        "migration_at_scale",
        "service_operations",
        "commercial_delivery_capacity",
    ),
    "TEAMING_INTEROPERABILITY_SPECIALIST": (
        "healthcare_interoperability",
        "data_migration_reconciliation",
        "interface_conformance",
        "replay_idempotency",
        "observability_lineage",
        "security_data_governance",
    ),
    "TEAMING_ACCEPTANCE_EVIDENCE": (
        "interface_conformance",
        "data_migration_reconciliation",
        "observability_lineage",
        "replay_idempotency",
        "human_release_controls",
    ),
}
TEAMING_ROUTES = {"TEAMING_INTEROPERABILITY_SPECIALIST", "TEAMING_ACCEPTANCE_EVIDENCE"}


class QualificationError(ValueError):
    pass


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


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QualificationError(f"{key}:MUST_BE_STRING")
    return value


def _require_bool(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key)
    if type(value) is not bool:
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
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label}:INVALID_DATETIME") from exc
    if dt.tzinfo is None:
        raise QualificationError(f"{label}:TIMEZONE_REQUIRED")
    return dt


def _validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_SHA256")
    return value


def validate_source(source: dict[str, Any], *, tender_pack_bytes: bytes | None) -> dict[str, Any]:
    if _require_int(source, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("source.schema_version:UNSUPPORTED")
    if _require_str(source, "notice_id") != NOTICE_ID:
        raise QualificationError("source.notice_id:MISMATCH")
    checked_at = _parse_dt(_require_str(source, "checked_at"), "source.checked_at")
    _parse_dt(_require_str(source, "response_deadline"), "source.response_deadline")
    pack = source.get("tender_pack")
    if not isinstance(pack, dict):
        raise QualificationError("source.tender_pack:MUST_BE_OBJECT")
    acquired = _require_bool(pack, "acquired")
    reviewed = _require_bool(pack, "reviewed")
    declared_sha = pack.get("sha256")
    state = _require_str(pack, "state")
    actual_sha = None
    if not acquired:
        if reviewed:
            raise QualificationError("source.tender_pack:REVIEWED_WITHOUT_ACQUISITION")
        if declared_sha is not None:
            raise QualificationError("source.tender_pack:SHA_WITHOUT_ACQUISITION")
        if state != "TENDER_PACK_NOT_ACQUIRED":
            raise QualificationError("source.tender_pack:STATE_MISMATCH")
        if tender_pack_bytes is not None:
            raise QualificationError("source.tender_pack:BYTES_PRESENT_BUT_NOT_ACQUIRED")
    else:
        declared = _validate_sha(declared_sha, "source.tender_pack.sha256")
        if state not in {"TENDER_PACK_ACQUIRED_UNREVIEWED", "TENDER_PACK_ACQUIRED_REVIEWED"}:
            raise QualificationError("source.tender_pack:STATE_MISMATCH")
        if reviewed != (state == "TENDER_PACK_ACQUIRED_REVIEWED"):
            raise QualificationError("source.tender_pack:REVIEW_STATE_MISMATCH")
        if tender_pack_bytes is not None:
            actual_sha = sha256_bytes(tender_pack_bytes)
            if actual_sha != declared:
                raise QualificationError("TENDER_PACK_DIGEST_MISMATCH")
    return {
        "checked_at": checked_at,
        "pack_acquired": acquired,
        "pack_reviewed": reviewed,
        "pack_declared_sha256": declared_sha,
        "pack_actual_sha256": actual_sha,
    }


def validate_manifest(manifest: dict[str, Any], source_raw: bytes) -> dict[str, Any]:
    if _require_int(manifest, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("manifest.schema_version:UNSUPPORTED")
    if _require_str(manifest, "notice_id") != NOTICE_ID:
        raise QualificationError("manifest.notice_id:MISMATCH")
    expected = _validate_sha(manifest.get("source_ledger_sha256"), "manifest.source_ledger_sha256")
    actual = sha256_bytes(source_raw)
    if expected != actual:
        raise QualificationError("SOURCE_LEDGER_DIGEST_MISMATCH")
    evaluated_at = _parse_dt(_require_str(manifest, "evaluated_at"), "manifest.evaluated_at")
    route = _require_str(manifest, "route")
    if route not in ROUTES:
        raise QualificationError("manifest.route:UNSUPPORTED")
    partner_prime_confirmed = _require_bool(manifest, "partner_prime_confirmed")
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise QualificationError("manifest.authority:MUST_BE_OBJECT")
    missing = AUTHORITY_FLAGS - authority.keys()
    extra = authority.keys() - AUTHORITY_FLAGS
    if missing:
        raise QualificationError("manifest.authority:MISSING_FLAGS:" + ",".join(sorted(missing)))
    if extra:
        raise QualificationError("manifest.authority:UNKNOWN_FLAGS:" + ",".join(sorted(extra)))
    escalated = [key for key in sorted(AUTHORITY_FLAGS) if _require_bool(authority, key)]
    if escalated:
        raise QualificationError("AUTHORITY_ESCALATION_FORBIDDEN:" + ",".join(escalated))
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        raise QualificationError("manifest.capabilities:MUST_BE_OBJECT")
    normalized: dict[str, dict[str, Any]] = {}
    for name, record in capabilities.items():
        if not isinstance(name, str) or not name or not isinstance(record, dict):
            raise QualificationError("manifest.capabilities:INVALID_RECORD")
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
        "evaluated_at": evaluated_at,
        "route": route,
        "partner_prime_confirmed": partner_prime_confirmed,
        "capabilities": normalized,
        "source_sha256": actual,
    }


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return (json.dumps(self.payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def evaluate(manifest: dict[str, Any], source: dict[str, Any], source_raw: bytes, *, tender_pack_bytes: bytes | None = None) -> Evaluation:
    s = validate_source(source, tender_pack_bytes=tender_pack_bytes)
    m = validate_manifest(manifest, source_raw)
    age_seconds = (m["evaluated_at"] - s["checked_at"]).total_seconds()
    if age_seconds < 0:
        raise QualificationError("manifest.evaluated_at:BEFORE_SOURCE_CHECK")
    age_days = age_seconds // 86400
    missing_caps: list[dict[str, str]] = []
    for gate in ROUTES[m["route"]]:
        record = m["capabilities"].get(gate)
        if record is None:
            missing_caps.append({"gate": gate, "status": "UNDECLARED"})
        elif record["status"] != "PROVEN":
            missing_caps.append({"gate": gate, "status": record["status"]})
    if age_days > MAX_SOURCE_AGE_DAYS:
        state = "HOLD_SOURCE_STALE"
    elif not s["pack_acquired"]:
        state = "HOLD_TENDER_PACK_REQUIRED"
    elif tender_pack_bytes is None:
        state = "HOLD_TENDER_PACK_FILE_REQUIRED"
    elif not s["pack_reviewed"]:
        state = "HOLD_TENDER_PACK_REVIEW"
    elif missing_caps:
        state = "HOLD_EVIDENCE_GAPS"
    elif m["route"] in TEAMING_ROUTES and not m["partner_prime_confirmed"]:
        state = "HOLD_PARTNER_REQUIRED"
    else:
        state = "READY_FOR_OWNER_TENDER_REVIEW"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "route": m["route"],
        "state": state,
        "source_age_days": int(age_days),
        "source_ledger_sha256": m["source_sha256"],
        "tender_pack_acquired": s["pack_acquired"],
        "tender_pack_reviewed": s["pack_reviewed"],
        "tender_pack_sha256": s["pack_declared_sha256"],
        "partner_prime_confirmed": m["partner_prime_confirmed"],
        "missing_required_capabilities": missing_caps,
        "authority": "INTERNAL_QUALIFICATION_ONLY",
        "tender_submission_authorized": False,
        "evaluated_at": m["evaluated_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return Evaluation(state, 0 if state == "READY_FOR_OWNER_TENDER_REVIEW" else 3, payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--source-ledger", type=Path, default=Path(__file__).with_name("sources.json"))
    p.add_argument("--tender-pack", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        source_raw = args.source_ledger.read_bytes()
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_bytes(args.manifest.read_bytes(), "manifest")
        pack_bytes = args.tender_pack.read_bytes() if args.tender_pack else None
        result = evaluate(manifest, source, source_raw, tender_pack_bytes=pack_bytes)
    except (OSError, QualificationError) as exc:
        payload = {"state": "INVALID_INPUT", "error": str(exc), "tender_submission_authorized": False}
        sys.stderr.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return 2
    encoded = result.bytes()
    if args.output:
        args.output.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
