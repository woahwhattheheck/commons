"""Strict candidate, source, and authority contracts for DCSA Innovation Call #01."""

from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any, Dict, Iterable, Mapping

from .strict import (
    ValidationError,
    canonical_json_bytes,
    format_utc,
    parse_utc,
    require_bool,
    require_exact_keys,
    require_hex64,
    require_int,
    require_nullable_hex64,
    require_plain_list,
    require_string,
)

CANDIDATE_SCHEMA = "dcsa-innovation-call-01/candidate/v1"
SOURCE_SCHEMA = "dcsa-innovation-call-01/source-ledger/v1"
AUTHORITY_SCHEMA = "dcsa-innovation-call-01/host-authority/v1"
FLOOR_SCHEMA = "dcsa-innovation-call-01/authority-floor/v1"
REPORT_SCHEMA = "dcsa-innovation-call-01/qualification-report/v1"

NOTICE_ID = "DCSAInnovationCall01"
GENERAL_SOLICITATION_ID = "HS0021-26-CSO-DCSA"
QUESTION_DEADLINE = dt.datetime(2026, 9, 14, 15, 0, 0, tzinfo=dt.timezone.utc)
LIVE_QA_AT = dt.datetime(2026, 9, 16, 15, 0, 0, tzinfo=dt.timezone.utc)
CONCEPT_DEADLINE = dt.datetime(2026, 9, 18, 13, 0, 0, tzinfo=dt.timezone.utc)
ESTIMATED_START_DATE = "2026-10-15"
MAX_SOURCE_OBSERVATION_AGE = dt.timedelta(hours=24)
MAX_CURRENT_REPORT_AGE = dt.timedelta(minutes=5)

REQUIRED_DOCUMENTS = (
    "innovation_call_pdf",
    "general_solicitation_pdf",
    "concept_paper_template",
    "ecosystem_style_guide",
)

REQUIRED_CAPABILITIES = (
    "mission_workflow_discovery",
    "unified_experience_shell",
    "multi_idp_icam",
    "policy_attribute_access",
    "api_event_integration",
    "legacy_ie_sustainment",
    "devsecops_iac",
    "security_authorization_ato",
    "test_acceptance_evidence",
    "production_transition_rom",
)

_ALLOWED_ROUTE_PREFERENCES = {"AUTO", "DIRECT", "TEAMING"}
_ALLOWED_EVIDENCE_STATES = {"VERIFIED", "NOT_HELD", "UNVERIFIED"}
_ALLOWED_ROM_STATES = {"OWNER_DECISION_REQUIRED", "OWNER_APPROVED"}
_ALLOWED_SOURCE_ROLES = {
    "CONTROLLING_CALL",
    "CONTROLLING_GENERAL_SOLICITATION",
    "MANDATORY_TEMPLATE",
    "DESIGN_REFERENCE",
}

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sorted_unique_strings(
    value: Any,
    *,
    field: str,
    maximum_items: int,
    maximum_length: int,
) -> list[str]:
    rows = require_plain_list(value, field=field)
    if len(rows) > maximum_items:
        raise ValidationError(f"{field} exceeds {maximum_items} items")
    normalized = [
        require_string(item, field=f"{field}[{index}]", maximum=maximum_length)
        for index, item in enumerate(rows)
    ]
    if len(set(normalized)) != len(normalized):
        raise ValidationError(f"{field} contains duplicate values")
    return sorted(normalized)


def normalize_candidate(value: Any) -> Dict[str, Any]:
    obj = require_exact_keys(
        value,
        {
            "schema",
            "subject_id",
            "operation_id",
            "route_preference",
            "concept_title",
            "declared_capabilities",
            "background_ip",
            "third_party_dependencies",
            "risks",
            "question_drafts",
            "rom_state",
        },
        field="candidate",
    )
    if obj["schema"] != CANDIDATE_SCHEMA:
        raise ValidationError("candidate schema is unsupported")
    route = require_string(obj["route_preference"], field="route_preference", maximum=16)
    if route not in _ALLOWED_ROUTE_PREFERENCES:
        raise ValidationError("route_preference is unsupported")
    rom_state = require_string(obj["rom_state"], field="rom_state", maximum=32)
    if rom_state not in _ALLOWED_ROM_STATES:
        raise ValidationError("rom_state is unsupported")
    capabilities = _sorted_unique_strings(
        obj["declared_capabilities"],
        field="declared_capabilities",
        maximum_items=32,
        maximum_length=80,
    )
    unknown = sorted(set(capabilities) - set(REQUIRED_CAPABILITIES))
    if unknown:
        raise ValidationError(f"declared_capabilities contains unsupported values: {unknown}")
    return {
        "schema": CANDIDATE_SCHEMA,
        "subject_id": require_string(obj["subject_id"], field="subject_id", maximum=128),
        "operation_id": require_string(obj["operation_id"], field="operation_id", maximum=160),
        "route_preference": route,
        "concept_title": require_string(obj["concept_title"], field="concept_title", maximum=200),
        "declared_capabilities": capabilities,
        "background_ip": _sorted_unique_strings(
            obj["background_ip"], field="background_ip", maximum_items=24, maximum_length=240
        ),
        "third_party_dependencies": _sorted_unique_strings(
            obj["third_party_dependencies"],
            field="third_party_dependencies",
            maximum_items=32,
            maximum_length=240,
        ),
        "risks": _sorted_unique_strings(
            obj["risks"], field="risks", maximum_items=32, maximum_length=400
        ),
        "question_drafts": _sorted_unique_strings(
            obj["question_drafts"],
            field="question_drafts",
            maximum_items=24,
            maximum_length=600,
        ),
        "rom_state": rom_state,
    }


