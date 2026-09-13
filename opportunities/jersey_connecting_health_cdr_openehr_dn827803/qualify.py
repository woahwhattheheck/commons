#!/usr/bin/env python3
"""Fail-closed qualification engine for Jersey procurement DN827803 (authority v2)."""
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
SCHEMA_VERSION = 2
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ROUTES = {
    "PRIME_CDR",
    "TEAMING_INTEROPERABILITY_SPECIALIST",
    "TEAMING_ACCEPTANCE_EVIDENCE",
}
TEAMING_ROUTES = {"TEAMING_INTEROPERABILITY_SPECIALIST", "TEAMING_ACCEPTANCE_EVIDENCE"}
CLAIM_STATES = {"PROVEN", "PARTNER_CURABLE", "MISSING", "UNKNOWN", "NOT_APPLICABLE"}
CURE_SEMANTICS = {"SELF_ONLY", "PARTNER_ALLOWED", "NOT_CURABLE"}
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


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _require_str(obj: dict[str, Any], key: str, *, prefix: str = "") -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QualificationError(f"{prefix}{key}:MUST_BE_STRING")
    return value


def _require_bool(obj: dict[str, Any], key: str, *, prefix: str = "") -> bool:
    value = obj.get(key)
    if type(value) is not bool:
        raise QualificationError(f"{prefix}{key}:MUST_BE_BOOL")
    return value


def _require_int(
    obj: dict[str, Any],
    key: str,
    *,
    prefix: str = "",
    minimum: int | None = None,
) -> int:
    value = obj.get(key)
    if type(value) is not int:
        raise QualificationError(f"{prefix}{key}:MUST_BE_INT_NOT_BOOL")
    if minimum is not None and value < minimum:
        raise QualificationError(f"{prefix}{key}:BELOW_MINIMUM")
    return value


def _parse_dt(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label}:INVALID_DATETIME") from exc
    if parsed.tzinfo is None:
        raise QualificationError(f"{label}:TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_SHA256")
    return value


