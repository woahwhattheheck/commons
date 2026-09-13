#!/usr/bin/env python3
"""Fail-closed qualification engine for Jersey procurement DN827803.

Current-work authority is split across:
- the caller packet (route/status assertions);
- exact source/tender-pack bytes; and
- an independently retained v2 trusted qualification commitment plus its
  separately retained canonical SHA-256.

The evaluator never authorizes external tender actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

NOTICE_ID = "DN827803"
SCHEMA_VERSION = 1
TRUST_SCHEMA_VERSION = 2
TRUST_CONTRACT = "jersey-dn827803-trusted-qualification/v2"
MAX_SOURCE_AGE_SECONDS = 30 * 24 * 60 * 60
MAX_ADDENDA_AGE_SECONDS = 24 * 60 * 60
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_TENDER_PACK_BYTES = 256 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
CAPABILITY_STATES = {"PROVEN", "PARTNER_CURABLE", "MISSING", "UNKNOWN", "NOT_APPLICABLE"}
EVIDENCE_SUBJECTS = {"PRIME", "PARTNER"}
CURES = {"NONE", "PARTNER"}
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
TRUST_ROOT_KEYS = {
    "contract",
    "schema_version",
    "notice_id",
    "source_ledger_sha256",
    "tender_pack_sha256",
    "extracted_at",
    "addenda_checked_through",
    "response_deadline",
    "deadline_source_id",
    "complete",
    "buyer_sources",
    "buyer_source_set_sha256",
    "requirements",
    "requirement_set_sha256",
    "approved_evidence",
    "evidence_set_sha256",
}
BUYER_SOURCE_KEYS = {"source_id", "kind", "sha256"}
REQUIREMENT_KEYS = {
    "requirement_id",
    "claim_id",
    "mandatory",
    "routes",
    "cure",
    "buyer_source_id",
    "buyer_source_sha256",
    "description_sha256",
}
APPROVED_EVIDENCE_KEYS = {
    "evidence_id",
    "claim_id",
    "subject",
    "source_sha256",
    "source_ref",
    "statement_sha256",
}


class QualificationError(ValueError):
    pass


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> Any:
    raise QualificationError(f"NONFINITE_JSON_NUMBER:{value}")


def load_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise QualificationError(f"{label}:NOT_UTF8") from exc
    except json.JSONDecodeError as exc:
        raise QualificationError(f"{label}:INVALID_JSON:{exc.msg}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{label}:ROOT_MUST_BE_OBJECT")
    _reject_floats(value, label)
    return value


def _reject_floats(value: Any, label: str) -> None:
    if isinstance(value, float):
        raise QualificationError(f"{label}:FLOAT_NOT_ALLOWED")
    if isinstance(value, list):
        for item in value:
            _reject_floats(item, label)
    elif isinstance(value, dict):
        for item in value.values():
            _reject_floats(item, label)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_exact_keys(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(obj))
    extra = sorted(set(obj) - expected)
    if missing or extra:
        raise QualificationError(f"{label}:SCHEMA_MISMATCH:missing={missing}:extra={extra}")


def _require_str(obj: Mapping[str, Any], key: str, *, label: str | None = None, max_len: int = 1024) -> str:
    value = obj.get(key)
    name = label or key
    if not isinstance(value, str) or not value.strip() or len(value) > max_len or "\x00" in value:
        raise QualificationError(f"{name}:MUST_BE_STRING")
    return value


def _require_ident(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENT_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_ID")
    return value


def _require_bool(obj: Mapping[str, Any], key: str, *, label: str | None = None) -> bool:
    value = obj.get(key)
    name = label or key
    if type(value) is not bool:
        raise QualificationError(f"{name}:MUST_BE_BOOL")
    return value


def _require_int(obj: Mapping[str, Any], key: str, *, label: str | None = None, minimum: int | None = None) -> int:
    value = obj.get(key)
    name = label or key
    if type(value) is not int:
        raise QualificationError(f"{name}:MUST_BE_INT_NOT_BOOL")
    if minimum is not None and value < minimum:
        raise QualificationError(f"{name}:BELOW_MINIMUM")
    return value


def _parse_dt(value: str, label: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label}:INVALID_DATETIME") from exc
    if dt.tzinfo is None:
        raise QualificationError(f"{label}:TIMEZONE_REQUIRED")
    return dt.astimezone(timezone.utc)


def _trusted_dt(value: str, label: str) -> datetime:
    dt = _parse_dt(value, label)
    if not value.endswith("Z"):
        raise QualificationError(f"{label}:UTC_Z_REQUIRED")
    return dt


def _validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_SHA256")
    return value


def _read_plain_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    else:
        raise QualificationError(f"{label}:NOFOLLOW_UNAVAILABLE")
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise QualificationError(f"{label}:OPEN_FAILED:{exc.strerror or exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise QualificationError(f"{label}:NOT_REGULAR_FILE")
        if info.st_size > max_bytes:
            raise QualificationError(f"{label}:TOO_LARGE")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raise QualificationError(f"{label}:TOO_LARGE")
        return raw
    finally:
        os.close(fd)


def validate_source(
    source: dict[str, Any],
    *,
    tender_pack_bytes: bytes | None,
    trusted_as_of: str,
) -> dict[str, Any]:
    if _require_int(source, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("source.schema_version:UNSUPPORTED")
    if _require_str(source, "notice_id") != NOTICE_ID:
        raise QualificationError("source.notice_id:MISMATCH")
    now = _trusted_dt(trusted_as_of, "trusted_as_of")
    checked_at = _parse_dt(_require_str(source, "checked_at"), "source.checked_at")
    deadline = _parse_dt(_require_str(source, "response_deadline"), "source.response_deadline")
    if checked_at > now:
        raise QualificationError("source.checked_at:AFTER_TRUSTED_TIME")
    pack = source.get("tender_pack")
    if not isinstance(pack, dict):
        raise QualificationError("source.tender_pack:MUST_BE_OBJECT")
    acquired = _require_bool(pack, "acquired", label="source.tender_pack.acquired")
    reviewed = _require_bool(pack, "reviewed", label="source.tender_pack.reviewed")
    declared_sha = pack.get("sha256")
    state = _require_str(pack, "state", label="source.tender_pack.state")
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
        "trusted_now": now,
        "checked_at": checked_at,
        "response_deadline": deadline,
        "pack_acquired": acquired,
        "pack_reviewed": reviewed,
        "pack_declared_sha256": declared_sha,
        "pack_actual_sha256": actual_sha,
    }


def validate_manifest(
    manifest: dict[str, Any],
    source_raw: bytes,
    *,
    trusted_as_of: str,
) -> dict[str, Any]:
    if _require_int(manifest, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("manifest.schema_version:UNSUPPORTED")
    if _require_str(manifest, "notice_id") != NOTICE_ID:
        raise QualificationError("manifest.notice_id:MISMATCH")
    expected = _validate_sha(manifest.get("source_ledger_sha256"), "manifest.source_ledger_sha256")
    actual = sha256_bytes(source_raw)
    if expected != actual:
        raise QualificationError("SOURCE_LEDGER_DIGEST_MISMATCH")
    trusted_now = _trusted_dt(trusted_as_of, "trusted_as_of")
    evaluated_at = _parse_dt(_require_str(manifest, "evaluated_at"), "manifest.evaluated_at")
    if evaluated_at > trusted_now:
        raise QualificationError("manifest.evaluated_at:AFTER_TRUSTED_TIME")
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
        if not isinstance(name, str) or not IDENT_RE.fullmatch(name) or not isinstance(record, dict):
            raise QualificationError("manifest.capabilities:INVALID_RECORD")
        _require_exact_keys(record, {"status", "evidence_refs"}, f"capability.{name}")
        status = _require_str(record, "status", label=f"capability.{name}.status")
        if status not in CAPABILITY_STATES:
            raise QualificationError(f"capability.{name}:INVALID_STATUS")
        refs = record.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not IDENT_RE.fullmatch(ref) for ref in refs):
            raise QualificationError(f"capability.{name}:INVALID_EVIDENCE_REFS")
        if len(refs) != len(set(refs)):
            raise QualificationError(f"capability.{name}:DUPLICATE_EVIDENCE_REF")
        if status == "PROVEN" and not refs:
            raise QualificationError(f"capability.{name}:PROVEN_REQUIRES_EVIDENCE")
        if status != "PROVEN" and refs:
            raise QualificationError(f"capability.{name}:NONPROVEN_CANNOT_CARRY_EVIDENCE")
        normalized[name] = {"status": status, "evidence_refs": sorted(refs)}
    return {
        "evaluated_at": evaluated_at,
        "route": route,
        "partner_prime_confirmed": partner_prime_confirmed,
        "capabilities": normalized,
        "source_sha256": actual,
    }


def _normalize_buyer_source(raw: Any, index: int) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise QualificationError(f"trusted.buyer_sources[{index}]:MUST_BE_OBJECT")
    _require_exact_keys(raw, BUYER_SOURCE_KEYS, f"trusted.buyer_sources[{index}]")
    return {
        "source_id": _require_ident(raw["source_id"], f"trusted.buyer_sources[{index}].source_id"),
        "kind": _require_ident(raw["kind"], f"trusted.buyer_sources[{index}].kind"),
        "sha256": _validate_sha(raw["sha256"], f"trusted.buyer_sources[{index}].sha256"),
    }


def _normalize_requirement(raw: Any, index: int) -> dict[str, Any]:
    label = f"trusted.requirements[{index}]"
    if not isinstance(raw, dict):
        raise QualificationError(f"{label}:MUST_BE_OBJECT")
    _require_exact_keys(raw, REQUIREMENT_KEYS, label)
    routes = raw["routes"]
    if not isinstance(routes, list) or not routes:
        raise QualificationError(f"{label}.routes:MUST_BE_NONEMPTY_LIST")
    normalized_routes: list[str] = []
    for route in routes:
        if route != "ALL" and route not in ROUTES:
            raise QualificationError(f"{label}.routes:UNSUPPORTED")
        normalized_routes.append(route)
    if len(normalized_routes) != len(set(normalized_routes)):
        raise QualificationError(f"{label}.routes:DUPLICATE")
    cure = _require_str(raw, "cure", label=f"{label}.cure")
    if cure not in CURES:
        raise QualificationError(f"{label}.cure:UNSUPPORTED")
    return {
        "requirement_id": _require_ident(raw["requirement_id"], f"{label}.requirement_id"),
        "claim_id": _require_ident(raw["claim_id"], f"{label}.claim_id"),
        "mandatory": _require_bool(raw, "mandatory", label=f"{label}.mandatory"),
        "routes": sorted(normalized_routes),
        "cure": cure,
        "buyer_source_id": _require_ident(raw["buyer_source_id"], f"{label}.buyer_source_id"),
        "buyer_source_sha256": _validate_sha(raw["buyer_source_sha256"], f"{label}.buyer_source_sha256"),
        "description_sha256": _validate_sha(raw["description_sha256"], f"{label}.description_sha256"),
    }


def _normalize_approved_evidence(raw: Any, index: int) -> dict[str, str]:
    label = f"trusted.approved_evidence[{index}]"
    if not isinstance(raw, dict):
        raise QualificationError(f"{label}:MUST_BE_OBJECT")
    _require_exact_keys(raw, APPROVED_EVIDENCE_KEYS, label)
    subject = _require_str(raw, "subject", label=f"{label}.subject")
    if subject not in EVIDENCE_SUBJECTS:
        raise QualificationError(f"{label}.subject:UNSUPPORTED")
    source_ref = _require_str(raw, "source_ref", label=f"{label}.source_ref", max_len=2048)
    if not source_ref.startswith("https://"):
        raise QualificationError(f"{label}.source_ref:HTTPS_REQUIRED")
    return {
        "evidence_id": _require_ident(raw["evidence_id"], f"{label}.evidence_id"),
        "claim_id": _require_ident(raw["claim_id"], f"{label}.claim_id"),
        "subject": subject,
        "source_sha256": _validate_sha(raw["source_sha256"], f"{label}.source_sha256"),
        "source_ref": source_ref,
        "statement_sha256": _validate_sha(raw["statement_sha256"], f"{label}.statement_sha256"),
    }


def normalize_trusted_qualification(
    raw: Any,
    *,
    trusted_as_of: str,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QualificationError("trusted_qualification:MUST_BE_OBJECT")
    _require_exact_keys(raw, TRUST_ROOT_KEYS, "trusted_qualification")
    if _require_str(raw, "contract", label="trusted.contract") != TRUST_CONTRACT:
        raise QualificationError("trusted.contract:UNSUPPORTED")
    if _require_int(raw, "schema_version", label="trusted.schema_version", minimum=1) != TRUST_SCHEMA_VERSION:
        raise QualificationError("trusted.schema_version:UNSUPPORTED")
    if _require_str(raw, "notice_id", label="trusted.notice_id") != NOTICE_ID:
        raise QualificationError("trusted.notice_id:MISMATCH")
    now = _trusted_dt(trusted_as_of, "trusted_as_of")
    extracted_at = _parse_dt(_require_str(raw, "extracted_at", label="trusted.extracted_at"), "trusted.extracted_at")
    addenda_checked = _parse_dt(
        _require_str(raw, "addenda_checked_through", label="trusted.addenda_checked_through"),
        "trusted.addenda_checked_through",
    )
    deadline = _parse_dt(_require_str(raw, "response_deadline", label="trusted.response_deadline"), "trusted.response_deadline")
    if extracted_at > addenda_checked:
        raise QualificationError("trusted.extracted_at:AFTER_ADDENDA_CHECK")
    if addenda_checked > now:
        raise QualificationError("trusted.addenda_checked_through:AFTER_TRUSTED_TIME")

    buyer_sources_raw = raw["buyer_sources"]
    requirements_raw = raw["requirements"]
    evidence_raw = raw["approved_evidence"]
    if not isinstance(buyer_sources_raw, list) or not buyer_sources_raw:
        raise QualificationError("trusted.buyer_sources:MUST_BE_NONEMPTY_LIST")
    if not isinstance(requirements_raw, list) or not requirements_raw:
        raise QualificationError("trusted.requirements:MUST_BE_NONEMPTY_LIST")
    if not isinstance(evidence_raw, list):
        raise QualificationError("trusted.approved_evidence:MUST_BE_LIST")

    buyer_sources = [_normalize_buyer_source(item, i) for i, item in enumerate(buyer_sources_raw)]
    requirements = [_normalize_requirement(item, i) for i, item in enumerate(requirements_raw)]
    evidence = [_normalize_approved_evidence(item, i) for i, item in enumerate(evidence_raw)]

    def unique(rows: list[dict[str, Any]], key: str, label: str) -> None:
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            raise QualificationError(f"{label}:DUPLICATE_{key.upper()}")

    unique(buyer_sources, "source_id", "trusted.buyer_sources")
    unique(requirements, "requirement_id", "trusted.requirements")
    unique(evidence, "evidence_id", "trusted.approved_evidence")
    buyer_sources.sort(key=lambda row: row["source_id"])
    requirements.sort(key=lambda row: row["requirement_id"])
    evidence.sort(key=lambda row: row["evidence_id"])

    buyer_by_id = {row["source_id"]: row for row in buyer_sources}
    for requirement in requirements:
        source = buyer_by_id.get(requirement["buyer_source_id"])
        if source is None:
            raise QualificationError(f"trusted.requirement.{requirement['requirement_id']}:UNKNOWN_BUYER_SOURCE")
        if source["sha256"] != requirement["buyer_source_sha256"]:
            raise QualificationError(f"trusted.requirement.{requirement['requirement_id']}:BUYER_SOURCE_DIGEST_MISMATCH")

    deadline_source_id = _require_ident(raw["deadline_source_id"], "trusted.deadline_source_id")
    if deadline_source_id not in buyer_by_id:
        raise QualificationError("trusted.deadline_source_id:UNKNOWN_BUYER_SOURCE")

    buyer_set_digest = _validate_sha(raw["buyer_source_set_sha256"], "trusted.buyer_source_set_sha256")
    req_set_digest = _validate_sha(raw["requirement_set_sha256"], "trusted.requirement_set_sha256")
    evidence_set_digest = _validate_sha(raw["evidence_set_sha256"], "trusted.evidence_set_sha256")
    if buyer_set_digest != digest_object(buyer_sources):
        raise QualificationError("trusted.buyer_source_set_sha256:MISMATCH")
    if req_set_digest != digest_object(requirements):
        raise QualificationError("trusted.requirement_set_sha256:MISMATCH")
    if evidence_set_digest != digest_object(evidence):
        raise QualificationError("trusted.evidence_set_sha256:MISMATCH")

    normalized = {
        "contract": TRUST_CONTRACT,
        "schema_version": TRUST_SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "source_ledger_sha256": _validate_sha(raw["source_ledger_sha256"], "trusted.source_ledger_sha256"),
        "tender_pack_sha256": _validate_sha(raw["tender_pack_sha256"], "trusted.tender_pack_sha256"),
        "extracted_at": extracted_at.isoformat().replace("+00:00", "Z"),
        "addenda_checked_through": addenda_checked.isoformat().replace("+00:00", "Z"),
        "response_deadline": deadline.isoformat().replace("+00:00", "Z"),
        "deadline_source_id": deadline_source_id,
        "complete": _require_bool(raw, "complete", label="trusted.complete"),
        "buyer_sources": buyer_sources,
        "buyer_source_set_sha256": buyer_set_digest,
        "requirements": requirements,
        "requirement_set_sha256": req_set_digest,
        "approved_evidence": evidence,
        "evidence_set_sha256": evidence_set_digest,
    }
    return normalized


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return canonical_bytes(self.payload) + b"\n"


def _expected_subjects(route: str, cure: str) -> set[str]:
    if route in TEAMING_ROUTES:
        return {"PARTNER"}
    if cure == "PARTNER":
        return {"PRIME", "PARTNER"}
    return {"PRIME"}


def _build_receipt(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "receipt_sha256": digest_object(body)}


def verify_receipt_integrity(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    actual = receipt.get("receipt_sha256")
    if not isinstance(actual, str) or not SHA256_RE.fullmatch(actual):
        return False
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    return digest_object(body) == actual and body.get("tender_submission_authorized") is False


def evaluate(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    trusted_as_of: str,
    tender_pack_bytes: bytes | None = None,
    trusted_qualification: dict[str, Any] | None = None,
    trusted_qualification_sha256: str | None = None,
) -> Evaluation:
    s = validate_source(source, tender_pack_bytes=tender_pack_bytes, trusted_as_of=trusted_as_of)
    m = validate_manifest(manifest, source_raw, trusted_as_of=trusted_as_of)
    now = s["trusted_now"]
    source_age_seconds = (now - s["checked_at"]).total_seconds()
    if source_age_seconds < 0:
        raise QualificationError("source.checked_at:AFTER_TRUSTED_TIME")

    trust: dict[str, Any] | None = None
    trust_digest: str | None = None
    trust_reasons: list[str] = []
    if trusted_qualification is None and trusted_qualification_sha256 is not None:
        raise QualificationError("TRUSTED_QUALIFICATION_FILE_REQUIRED")
    if trusted_qualification is not None and trusted_qualification_sha256 is None:
        trust_reasons.append("TRUST_ROOT_NOT_PROVIDED")
    elif trusted_qualification is not None:
        expected_root = _validate_sha(trusted_qualification_sha256, "trusted_qualification_sha256")
        trust = normalize_trusted_qualification(trusted_qualification, trusted_as_of=trusted_as_of)
        trust_digest = digest_object(trust)
        if trust_digest != expected_root:
            raise QualificationError("TRUST_ROOT_MISMATCH")
        if trust["source_ledger_sha256"] != m["source_sha256"]:
            raise QualificationError("TRUST_SOURCE_LEDGER_DIGEST_MISMATCH")
        if s["pack_actual_sha256"] is None:
            trust_reasons.append("TENDER_PACK_BYTES_NOT_AVAILABLE_FOR_TRUST")
        elif trust["tender_pack_sha256"] != s["pack_actual_sha256"]:
            raise QualificationError("TRUST_TENDER_PACK_DIGEST_MISMATCH")
        source_deadline = s["response_deadline"].isoformat().replace("+00:00", "Z")
        if trust["response_deadline"] != source_deadline:
            raise QualificationError("TRUST_DEADLINE_MISMATCH")

    missing_caps: list[dict[str, str]] = []
    relevant_requirements: list[dict[str, Any]] = []
    trusted_requirement_ids: list[str] = []
    if trust is not None:
        relevant_requirements = [
            req for req in trust["requirements"]
            if req["mandatory"] and (m["route"] in req["routes"] or "ALL" in req["routes"])
        ]
        trusted_requirement_ids = [req["requirement_id"] for req in relevant_requirements]
        strategic_claims = {req["claim_id"] for req in relevant_requirements}
        missing_floor = sorted(set(ROUTES[m["route"]]) - strategic_claims)
        for claim in missing_floor:
            missing_caps.append({"gate": claim, "status": "UNCOMMITTED_REQUIRED_CLAIM"})

        approved = {row["evidence_id"]: row for row in trust["approved_evidence"]}
        for requirement in relevant_requirements:
            claim = requirement["claim_id"]
            record = m["capabilities"].get(claim)
            if record is None:
                missing_caps.append({"gate": claim, "status": "UNDECLARED"})
                continue
            if record["status"] != "PROVEN":
                missing_caps.append({"gate": claim, "status": record["status"]})
                continue
            allowed_subjects = _expected_subjects(m["route"], requirement["cure"])
            valid = False
            for evidence_id in record["evidence_refs"]:
                evidence = approved.get(evidence_id)
                if (
                    evidence is not None
                    and evidence["claim_id"] == claim
                    and evidence["subject"] in allowed_subjects
                ):
                    valid = True
                    break
            if not valid:
                missing_caps.append({"gate": claim, "status": "UNAPPROVED_EVIDENCE"})

        if m["route"] in TEAMING_ROUTES:
            partner = m["capabilities"].get("partner_prime_confirmation")
            valid_partner = False
            if m["partner_prime_confirmed"] and partner and partner["status"] == "PROVEN":
                for evidence_id in partner["evidence_refs"]:
                    evidence = approved.get(evidence_id)
                    if evidence and evidence["claim_id"] == "partner_prime_confirmation" and evidence["subject"] == "PARTNER":
                        valid_partner = True
                        break
            if not valid_partner:
                missing_caps.append({"gate": "partner_prime_confirmation", "status": "UNAPPROVED_EVIDENCE"})

    if source_age_seconds > MAX_SOURCE_AGE_SECONDS:
        state = "HOLD_SOURCE_STALE"
        exit_code = 3
    elif not s["pack_acquired"]:
        state = "HOLD_TENDER_PACK_REQUIRED"
        exit_code = 3
    elif tender_pack_bytes is None:
        state = "HOLD_TENDER_PACK_FILE_REQUIRED"
        exit_code = 3
    elif not s["pack_reviewed"]:
        state = "HOLD_TENDER_PACK_REVIEW"
        exit_code = 3
    elif trust is None or trust_reasons:
        state = "HOLD_TRUSTED_QUALIFICATION_REQUIRED"
        exit_code = 3
    elif not trust["complete"]:
        state = "HOLD_REQUIREMENT_UNIVERSE_UNVERIFIED"
        exit_code = 3
    else:
        addenda_checked = _parse_dt(trust["addenda_checked_through"], "trusted.addenda_checked_through")
        addenda_age = (now - addenda_checked).total_seconds()
        if addenda_age < 0:
            raise QualificationError("trusted.addenda_checked_through:AFTER_TRUSTED_TIME")
        if addenda_age > MAX_ADDENDA_AGE_SECONDS:
            state = "HOLD_ADDENDA_INVENTORY_STALE"
            exit_code = 3
        elif now >= _parse_dt(trust["response_deadline"], "trusted.response_deadline"):
            state = "NO_BID_DEADLINE_CLOSED"
            exit_code = 4
        elif missing_caps:
            state = "HOLD_EVIDENCE_GAPS"
            exit_code = 3
        elif m["route"] in TEAMING_ROUTES and not m["partner_prime_confirmed"]:
            state = "HOLD_PARTNER_REQUIRED"
            exit_code = 3
        else:
            state = "READY_FOR_OWNER_TENDER_REVIEW"
            exit_code = 0

    body = {
        "schema_version": 2,
        "notice_id": NOTICE_ID,
        "route": m["route"],
        "state": state,
        "source_age_seconds": int(source_age_seconds),
        "source_ledger_sha256": m["source_sha256"],
        "tender_pack_acquired": s["pack_acquired"],
        "tender_pack_reviewed": s["pack_reviewed"],
        "tender_pack_sha256": s["pack_declared_sha256"],
        "trusted_qualification_sha256": trust_digest,
        "trusted_requirement_set_sha256": trust["requirement_set_sha256"] if trust else None,
        "trusted_evidence_set_sha256": trust["evidence_set_sha256"] if trust else None,
        "trusted_buyer_source_set_sha256": trust["buyer_source_set_sha256"] if trust else None,
        "trusted_requirement_ids": trusted_requirement_ids,
        "response_deadline": trust["response_deadline"] if trust else None,
        "partner_prime_confirmed": m["partner_prime_confirmed"],
        "missing_required_capabilities": sorted(missing_caps, key=lambda row: (row["gate"], row["status"])),
        "trust_reasons": sorted(trust_reasons),
        "authority": "INTERNAL_QUALIFICATION_ONLY",
        "tender_submission_authorized": False,
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
    }
    payload = _build_receipt(body)
    return Evaluation(state, exit_code, payload)


def verify_current_evaluation(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    trusted_current_as_of: str,
    tender_pack_bytes: bytes | None = None,
    trusted_qualification: dict[str, Any] | None = None,
    trusted_qualification_sha256: str | None = None,
) -> bool:
    if not verify_receipt_integrity(receipt):
        return False
    prior_time_raw = receipt.get("evaluated_at")
    if not isinstance(prior_time_raw, str):
        return False
    prior_time = _parse_dt(prior_time_raw, "receipt.evaluated_at")
    current_time = _trusted_dt(trusted_current_as_of, "trusted_current_as_of")
    if current_time < prior_time:
        raise QualificationError("TRUSTED_CURRENT_TIME_ROLLBACK")
    try:
        historical = evaluate(
            manifest,
            source,
            source_raw,
            trusted_as_of=prior_time.isoformat().replace("+00:00", "Z"),
            tender_pack_bytes=tender_pack_bytes,
            trusted_qualification=trusted_qualification,
            trusted_qualification_sha256=trusted_qualification_sha256,
        )
        if historical.payload != receipt:
            return False
        current = evaluate(
            manifest,
            source,
            source_raw,
            trusted_as_of=trusted_current_as_of,
            tender_pack_bytes=tender_pack_bytes,
            trusted_qualification=trusted_qualification,
            trusted_qualification_sha256=trusted_qualification_sha256,
        )
    except QualificationError:
        return False

    stable_keys = {
        "notice_id",
        "route",
        "state",
        "source_ledger_sha256",
        "tender_pack_sha256",
        "trusted_qualification_sha256",
        "trusted_requirement_set_sha256",
        "trusted_evidence_set_sha256",
        "trusted_buyer_source_set_sha256",
        "trusted_requirement_ids",
        "response_deadline",
        "partner_prime_confirmed",
        "missing_required_capabilities",
        "trust_reasons",
        "authority",
        "tender_submission_authorized",
    }
    return all(receipt.get(key) == current.payload.get(key) for key in stable_keys)


def trusted_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--source-ledger", type=Path, default=Path(__file__).with_name("sources.json"))
    p.add_argument("--tender-pack", type=Path, default=None)
    p.add_argument("--trusted-qualification", type=Path, default=None)
    p.add_argument("--trusted-qualification-sha256", default=None)
    p.add_argument("--verify-receipt", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args(argv)
    now = trusted_utc_now()
    try:
        source_raw = _read_plain_file(args.source_ledger, max_bytes=MAX_JSON_BYTES, label="source_ledger")
        manifest_raw = _read_plain_file(args.manifest, max_bytes=MAX_JSON_BYTES, label="manifest")
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_bytes(manifest_raw, "manifest")
        pack_bytes = (
            _read_plain_file(args.tender_pack, max_bytes=MAX_TENDER_PACK_BYTES, label="tender_pack")
            if args.tender_pack else None
        )
        if (args.trusted_qualification is None) != (args.trusted_qualification_sha256 is None):
            raise QualificationError("TRUSTED_QUALIFICATION_AND_SHA_REQUIRED_TOGETHER")
        trust = None
        if args.trusted_qualification is not None:
            trust_raw = _read_plain_file(
                args.trusted_qualification,
                max_bytes=MAX_JSON_BYTES,
                label="trusted_qualification",
            )
            trust = load_json_bytes(trust_raw, "trusted_qualification")

        result = evaluate(
            manifest,
            source,
            source_raw,
            trusted_as_of=now,
            tender_pack_bytes=pack_bytes,
            trusted_qualification=trust,
            trusted_qualification_sha256=args.trusted_qualification_sha256,
        )
        if args.verify_receipt:
            receipt_raw = _read_plain_file(args.verify_receipt, max_bytes=MAX_JSON_BYTES, label="receipt")
            receipt = load_json_bytes(receipt_raw, "receipt")
            valid = verify_current_evaluation(
                receipt,
                manifest,
                source,
                source_raw,
                trusted_current_as_of=now,
                tender_pack_bytes=pack_bytes,
                trusted_qualification=trust,
                trusted_qualification_sha256=args.trusted_qualification_sha256,
            )
            payload = {"valid_current": valid, "evaluated_at": now}
            encoded = canonical_bytes(payload) + b"\n"
            if args.output:
                if args.output.exists():
                    raise QualificationError("OUTPUT_ALREADY_EXISTS")
                args.output.write_bytes(encoded)
            else:
                sys.stdout.buffer.write(encoded)
            return 0 if valid else 3
    except (OSError, QualificationError) as exc:
        payload = {"state": "INVALID_INPUT", "error": str(exc), "tender_submission_authorized": False}
        sys.stderr.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return 2

    encoded = result.bytes()
    if args.output:
        if args.output.exists():
            payload = {"state": "INVALID_INPUT", "error": "OUTPUT_ALREADY_EXISTS", "tender_submission_authorized": False}
            sys.stderr.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            return 2
        args.output.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