def normalize_source_ledger(value: Any) -> Dict[str, Any]:
    obj = require_exact_keys(
        value,
        {"schema", "notice_id", "general_solicitation_id", "observed_at", "documents"},
        field="source ledger",
    )
    if obj["schema"] != SOURCE_SCHEMA:
        raise ValidationError("source ledger schema is unsupported")
    if obj["notice_id"] != NOTICE_ID or obj["general_solicitation_id"] != GENERAL_SOLICITATION_ID:
        raise ValidationError("source ledger identifies a different solicitation")
    observed_at = parse_utc(obj["observed_at"], field="source ledger observed_at")
    docs_raw = require_plain_list(obj["documents"], field="source ledger documents")
    if len(docs_raw) != len(REQUIRED_DOCUMENTS):
        raise ValidationError("source ledger must contain the exact required document set")
    docs: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(docs_raw):
        doc = require_exact_keys(
            raw,
            {
                "document_id",
                "role",
                "authority",
                "official_url",
                "mirror_url",
                "posted_at",
                "retained_bytes",
                "sha256",
            },
            field=f"source document {index}",
        )
        document_id = require_string(doc["document_id"], field="document_id", maximum=80)
        if document_id in seen:
            raise ValidationError("source ledger contains duplicate document_id")
        seen.add(document_id)
        role = require_string(doc["role"], field=f"{document_id}.role", maximum=64)
        if role not in _ALLOWED_SOURCE_ROLES:
            raise ValidationError(f"{document_id}.role is unsupported")
        authority = require_string(doc["authority"], field=f"{document_id}.authority", maximum=40)
        if authority != "OFFICIAL_FIRST_PARTY":
            raise ValidationError(f"{document_id} must identify the official first-party source")
        retained = require_bool(doc["retained_bytes"], field=f"{document_id}.retained_bytes")
        digest = require_nullable_hex64(doc["sha256"], field=f"{document_id}.sha256")
        if retained != (digest is not None):
            raise ValidationError(
                f"{document_id} retained_bytes and sha256 must agree"
            )
        docs.append(
            {
                "document_id": document_id,
                "role": role,
                "authority": authority,
                "official_url": require_string(
                    doc["official_url"], field=f"{document_id}.official_url", maximum=1000
                ),
                "mirror_url": (
                    None
                    if doc["mirror_url"] is None
                    else require_string(
                        doc["mirror_url"], field=f"{document_id}.mirror_url", maximum=1000
                    )
                ),
                "posted_at": format_utc(parse_utc(doc["posted_at"], field=f"{document_id}.posted_at")),
                "retained_bytes": retained,
                "sha256": digest,
            }
        )
    if seen != set(REQUIRED_DOCUMENTS):
        raise ValidationError("source ledger document IDs do not match the required set")
    docs.sort(key=lambda row: row["document_id"])
    source_generation = _sha256(
        canonical_json_bytes(
            {
                "notice_id": NOTICE_ID,
                "general_solicitation_id": GENERAL_SOLICITATION_ID,
                "documents": [
                    {
                        "document_id": row["document_id"],
                        "role": row["role"],
                        "sha256": row["sha256"],
                    }
                    for row in docs
                ],
            }
        )
    )
    complete = all(row["retained_bytes"] for row in docs)
    return {
        "schema": SOURCE_SCHEMA,
        "notice_id": NOTICE_ID,
        "general_solicitation_id": GENERAL_SOLICITATION_ID,
        "observed_at": format_utc(observed_at),
        "documents": docs,
        "source_generation_sha256": source_generation,
        "complete": complete,
    }


def _normalize_evidence(value: Any, *, field: str) -> Dict[str, Any]:
    obj = require_exact_keys(value, {"state", "evidence_ref", "evidence_sha256"}, field=field)
    state = require_string(obj["state"], field=f"{field}.state", maximum=16)
    if state not in _ALLOWED_EVIDENCE_STATES:
        raise ValidationError(f"{field}.state is unsupported")
    ref = obj["evidence_ref"]
    digest = obj["evidence_sha256"]
    if state == "VERIFIED":
        ref = require_string(ref, field=f"{field}.evidence_ref", maximum=240)
        digest = require_hex64(digest, field=f"{field}.evidence_sha256")
    else:
        if ref is not None or digest is not None:
            raise ValidationError(f"{field} non-VERIFIED states cannot carry evidence authority")
    return {"state": state, "evidence_ref": ref, "evidence_sha256": digest}