def _optional_sha(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _validate_sha(value, label)


def _validate_schema(obj: dict[str, Any], label: str) -> None:
    if _require_int(obj, "schema_version", prefix=f"{label}.", minimum=1) != SCHEMA_VERSION:
        raise QualificationError(f"{label}.schema_version:UNSUPPORTED")
    if _require_str(obj, "notice_id", prefix=f"{label}.") != NOTICE_ID:
        raise QualificationError(f"{label}.notice_id:MISMATCH")


def _set_digest(records: list[dict[str, Any]]) -> str:
    ordered = sorted(records, key=lambda item: item["id"])
    return sha256_bytes(canonical_bytes(ordered))


def validate_source(
    source: dict[str, Any],
    *,
    tender_pack_bytes: bytes | None,
) -> dict[str, Any]:
    _validate_schema(source, "source")
    checked_at = _parse_dt(_require_str(source, "checked_at", prefix="source."), "source.checked_at")
    response_deadline = _parse_dt(
        _require_str(source, "response_deadline", prefix="source."),
        "source.response_deadline",
    )
    pack = source.get("tender_pack")
    if not isinstance(pack, dict):
        raise QualificationError("source.tender_pack:MUST_BE_OBJECT")
    acquired = _require_bool(pack, "acquired", prefix="source.tender_pack.")
    reviewed = _require_bool(pack, "reviewed", prefix="source.tender_pack.")
    state = _require_str(pack, "state", prefix="source.tender_pack.")
    declared_sha = pack.get("sha256")
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
        declared_sha = _validate_sha(declared_sha, "source.tender_pack.sha256")
        expected_state = (
            "TENDER_PACK_ACQUIRED_REVIEWED"
            if reviewed
            else "TENDER_PACK_ACQUIRED_UNREVIEWED"
        )
        if state != expected_state:
            raise QualificationError("source.tender_pack:STATE_MISMATCH")
        if tender_pack_bytes is not None:
            actual_sha = sha256_bytes(tender_pack_bytes)
            if actual_sha != declared_sha:
                raise QualificationError("TENDER_PACK_DIGEST_MISMATCH")

    return {
        "checked_at": checked_at,
        "response_deadline": response_deadline,
        "pack_acquired": acquired,
        "pack_reviewed": reviewed,
        "pack_declared_sha256": declared_sha,
        "pack_actual_sha256": actual_sha,
    }


def validate_trusted_root(
    trusted_root: dict[str, Any],
    *,
    source_raw: bytes,
    source_info: dict[str, Any],
    trusted_as_of: datetime,
) -> dict[str, Any]:
    _validate_schema(trusted_root, "trusted_root")
    retained_at = _parse_dt(
        _require_str(trusted_root, "retained_at", prefix="trusted_root."),
        "trusted_root.retained_at",
    )
    if trusted_as_of.tzinfo is None:
        raise QualificationError("trusted_as_of:TIMEZONE_REQUIRED")
    trusted_as_of = trusted_as_of.astimezone(timezone.utc)
    if trusted_as_of < retained_at:
        raise QualificationError("TRUSTED_TIME_ROLLBACK")

    expected_source_sha = _validate_sha(
        trusted_root.get("source_ledger_sha256"),
        "trusted_root.source_ledger_sha256",
    )
    if sha256_bytes(source_raw) != expected_source_sha:
        raise QualificationError("RETAINED_SOURCE_ROOT_MISMATCH")

    root_checked_at = _parse_dt(
        _require_str(trusted_root, "source_checked_at", prefix="trusted_root."),
        "trusted_root.source_checked_at",
    )
    if root_checked_at != source_info["checked_at"]:
        raise QualificationError("SOURCE_CHECKED_AT_ROOT_MISMATCH")
    if source_info["checked_at"] > trusted_as_of:
        raise QualificationError("SOURCE_CHECK_IN_FUTURE")

    root_deadline = _parse_dt(
        _require_str(trusted_root, "response_deadline", prefix="trusted_root."),
        "trusted_root.response_deadline",
    )
    if root_deadline != source_info["response_deadline"]:
        raise QualificationError("DEADLINE_ROOT_MISMATCH")

    max_source_age_seconds = _require_int(
        trusted_root,
        "max_source_age_seconds",
        prefix="trusted_root.",
        minimum=1,
    )
    root_pack_sha = _optional_sha(
        trusted_root.get("tender_pack_sha256"),
        "trusted_root.tender_pack_sha256",
    )
    extraction_sha = _optional_sha(
        trusted_root.get("extraction_sha256"),
        "trusted_root.extraction_sha256",
    )
    evidence_sha = _optional_sha(
        trusted_root.get("evidence_bundle_sha256"),
        "trusted_root.evidence_bundle_sha256",
    )

    if source_info["pack_acquired"]:
        if root_pack_sha is None:
            raise QualificationError("TRUSTED_ROOT:TENDER_PACK_COMMITMENT_REQUIRED")
        if root_pack_sha != source_info["pack_declared_sha256"]:
            raise QualificationError("TENDER_PACK_ROOT_MISMATCH")
    elif any(value is not None for value in (root_pack_sha, extraction_sha, evidence_sha)):
        raise QualificationError("TRUSTED_ROOT:PACK_COMMITMENTS_WITHOUT_ACQUISITION")

    return {
        "retained_at": retained_at,
        "source_sha256": expected_source_sha,
        "source_checked_at": root_checked_at,
        "response_deadline": root_deadline,
        "max_source_age_seconds": max_source_age_seconds,
        "tender_pack_sha256": root_pack_sha,
        "extraction_sha256": extraction_sha,
        "evidence_bundle_sha256": evidence_sha,
        "commitment_sha256": sha256_bytes(canonical_bytes(trusted_root)),
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(manifest, "manifest")
    route = _require_str(manifest, "route", prefix="manifest.")
    if route not in ROUTES:
        raise QualificationError("manifest.route:UNSUPPORTED")
    subject_id = _require_str(manifest, "subject_id", prefix="manifest.")
    partner_prime_confirmed = _require_bool(
        manifest,
        "partner_prime_confirmed",
        prefix="manifest.",
    )

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise QualificationError("manifest.authority:MUST_BE_OBJECT")
    missing = AUTHORITY_FLAGS - authority.keys()
    extra = authority.keys() - AUTHORITY_FLAGS
    if missing:
        raise QualificationError(
            "manifest.authority:MISSING_FLAGS:" + ",".join(sorted(missing))
        )
    if extra:
        raise QualificationError(
            "manifest.authority:UNKNOWN_FLAGS:" + ",".join(sorted(extra))
        )
    escalated = [
        key for key in sorted(AUTHORITY_FLAGS)
        if _require_bool(authority, key, prefix="manifest.authority.")
    ]
    if escalated:
        raise QualificationError(
            "AUTHORITY_ESCALATION_FORBIDDEN:" + ",".join(escalated)
        )

    claims = manifest.get("requirement_claims")
    if not isinstance(claims, dict):
        raise QualificationError("manifest.requirement_claims:MUST_BE_OBJECT")
    normalized: dict[str, dict[str, Any]] = {}
    for requirement_id, record in claims.items():
        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
            or not isinstance(record, dict)
        ):
            raise QualificationError("manifest.requirement_claims:INVALID_RECORD")
        status = _require_str(
            record,
            "status",
            prefix=f"manifest.requirement_claims.{requirement_id}.",
        )
        if status not in CLAIM_STATES:
            raise QualificationError(f"claim.{requirement_id}:INVALID_STATUS")
        evidence_ids = record.get("evidence_ids")
        if (
            not isinstance(evidence_ids, list)
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
            or len(evidence_ids) != len(set(evidence_ids))
        ):
            raise QualificationError(f"claim.{requirement_id}:INVALID_EVIDENCE_IDS")
        if status == "PROVEN" and not evidence_ids:
            raise QualificationError(f"claim.{requirement_id}:PROVEN_REQUIRES_EVIDENCE")
        if status != "PROVEN" and evidence_ids:
            raise QualificationError(
                f"claim.{requirement_id}:NON_PROVEN_MUST_NOT_CARRY_EVIDENCE"
            )
        normalized[requirement_id] = {
            "status": status,
            "evidence_ids": list(evidence_ids),
        }

    return {
        "route": route,
        "subject_id": subject_id,
        "partner_prime_confirmed": partner_prime_confirmed,
        "claims": normalized,
    }


def validate_extraction(
    extraction_raw: bytes,
    *,
    trusted: dict[str, Any],
    source_info: dict[str, Any],
    trusted_as_of: datetime,
) -> dict[str, Any]:
    expected_sha = trusted["extraction_sha256"]
    if expected_sha is None:
        raise QualificationError("TRUSTED_EXTRACTION_COMMITMENT_REQUIRED")
    if sha256_bytes(extraction_raw) != expected_sha:
        raise QualificationError("RETAINED_EXTRACTION_ROOT_MISMATCH")

    extraction = load_json_bytes(extraction_raw, "extraction")
    _validate_schema(extraction, "extraction")
    if _validate_sha(
        extraction.get("source_ledger_sha256"),
        "extraction.source_ledger_sha256",
    ) != trusted["source_sha256"]:
        raise QualificationError("EXTRACTION_SOURCE_ROOT_MISMATCH")
    if _validate_sha(
        extraction.get("tender_pack_sha256"),
        "extraction.tender_pack_sha256",
    ) != trusted["tender_pack_sha256"]:
        raise QualificationError("EXTRACTION_TENDER_PACK_ROOT_MISMATCH")

    extracted_at = _parse_dt(
        _require_str(extraction, "extracted_at", prefix="extraction."),
        "extraction.extracted_at",
    )
    if extracted_at < source_info["checked_at"]:
        raise QualificationError("EXTRACTION_TIME_BEFORE_SOURCE_CHECK")
    if extracted_at > trusted["retained_at"]:
        raise QualificationError("EXTRACTION_TIME_AFTER_ROOT_RETENTION")
    if extracted_at > trusted_as_of.astimezone(timezone.utc):
        raise QualificationError("EXTRACTION_TIME_IN_FUTURE")

    extraction_deadline = _parse_dt(
        _require_str(extraction, "response_deadline", prefix="extraction."),
        "extraction.response_deadline",
    )
    if extraction_deadline != trusted["response_deadline"]:
        raise QualificationError("EXTRACTION_DEADLINE_ROOT_MISMATCH")
    if extraction_deadline != source_info["response_deadline"]:
        raise QualificationError("EXTRACTION_DEADLINE_SOURCE_MISMATCH")

    if not _require_bool(
        extraction,
        "inventory_complete",
        prefix="extraction.",
    ):
        raise QualificationError("EXTRACTION_INVENTORY_INCOMPLETE")
    if not _require_bool(
        extraction,
        "mandatory_requirements_complete",
        prefix="extraction.",
    ):
        raise QualificationError("EXTRACTION_REQUIREMENT_UNIVERSE_INCOMPLETE")

    inventory = extraction.get("inventory")
    if not isinstance(inventory, list) or not inventory:
        raise QualificationError("extraction.inventory:MUST_BE_NONEMPTY_LIST")
    inventory_by_id: dict[str, dict[str, Any]] = {}
    normalized_inventory: list[dict[str, Any]] = []
    for index, row in enumerate(inventory):
        prefix = f"extraction.inventory[{index}]."
        if not isinstance(row, dict):
            raise QualificationError(f"{prefix}MUST_BE_OBJECT")
        source_id = _require_str(row, "id", prefix=prefix)
        if source_id in inventory_by_id:
            raise QualificationError(f"extraction.inventory:DUPLICATE_ID:{source_id}")
        kind = _require_str(row, "kind", prefix=prefix)
        if kind not in {"TENDER", "ADDENDUM", "SCHEDULE", "FORM"}:
            raise QualificationError(f"{prefix}kind:UNSUPPORTED")
        sha = _validate_sha(row.get("sha256"), f"{prefix}sha256")
        coordinate = _require_str(row, "coordinate", prefix=prefix)
        normalized = {
            "id": source_id,
            "kind": kind,
            "sha256": sha,
            "coordinate": coordinate,
        }
        inventory_by_id[source_id] = normalized
        normalized_inventory.append(normalized)

    inventory_count = _require_int(
        extraction,
        "inventory_count",
        prefix="extraction.",
        minimum=1,
    )
    if inventory_count != len(normalized_inventory):
        raise QualificationError("EXTRACTION_INVENTORY_COUNT_MISMATCH")
    declared_inventory_digest = _validate_sha(
        extraction.get("inventory_set_sha256"),
        "extraction.inventory_set_sha256",
    )
    if declared_inventory_digest != _set_digest(normalized_inventory):
        raise QualificationError("EXTRACTION_INVENTORY_SET_DIGEST_MISMATCH")

    deadline_source_id = _require_str(
        extraction,
        "deadline_source_id",
        prefix="extraction.",
    )
    deadline_source = inventory_by_id.get(deadline_source_id)
    if deadline_source is None:
        raise QualificationError("EXTRACTION_DEADLINE_SOURCE_NOT_IN_INVENTORY")
    deadline_coordinate = _require_str(
        extraction,
        "deadline_source_coordinate",
        prefix="extraction.",
    )
    if deadline_coordinate != deadline_source["coordinate"]:
        raise QualificationError("EXTRACTION_DEADLINE_COORDINATE_MISMATCH")
    _validate_sha(
        extraction.get("deadline_text_sha256"),
        "extraction.deadline_text_sha256",
    )

    requirements = extraction.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise QualificationError("extraction.requirements:MUST_BE_NONEMPTY_LIST")
    requirements_by_id: dict[str, dict[str, Any]] = {}
    normalized_requirements: list[dict[str, Any]] = []
    for index, row in enumerate(requirements):
        prefix = f"extraction.requirements[{index}]."
        if not isinstance(row, dict):
            raise QualificationError(f"{prefix}MUST_BE_OBJECT")
        requirement_id = _require_str(row, "id", prefix=prefix)
        if requirement_id in requirements_by_id:
            raise QualificationError(
                f"extraction.requirements:DUPLICATE_ID:{requirement_id}"
            )
        source_id = _require_str(row, "source_id", prefix=prefix)
        source_row = inventory_by_id.get(source_id)
        if source_row is None:
            raise QualificationError(f"{prefix}source_id:UNKNOWN")
        source_sha = _validate_sha(row.get("source_sha256"), f"{prefix}source_sha256")
        if source_sha != source_row["sha256"]:
            raise QualificationError(f"{prefix}source_sha256:MISMATCH")
        source_coordinate = _require_str(row, "source_coordinate", prefix=prefix)
        if not source_coordinate.startswith(source_row["coordinate"]):
            raise QualificationError(f"{prefix}source_coordinate:OUTSIDE_SOURCE")
        category = _require_str(row, "category", prefix=prefix)
        mandatory = _require_bool(row, "mandatory", prefix=prefix)
        applies_to_routes = row.get("applies_to_routes")
        if (
            not isinstance(applies_to_routes, list)
            or not applies_to_routes
            or any(route not in ROUTES for route in applies_to_routes)
            or len(applies_to_routes) != len(set(applies_to_routes))
        ):
            raise QualificationError(f"{prefix}applies_to_routes:INVALID")
        cure = _require_str(row, "cure", prefix=prefix)
        if cure not in CURE_SEMANTICS:
            raise QualificationError(f"{prefix}cure:UNSUPPORTED")
        allow_shared_evidence = _require_bool(
            row,
            "allow_shared_evidence",
            prefix=prefix,
        )
        text_sha = _validate_sha(row.get("text_sha256"), f"{prefix}text_sha256")
        description = _require_str(row, "description", prefix=prefix)
        description_sha = _validate_sha(
            row.get("description_sha256"),
            f"{prefix}description_sha256",
        )
        if sha256_bytes(description.encode("utf-8")) != description_sha:
            raise QualificationError(f"{prefix}description_sha256:MISMATCH")

        normalized = {
            "id": requirement_id,
            "source_id": source_id,
            "source_sha256": source_sha,
            "source_coordinate": source_coordinate,
            "category": category,
            "mandatory": mandatory,
            "applies_to_routes": sorted(applies_to_routes),
            "cure": cure,
            "allow_shared_evidence": allow_shared_evidence,
            "text_sha256": text_sha,
            "description": description,
            "description_sha256": description_sha,
        }
        requirements_by_id[requirement_id] = normalized
        normalized_requirements.append(normalized)

    requirement_count = _require_int(
        extraction,
        "requirement_count",
        prefix="extraction.",
        minimum=1,
    )
    if requirement_count != len(normalized_requirements):
        raise QualificationError("EXTRACTION_REQUIREMENT_COUNT_MISMATCH")
    declared_requirement_digest = _validate_sha(
        extraction.get("requirement_set_sha256"),
        "extraction.requirement_set_sha256",
    )
    if declared_requirement_digest != _set_digest(normalized_requirements):
        raise QualificationError("EXTRACTION_REQUIREMENT_SET_DIGEST_MISMATCH")

    return {
        "extracted_at": extracted_at,
        "inventory": inventory_by_id,
        "requirements": requirements_by_id,
        "inventory_count": inventory_count,
        "requirement_count": requirement_count,
        "inventory_set_sha256": declared_inventory_digest,
        "requirement_set_sha256": declared_requirement_digest,
    }


def _evidence_binding(record: dict[str, Any]) -> str:
    payload = {
        "subject_id": record["subject_id"],
        "requirement_ids": sorted(record["requirement_ids"]),
        "category": record["category"],
        "source_id": record["source_id"],
        "source_sha256": record["source_sha256"],
        "source_coordinate": record["source_coordinate"],
        "claim_sha256": record["claim_sha256"],
        "reuse_semantics": record["reuse_semantics"],
    }
    return sha256_bytes(canonical_bytes(payload))


def validate_evidence_bundle(
    evidence_raw: bytes,
    *,
    trusted: dict[str, Any],
    extraction: dict[str, Any],
) -> dict[str, Any]:
    expected_sha = trusted["evidence_bundle_sha256"]
    if expected_sha is None:
        raise QualificationError("TRUSTED_EVIDENCE_COMMITMENT_REQUIRED")
    if sha256_bytes(evidence_raw) != expected_sha:
        raise QualificationError("RETAINED_EVIDENCE_ROOT_MISMATCH")

    evidence = load_json_bytes(evidence_raw, "evidence")
    _validate_schema(evidence, "evidence")
    if not _require_bool(evidence, "source_inventory_complete", prefix="evidence."):
        raise QualificationError("EVIDENCE_SOURCE_INVENTORY_INCOMPLETE")

    sources = evidence.get("sources")
    if not isinstance(sources, list):
        raise QualificationError("evidence.sources:MUST_BE_LIST")
    source_by_id: dict[str, dict[str, str]] = {}
    for index, row in enumerate(sources):
        prefix = f"evidence.sources[{index}]."
        if not isinstance(row, dict):
            raise QualificationError(f"{prefix}MUST_BE_OBJECT")
        source_id = _require_str(row, "id", prefix=prefix)
        if source_id in source_by_id:
            raise QualificationError(f"evidence.sources:DUPLICATE_ID:{source_id}")
        source_by_id[source_id] = {
            "sha256": _validate_sha(row.get("sha256"), f"{prefix}sha256"),
            "coordinate": _require_str(row, "coordinate", prefix=prefix),
        }

    records = evidence.get("records")
    if not isinstance(records, list):
        raise QualificationError("evidence.records:MUST_BE_LIST")
    record_by_id: dict[str, dict[str, Any]] = {}
    requirements = extraction["requirements"]
    for index, row in enumerate(records):
        prefix = f"evidence.records[{index}]."
        if not isinstance(row, dict):
            raise QualificationError(f"{prefix}MUST_BE_OBJECT")
        evidence_id = _require_str(row, "id", prefix=prefix)
        if evidence_id in record_by_id:
            raise QualificationError(f"evidence.records:DUPLICATE_ID:{evidence_id}")
        subject_id = _require_str(row, "subject_id", prefix=prefix)
        requirement_ids = row.get("requirement_ids")
        if (
            not isinstance(requirement_ids, list)
            or not requirement_ids
            or any(
                not isinstance(requirement_id, str) or requirement_id not in requirements
                for requirement_id in requirement_ids
            )
            or len(requirement_ids) != len(set(requirement_ids))
        ):
            raise QualificationError(f"{prefix}requirement_ids:INVALID")
        category = _require_str(row, "category", prefix=prefix)
        requirement_rows = [requirements[requirement_id] for requirement_id in requirement_ids]
        if any(requirement["category"] != category for requirement in requirement_rows):
            raise QualificationError(f"{prefix}category:REQUIREMENT_MISMATCH")

        source_id = _require_str(row, "source_id", prefix=prefix)
        source = source_by_id.get(source_id)
        if source is None:
            raise QualificationError(f"{prefix}source_id:UNKNOWN")
        source_sha = _validate_sha(row.get("source_sha256"), f"{prefix}source_sha256")
        if source_sha != source["sha256"]:
            raise QualificationError(f"{prefix}source_sha256:MISMATCH")
        source_coordinate = _require_str(row, "source_coordinate", prefix=prefix)
        if source_coordinate != source["coordinate"]:
            raise QualificationError(f"{prefix}source_coordinate:MISMATCH")

        claim = _require_str(row, "claim", prefix=prefix)
        claim_sha = _validate_sha(row.get("claim_sha256"), f"{prefix}claim_sha256")
        if sha256_bytes(claim.encode("utf-8")) != claim_sha:
            raise QualificationError(f"{prefix}claim_sha256:MISMATCH")

        reuse_semantics = _require_str(row, "reuse_semantics", prefix=prefix)
        if len(requirement_ids) == 1:
            if reuse_semantics != "SINGLE_REQUIREMENT":
                raise QualificationError(f"{prefix}reuse_semantics:INVALID_SINGLE")
        else:
            if reuse_semantics != "EXPLICIT_SAME_CATEGORY":
                raise QualificationError(f"{prefix}reuse_semantics:NOT_EXPLICIT")
            if any(not requirement["allow_shared_evidence"] for requirement in requirement_rows):
                raise QualificationError(f"{prefix}reuse_semantics:REUSE_NOT_ALLOWED")

        normalized = {
            "id": evidence_id,
            "subject_id": subject_id,
            "requirement_ids": sorted(requirement_ids),
            "category": category,
            "source_id": source_id,
            "source_sha256": source_sha,
            "source_coordinate": source_coordinate,
            "claim": claim,
            "claim_sha256": claim_sha,
            "reuse_semantics": reuse_semantics,
        }
        binding = _validate_sha(row.get("binding_sha256"), f"{prefix}binding_sha256")
        if binding != _evidence_binding(normalized):
            raise QualificationError(f"{prefix}binding_sha256:MISMATCH")
        normalized["binding_sha256"] = binding
        record_by_id[evidence_id] = normalized

    return {"sources": source_by_id, "records": record_by_id}


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return (
            json.dumps(self.payload, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")


def _base_payload(
    *,
    state: str,
    trusted_as_of: datetime,
    source_info: dict[str, Any],
    trusted: dict[str, Any],
    manifest: dict[str, Any],
    authority_mode: str,
    missing_requirements: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    age_seconds = int(
        (trusted_as_of.astimezone(timezone.utc) - source_info["checked_at"]).total_seconds()
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "route": manifest["route"],
        "subject_id": manifest["subject_id"],
        "state": state,
        "authority_mode": authority_mode,
        "trusted_as_of": _utc_text(trusted_as_of),
        "source_age_seconds": age_seconds,
        "source_ledger_sha256": trusted["source_sha256"],
        "trusted_root_commitment_sha256": trusted["commitment_sha256"],
        "tender_pack_acquired": source_info["pack_acquired"],
        "tender_pack_reviewed": source_info["pack_reviewed"],
        "tender_pack_sha256": source_info["pack_declared_sha256"],
        "partner_prime_confirmed": manifest["partner_prime_confirmed"],
        "missing_required_requirements": missing_requirements or [],
        "authority": "INTERNAL_QUALIFICATION_ONLY",
        "tender_submission_authorized": False,
    }


def evaluate(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    trusted_root: dict[str, Any],
    *,
    trusted_as_of: datetime,
    tender_pack_bytes: bytes | None = None,
    extraction_raw: bytes | None = None,
    evidence_raw: bytes | None = None,
) -> Evaluation:
    if trusted_as_of.tzinfo is None:
        raise QualificationError("trusted_as_of:TIMEZONE_REQUIRED")
    trusted_as_of = trusted_as_of.astimezone(timezone.utc)
    source_info = validate_source(source, tender_pack_bytes=tender_pack_bytes)
    trusted = validate_trusted_root(
        trusted_root,
        source_raw=source_raw,
        source_info=source_info,
        trusted_as_of=trusted_as_of,
    )
    manifest_info = validate_manifest(manifest)

    age_seconds = int((trusted_as_of - source_info["checked_at"]).total_seconds())
    if age_seconds < 0:
        raise QualificationError("SOURCE_CHECK_IN_FUTURE")
    if trusted_as_of > trusted["response_deadline"]:
        state = "HOLD_DEADLINE_PASSED"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    if age_seconds > trusted["max_source_age_seconds"]:
        state = "HOLD_SOURCE_STALE"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    if not source_info["pack_acquired"]:
        state = "HOLD_TENDER_PACK_REQUIRED"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    if tender_pack_bytes is None:
        state = "HOLD_TENDER_PACK_FILE_REQUIRED"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    if not source_info["pack_reviewed"]:
        state = "HOLD_TENDER_PACK_REVIEW"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    if source_info["pack_actual_sha256"] != trusted["tender_pack_sha256"]:
        raise QualificationError("TENDER_PACK_BYTES_ROOT_MISMATCH")
    if extraction_raw is None:
        state = "HOLD_TRUSTED_EXTRACTION_REQUIRED"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)
    if evidence_raw is None:
        state = "HOLD_TRUSTED_EVIDENCE_REQUIRED"
        payload = _base_payload(
            state=state,
            trusted_as_of=trusted_as_of,
            source_info=source_info,
            trusted=trusted,
            manifest=manifest_info,
            authority_mode="CURRENT_TRUSTED_UTC",
        )
        return Evaluation(state, 3, payload)

    extraction = validate_extraction(
        extraction_raw,
        trusted=trusted,
        source_info=source_info,
        trusted_as_of=trusted_as_of,
    )
    evidence = validate_evidence_bundle(
        evidence_raw,
        trusted=trusted,
        extraction=extraction,
    )

    unknown_claims = set(manifest_info["claims"]) - set(extraction["requirements"])
    if unknown_claims:
        raise QualificationError(
            "MANIFEST_CLAIMS_UNKNOWN_REQUIREMENTS:" + ",".join(sorted(unknown_claims))
        )

    missing_requirements: list[dict[str, str]] = []
    used_evidence: dict[str, str] = {}
    for requirement_id, requirement in sorted(extraction["requirements"].items()):
        if (
            not requirement["mandatory"]
            or manifest_info["route"] not in requirement["applies_to_routes"]
        ):
            continue
        claim = manifest_info["claims"].get(requirement_id)
        if claim is None:
            missing_requirements.append(
                {"requirement_id": requirement_id, "status": "UNDECLARED"}
            )
            continue
        if claim["status"] == "PARTNER_CURABLE" and requirement["cure"] != "PARTNER_ALLOWED":
            raise QualificationError(f"claim.{requirement_id}:PARTNER_CURE_NOT_ALLOWED")
        if claim["status"] != "PROVEN":
            missing_requirements.append(
                {"requirement_id": requirement_id, "status": claim["status"]}
            )
            continue

        for evidence_id in claim["evidence_ids"]:
            record = evidence["records"].get(evidence_id)
            if record is None:
                raise QualificationError(
                    f"claim.{requirement_id}:UNKNOWN_EVIDENCE:{evidence_id}"
                )
            if record["subject_id"] != manifest_info["subject_id"]:
                raise QualificationError(
                    f"claim.{requirement_id}:EVIDENCE_SUBJECT_MISMATCH:{evidence_id}"
                )
            if requirement_id not in record["requirement_ids"]:
                raise QualificationError(
                    f"claim.{requirement_id}:EVIDENCE_REQUIREMENT_MISMATCH:{evidence_id}"
                )
            if record["category"] != requirement["category"]:
                raise QualificationError(
                    f"claim.{requirement_id}:EVIDENCE_CATEGORY_MISMATCH:{evidence_id}"
                )
            previous_requirement = used_evidence.get(evidence_id)
            if previous_requirement and previous_requirement != requirement_id:
                if record["reuse_semantics"] != "EXPLICIT_SAME_CATEGORY":
                    raise QualificationError(
                        f"claim.{requirement_id}:IMPLICIT_CROSS_GATE_REUSE:{evidence_id}"
                    )
            used_evidence[evidence_id] = requirement_id

    if missing_requirements:
        state = "HOLD_EVIDENCE_GAPS"
    elif (
        manifest_info["route"] in TEAMING_ROUTES
        and not manifest_info["partner_prime_confirmed"]
    ):
        state = "HOLD_PARTNER_REQUIRED"
    else:
        state = "READY_FOR_OWNER_TENDER_REVIEW"

    payload = _base_payload(
        state=state,
        trusted_as_of=trusted_as_of,
        source_info=source_info,
        trusted=trusted,
        manifest=manifest_info,
        authority_mode="CURRENT_TRUSTED_UTC",
        missing_requirements=missing_requirements,
    )
    payload["extraction_sha256"] = trusted["extraction_sha256"]
    payload["evidence_bundle_sha256"] = trusted["evidence_bundle_sha256"]
    payload["inventory_count"] = extraction["inventory_count"]
    payload["requirement_count"] = extraction["requirement_count"]
    payload["inventory_set_sha256"] = extraction["inventory_set_sha256"]
    payload["requirement_set_sha256"] = extraction["requirement_set_sha256"]
    return Evaluation(
        state,
        0 if state == "READY_FOR_OWNER_TENDER_REVIEW" else 3,
        payload,
    )


def evaluate_historical(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    trusted_root: dict[str, Any],
    *,
    replay_as_of: datetime,
    tender_pack_bytes: bytes | None = None,
    extraction_raw: bytes | None = None,
    evidence_raw: bytes | None = None,
) -> Evaluation:
    result = evaluate(
        manifest,
        source,
        source_raw,
        trusted_root,
        trusted_as_of=replay_as_of,
        tender_pack_bytes=tender_pack_bytes,
        extraction_raw=extraction_raw,
        evidence_raw=evidence_raw,
    )
    payload = dict(result.payload)
    payload["authority_mode"] = "HISTORICAL_REPLAY_ONLY"
    payload["tender_submission_authorized"] = False
    state = result.state
    if state == "READY_FOR_OWNER_TENDER_REVIEW":
        state = "HISTORICAL_REPLAY_READY_NOT_CURRENT_AUTHORITY"
        payload["state"] = state
    return Evaluation(state, 3, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--source-ledger",
        type=Path,
        default=Path(__file__).with_name("sources.json"),
    )
    parser.add_argument("--tender-pack", type=Path, default=None)
    parser.add_argument("--extraction", type=Path, default=None)
    parser.add_argument("--evidence", type=Path, default=None)
    parser.add_argument(
        "--historical-as-of",
        type=str,
        default=None,
        help="explicit replay mode only; never emits current READY authority",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        source_raw = args.source_ledger.read_bytes()
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_bytes(args.manifest.read_bytes(), "manifest")
        trusted_root_path = Path(__file__).with_name("trusted_root.json")
        trusted_root = load_json_bytes(trusted_root_path.read_bytes(), "trusted_root")
        pack_bytes = args.tender_pack.read_bytes() if args.tender_pack else None
        extraction_raw = args.extraction.read_bytes() if args.extraction else None
        evidence_raw = args.evidence.read_bytes() if args.evidence else None

        if args.historical_as_of is None:
            result = evaluate(
                manifest,
                source,
                source_raw,
                trusted_root,
                trusted_as_of=datetime.now(timezone.utc),
                tender_pack_bytes=pack_bytes,
                extraction_raw=extraction_raw,
                evidence_raw=evidence_raw,
            )
        else:
            replay_as_of = _parse_dt(args.historical_as_of, "historical_as_of")
            result = evaluate_historical(
                manifest,
                source,
                source_raw,
                trusted_root,
                replay_as_of=replay_as_of,
                tender_pack_bytes=pack_bytes,
                extraction_raw=extraction_raw,
                evidence_raw=evidence_raw,
            )
    except (OSError, QualificationError) as exc:
        payload = {
            "state": "INVALID_INPUT",
            "error": str(exc),
            "authority": "INTERNAL_QUALIFICATION_ONLY",
            "tender_submission_authorized": False,
        }
        sys.stderr.write(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        )
        return 2

    encoded = result.bytes()
    if args.output:
        args.output.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