def normalize_authority(value: Any) -> Dict[str, Any]:
    obj = require_exact_keys(
        value,
        {
            "schema",
            "generation",
            "issued_at",
            "valid_until",
            "subject_id",
            "source_generation_sha256",
            "direct_clearance",
            "personnel",
            "ota_eligibility",
            "capability_evidence",
            "owner_decisions",
        },
        field="host authority",
    )
    if obj["schema"] != AUTHORITY_SCHEMA:
        raise ValidationError("host authority schema is unsupported")
    issued_at = parse_utc(obj["issued_at"], field="authority issued_at")
    valid_until = parse_utc(obj["valid_until"], field="authority valid_until")
    if valid_until <= issued_at:
        raise ValidationError("authority valid_until must follow issued_at")
    direct = require_exact_keys(
        obj["direct_clearance"], {"active_top_secret_fcl"}, field="direct_clearance"
    )
    personnel = require_exact_keys(
        obj["personnel"],
        {
            "all_assigned_us_citizens",
            "all_assigned_interim_secret_or_higher",
            "privileged_users_t5_or_ts_start",
            "cac_operability",
        },
        field="personnel",
    )
    ota = require_exact_keys(
        obj["ota_eligibility"], {"direct_path", "teaming_prime_path"}, field="ota_eligibility"
    )
    capability_rows = require_plain_list(obj["capability_evidence"], field="capability_evidence")
    if len(capability_rows) != len(REQUIRED_CAPABILITIES):
        raise ValidationError("capability_evidence must cover the exact required capability set")
    normalized_caps: list[Dict[str, Any]] = []
    seen_caps: set[str] = set()
    for index, raw in enumerate(capability_rows):
        row = require_exact_keys(
            raw,
            {"capability", "state", "evidence_ref", "evidence_sha256"},
            field=f"capability_evidence[{index}]",
        )
        capability = require_string(row["capability"], field="capability", maximum=80)
        if capability not in REQUIRED_CAPABILITIES or capability in seen_caps:
            raise ValidationError("capability_evidence has an unknown or duplicate capability")
        seen_caps.add(capability)
        evidence = _normalize_evidence(
            {
                "state": row["state"],
                "evidence_ref": row["evidence_ref"],
                "evidence_sha256": row["evidence_sha256"],
            },
            field=f"capability_evidence[{capability}]",
        )
        normalized_caps.append({"capability": capability, **evidence})
    normalized_caps.sort(key=lambda row: row["capability"])
    owner = require_exact_keys(
        obj["owner_decisions"],
        {
            "direct_route_approved",
            "teaming_route_approved",
            "rom_approved",
            "external_contact_approved",
            "external_submission_approved",
        },
        field="owner_decisions",
    )
    normalized_owner = {
        key: require_bool(owner[key], field=f"owner_decisions.{key}")
        for key in owner
    }
    if normalized_owner["external_contact_approved"] or normalized_owner["external_submission_approved"]:
        raise ValidationError(
            "this carrier cannot ingest or mint external contact/submission authority"
        )
    return {
        "schema": AUTHORITY_SCHEMA,
        "generation": require_int(obj["generation"], field="authority generation", minimum=1),
        "issued_at": format_utc(issued_at),
        "valid_until": format_utc(valid_until),
        "subject_id": require_string(obj["subject_id"], field="authority subject_id", maximum=128),
        "source_generation_sha256": require_hex64(
            obj["source_generation_sha256"], field="authority source_generation_sha256"
        ),
        "direct_clearance": {
            "active_top_secret_fcl": _normalize_evidence(
                direct["active_top_secret_fcl"], field="active_top_secret_fcl"
            )
        },
        "personnel": {
            key: _normalize_evidence(personnel[key], field=key)
            for key in sorted(personnel)
        },
        "ota_eligibility": {
            "direct_path": _normalize_evidence(ota["direct_path"], field="ota direct_path"),
            "teaming_prime_path": _normalize_evidence(
                ota["teaming_prime_path"], field="ota teaming_prime_path"
            ),
        },
        "capability_evidence": normalized_caps,
        "owner_decisions": normalized_owner,
    }


def normalize_floor(value: Any) -> Dict[str, Any]:
    obj = require_exact_keys(
        value,
        {"schema", "generation", "authority_sha256", "source_generation_sha256"},
        field="authority floor",
    )
    if obj["schema"] != FLOOR_SCHEMA:
        raise ValidationError("authority floor schema is unsupported")
    return {
        "schema": FLOOR_SCHEMA,
        "generation": require_int(obj["generation"], field="floor generation", minimum=1),
        "authority_sha256": require_hex64(obj["authority_sha256"], field="floor authority_sha256"),
        "source_generation_sha256": require_hex64(
            obj["source_generation_sha256"], field="floor source_generation_sha256"
        ),
    }


def authority_sha256(authority: Mapping[str, Any]) -> str:
    """Digest the normalized authority generation, never caller key ordering."""

    return _sha256(canonical_json_bytes(normalize_authority(authority)))

