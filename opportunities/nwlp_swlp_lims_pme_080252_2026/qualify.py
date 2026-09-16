#!/usr/bin/env python3
"""Fail-closed qualification engine for FTS 080252-2026.

Current commercial readiness uses verifier-owned UTC and independently retained
trust roots. Buyer questionnaire bytes are necessary but never sufficient for a
READY state. Historical integrity checking is a separate, non-readiness mode.
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

# Production trust roots are intentionally empty until reviewed authority packets
# are committed in a separate change. A caller cannot mint current READY merely
# by supplying self-authored authority JSON. Tests patch these sets with exact
# synthetic digests to exercise the positive path.
TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256: frozenset[str] = frozenset()
TRUSTED_EVIDENCE_AUTHORITY_SHA256: frozenset[str] = frozenset()
TRUSTED_PARTNER_AUTHORITY_SHA256: frozenset[str] = frozenset()


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


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_str(obj: dict[str, Any], key: str, *, nonempty: bool = True) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or (nonempty and not value.strip()):
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
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"{label}:INVALID_DATETIME") from exc
    if parsed.tzinfo is None:
        raise QualificationError(f"{label}:TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise QualificationError(f"{label}:INVALID_SHA256")
    return value


def _require_exact_keys(obj: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - obj.keys()
    extra = obj.keys() - expected
    if missing:
        raise QualificationError(f"{label}:MISSING_KEYS:" + ",".join(sorted(missing)))
    if extra:
        raise QualificationError(f"{label}:UNKNOWN_KEYS:" + ",".join(sorted(extra)))


def _normalize_now(now: datetime | None) -> datetime:
    value = now if now is not None else datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise QualificationError("verifier_now:TIMEZONE_REQUIRED")
    return value.astimezone(timezone.utc)


def _trusted_digest(raw: bytes, trusted: frozenset[str], label: str) -> str:
    digest = sha256_bytes(raw)
    if digest not in trusted:
        raise QualificationError(f"{label}:UNTRUSTED_SHA256:{digest}")
    return digest


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
    # Retained only as caller metadata. Current readiness NEVER uses this clock.
    caller_evaluated_at = _parse_dt(_require_str(manifest, "evaluated_at"), "manifest.evaluated_at")
    caller_partner_prime_confirmed = _require_bool(manifest, "partner_prime_confirmed")

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise QualificationError("manifest.authority:MUST_BE_OBJECT")
    _require_exact_keys(authority, FORBIDDEN_AUTHORITY_FLAGS, "manifest.authority")
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
        if len(set(refs)) != len(refs):
            raise QualificationError(f"capability.{name}:DUPLICATE_EVIDENCE_REF")
        if status == "PROVEN" and not refs:
            raise QualificationError(f"capability.{name}:PROVEN_REQUIRES_EVIDENCE")
        normalized[name] = {"status": status, "evidence_refs": list(refs)}

    return {
        "route": route,
        "caller_evaluated_at": caller_evaluated_at,
        "caller_partner_prime_confirmed": caller_partner_prime_confirmed,
        "capabilities": normalized,
        "source_sha256": actual_source_sha,
    }


def validate_questionnaire_authority(
    raw: bytes,
    *,
    source_raw: bytes,
    questionnaire_bytes: bytes,
    now: datetime,
) -> dict[str, Any]:
    digest = _trusted_digest(raw, TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256, "questionnaire_authority")
    obj = load_json_bytes(raw, "questionnaire_authority")
    if _require_int(obj, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("questionnaire_authority.schema_version:UNSUPPORTED")
    if _require_str(obj, "kind") != "questionnaire_extraction":
        raise QualificationError("questionnaire_authority.kind:MISMATCH")
    if _require_str(obj, "notice_id") != NOTICE_ID:
        raise QualificationError("questionnaire_authority.notice_id:MISMATCH")
    if _require_str(obj, "atamis_contract_reference") != ATAMIS_REF:
        raise QualificationError("questionnaire_authority.atamis_contract_reference:MISMATCH")
    if _validate_sha(obj.get("source_ledger_sha256"), "questionnaire_authority.source_ledger_sha256") != sha256_bytes(source_raw):
        raise QualificationError("QUESTIONNAIRE_AUTHORITY_SOURCE_REPLAY")
    if _validate_sha(obj.get("questionnaire_sha256"), "questionnaire_authority.questionnaire_sha256") != sha256_bytes(questionnaire_bytes):
        raise QualificationError("QUESTIONNAIRE_AUTHORITY_BYTES_MISMATCH")
    _require_str(obj, "extraction_id")
    _require_str(obj, "document_version")
    extracted_at = _parse_dt(_require_str(obj, "extracted_at"), "questionnaire_authority.extracted_at")
    if extracted_at > now:
        raise QualificationError("questionnaire_authority.extracted_at:IN_FUTURE")
    if not _require_bool(obj, "complete_addenda_set"):
        raise QualificationError("QUESTIONNAIRE_AUTHORITY_ADDENDA_INCOMPLETE")
    addenda = obj.get("addenda")
    if not isinstance(addenda, list):
        raise QualificationError("questionnaire_authority.addenda:MUST_BE_LIST")
    seen_addenda: set[str] = set()
    for index, item in enumerate(addenda):
        if not isinstance(item, dict):
            raise QualificationError(f"questionnaire_authority.addenda[{index}]:MUST_BE_OBJECT")
        aid = _require_str(item, "id")
        _validate_sha(item.get("sha256"), f"questionnaire_authority.addenda[{index}].sha256")
        if aid in seen_addenda:
            raise QualificationError("questionnaire_authority.addenda:DUPLICATE_ID")
        seen_addenda.add(aid)

    universe = obj.get("required_gates_by_route")
    if not isinstance(universe, dict):
        raise QualificationError("questionnaire_authority.required_gates_by_route:MUST_BE_OBJECT")
    if set(universe) != set(ROUTES):
        raise QualificationError("QUESTIONNAIRE_AUTHORITY_ROUTE_UNIVERSE_INCOMPLETE")
    normalized_universe: dict[str, tuple[str, ...]] = {}
    for route, baseline in ROUTES.items():
        gates = universe.get(route)
        if not isinstance(gates, list) or any(not isinstance(g, str) or not g for g in gates):
            raise QualificationError(f"questionnaire_authority.required_gates_by_route.{route}:INVALID")
        if len(set(gates)) != len(gates):
            raise QualificationError(f"questionnaire_authority.required_gates_by_route.{route}:DUPLICATE")
        missing_baseline = set(baseline) - set(gates)
        if missing_baseline:
            raise QualificationError("QUESTIONNAIRE_AUTHORITY_GATE_UNIVERSE_SHRINK:" + ",".join(sorted(missing_baseline)))
        normalized_universe[route] = tuple(gates)
    return {"sha256": digest, "required_gates_by_route": normalized_universe, "extraction_id": obj["extraction_id"]}


def validate_evidence_authority(
    raw: bytes,
    *,
    source_raw: bytes,
    questionnaire_authority_sha256: str,
    now: datetime,
) -> dict[str, Any]:
    digest = _trusted_digest(raw, TRUSTED_EVIDENCE_AUTHORITY_SHA256, "evidence_authority")
    obj = load_json_bytes(raw, "evidence_authority")
    if _require_int(obj, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("evidence_authority.schema_version:UNSUPPORTED")
    if _require_str(obj, "kind") != "capability_evidence":
        raise QualificationError("evidence_authority.kind:MISMATCH")
    if _require_str(obj, "notice_id") != NOTICE_ID:
        raise QualificationError("evidence_authority.notice_id:MISMATCH")
    if _validate_sha(obj.get("source_ledger_sha256"), "evidence_authority.source_ledger_sha256") != sha256_bytes(source_raw):
        raise QualificationError("EVIDENCE_AUTHORITY_SOURCE_REPLAY")
    if _validate_sha(obj.get("questionnaire_authority_sha256"), "evidence_authority.questionnaire_authority_sha256") != questionnaire_authority_sha256:
        raise QualificationError("EVIDENCE_AUTHORITY_QUESTIONNAIRE_REPLAY")
    generation = _require_str(obj, "generation")
    issued_at = _parse_dt(_require_str(obj, "issued_at"), "evidence_authority.issued_at")
    valid_until = _parse_dt(_require_str(obj, "valid_until"), "evidence_authority.valid_until")
    if issued_at > now:
        raise QualificationError("evidence_authority.issued_at:IN_FUTURE")
    if valid_until <= now:
        raise QualificationError("EVIDENCE_AUTHORITY_EXPIRED")
    claims = obj.get("claims")
    if not isinstance(claims, list) or not claims:
        raise QualificationError("evidence_authority.claims:MUST_BE_NONEMPTY_LIST")
    by_id: dict[str, dict[str, Any]] = {}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise QualificationError(f"evidence_authority.claims[{index}]:MUST_BE_OBJECT")
        evidence_id = _require_str(claim, "evidence_id")
        capability = _require_str(claim, "capability")
        kind = _require_str(claim, "evidence_kind")
        artifact_sha = _validate_sha(claim.get("artifact_sha256"), f"evidence_authority.claims[{index}].artifact_sha256")
        routes = claim.get("routes")
        if not isinstance(routes, list) or not routes or any(route not in ROUTES for route in routes):
            raise QualificationError(f"evidence_authority.claims[{index}].routes:INVALID")
        if len(set(routes)) != len(routes):
            raise QualificationError(f"evidence_authority.claims[{index}].routes:DUPLICATE")
        if evidence_id in by_id:
            raise QualificationError("evidence_authority.claims:DUPLICATE_EVIDENCE_ID")
        by_id[evidence_id] = {
            "capability": capability,
            "evidence_kind": kind,
            "artifact_sha256": artifact_sha,
            "routes": frozenset(routes),
        }
    return {"sha256": digest, "generation": generation, "claims": by_id}


def validate_partner_authority(
    raw: bytes,
    *,
    route: str,
    questionnaire_authority_sha256: str,
    evidence_generation: str,
    now: datetime,
) -> dict[str, Any]:
    digest = _trusted_digest(raw, TRUSTED_PARTNER_AUTHORITY_SHA256, "partner_authority")
    obj = load_json_bytes(raw, "partner_authority")
    if _require_int(obj, "schema_version", minimum=1) != SCHEMA_VERSION:
        raise QualificationError("partner_authority.schema_version:UNSUPPORTED")
    if _require_str(obj, "kind") != "partner_prime":
        raise QualificationError("partner_authority.kind:MISMATCH")
    if _require_str(obj, "notice_id") != NOTICE_ID:
        raise QualificationError("partner_authority.notice_id:MISMATCH")
    if _require_str(obj, "atamis_contract_reference") != ATAMIS_REF:
        raise QualificationError("partner_authority.atamis_contract_reference:MISMATCH")
    if _require_str(obj, "route") != route:
        raise QualificationError("PARTNER_AUTHORITY_ROUTE_REPLAY")
    if route not in TEAMING_ROUTES:
        raise QualificationError("partner_authority:NOT_APPLICABLE_TO_ROUTE")
    if not _require_bool(obj, "qualified_prime"):
        raise QualificationError("PARTNER_AUTHORITY_NOT_QUALIFIED")
    partner_id = _require_str(obj, "partner_id")
    if _validate_sha(obj.get("questionnaire_authority_sha256"), "partner_authority.questionnaire_authority_sha256") != questionnaire_authority_sha256:
        raise QualificationError("PARTNER_AUTHORITY_QUESTIONNAIRE_REPLAY")
    if _require_str(obj, "evidence_generation") != evidence_generation:
        raise QualificationError("PARTNER_AUTHORITY_EVIDENCE_GENERATION_REPLAY")
    _validate_sha(obj.get("proof_sha256"), "partner_authority.proof_sha256")
    valid_from = _parse_dt(_require_str(obj, "valid_from"), "partner_authority.valid_from")
    valid_until = _parse_dt(_require_str(obj, "valid_until"), "partner_authority.valid_until")
    if not (valid_from <= now < valid_until):
        raise QualificationError("PARTNER_AUTHORITY_OUTSIDE_VALIDITY")
    return {"sha256": digest, "partner_id": partner_id}


def _evaluate_capabilities(
    *,
    route: str,
    manifest_capabilities: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    evidence_claims: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    used_evidence: dict[str, str] = {}
    for capability, record in manifest_capabilities.items():
        if record["status"] != "PROVEN":
            continue
        for evidence_id in record["evidence_refs"]:
            claim = evidence_claims.get(evidence_id)
            if claim is None:
                raise QualificationError(f"EVIDENCE_REF_UNTRUSTED:{evidence_id}")
            if claim["capability"] != capability:
                raise QualificationError(f"EVIDENCE_CAPABILITY_MISMATCH:{evidence_id}:{capability}")
            if route not in claim["routes"]:
                raise QualificationError(f"EVIDENCE_ROUTE_MISMATCH:{evidence_id}:{route}")
            prior = used_evidence.get(evidence_id)
            if prior is not None and prior != capability:
                raise QualificationError(f"EVIDENCE_TRANSPLANT:{evidence_id}:{prior}:{capability}")
            used_evidence[evidence_id] = capability

    for gate in required:
        record = manifest_capabilities.get(gate)
        if record is None:
            missing.append({"gate": gate, "status": "UNDECLARED"})
        elif record["status"] != "PROVEN":
            missing.append({"gate": gate, "status": record["status"]})
        elif not record["evidence_refs"]:
            missing.append({"gate": gate, "status": "PROVEN_WITHOUT_TRUSTED_REF"})
    return missing


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return canonical_bytes(self.payload)


def evaluate(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    questionnaire_bytes: bytes | None = None,
    questionnaire_authority_raw: bytes | None = None,
    evidence_authority_raw: bytes | None = None,
    partner_authority_raw: bytes | None = None,
    now: datetime | None = None,
) -> Evaluation:
    verifier_now = _normalize_now(now)
    source_state = validate_source_ledger(source, questionnaire_bytes=questionnaire_bytes)
    manifest_state = validate_manifest(manifest, source_raw)

    if source_state["checked_at"] > verifier_now:
        raise QualificationError("source.checked_at:IN_FUTURE")
    source_age_days = int((verifier_now - source_state["checked_at"]).total_seconds() // 86400)
    route = manifest_state["route"]

    base_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "ocid": OCID,
        "atamis_contract_reference": ATAMIS_REF,
        "route": route,
        "source_age_days": source_age_days,
        "source_ledger_sha256": manifest_state["source_sha256"],
        "questionnaire_acquired": source_state["questionnaire_acquired"],
        "questionnaire_reviewed": source_state["questionnaire_reviewed"],
        "questionnaire_sha256": source_state["questionnaire_declared_sha256"],
        "caller_partner_prime_confirmed": manifest_state["caller_partner_prime_confirmed"],
        "partner_prime_confirmed": False,
        "authority": "INTERNAL_QUALIFICATION_ONLY",
        "buyer_submission_authorized": False,
        "evaluated_at": verifier_now.isoformat().replace("+00:00", "Z"),
        "caller_evaluated_at": manifest_state["caller_evaluated_at"].isoformat().replace("+00:00", "Z"),
        "questionnaire_authority_sha256": None,
        "evidence_authority_sha256": None,
        "partner_authority_sha256": None,
        "evidence_generation": None,
        "missing_required_capabilities": [],
    }

    def hold(state: str) -> Evaluation:
        payload = dict(base_payload)
        payload["state"] = state
        return Evaluation(state, 3, payload)

    if verifier_now >= source_state["deadline"]:
        return hold("HOLD_DEADLINE_PASSED")
    if source_age_days > MAX_SOURCE_AGE_DAYS:
        return hold("HOLD_SOURCE_STALE")
    if not source_state["questionnaire_acquired"]:
        return hold("HOLD_QUESTIONNAIRE_REQUIRED")
    if questionnaire_bytes is None:
        return hold("HOLD_QUESTIONNAIRE_FILE_REQUIRED")
    if not source_state["questionnaire_reviewed"]:
        return hold("HOLD_QUESTIONNAIRE_REVIEW")
    if questionnaire_authority_raw is None:
        return hold("HOLD_QUESTIONNAIRE_AUTHORITY_REQUIRED")

    qauth = validate_questionnaire_authority(
        questionnaire_authority_raw,
        source_raw=source_raw,
        questionnaire_bytes=questionnaire_bytes,
        now=verifier_now,
    )
    base_payload["questionnaire_authority_sha256"] = qauth["sha256"]

    if evidence_authority_raw is None:
        return hold("HOLD_EVIDENCE_AUTHORITY_REQUIRED")
    eauth = validate_evidence_authority(
        evidence_authority_raw,
        source_raw=source_raw,
        questionnaire_authority_sha256=qauth["sha256"],
        now=verifier_now,
    )
    base_payload["evidence_authority_sha256"] = eauth["sha256"]
    base_payload["evidence_generation"] = eauth["generation"]

    required = qauth["required_gates_by_route"][route]
    missing = _evaluate_capabilities(
        route=route,
        manifest_capabilities=manifest_state["capabilities"],
        required=required,
        evidence_claims=eauth["claims"],
    )
    base_payload["missing_required_capabilities"] = missing
    if missing:
        return hold("HOLD_EVIDENCE_GAPS")

    if route in TEAMING_ROUTES:
        if partner_authority_raw is None:
            return hold("HOLD_PARTNER_AUTHORITY_REQUIRED")
        pauth = validate_partner_authority(
            partner_authority_raw,
            route=route,
            questionnaire_authority_sha256=qauth["sha256"],
            evidence_generation=eauth["generation"],
            now=verifier_now,
        )
        base_payload["partner_authority_sha256"] = pauth["sha256"]
        base_payload["partner_prime_confirmed"] = True
        base_payload["partner_id"] = pauth["partner_id"]

    payload = dict(base_payload)
    payload["state"] = "READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW"
    return Evaluation("READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW", 0, payload)


def historical_integrity(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    questionnaire_bytes: bytes | None = None,
) -> Evaluation:
    source_state = validate_source_ledger(source, questionnaire_bytes=questionnaire_bytes)
    manifest_state = validate_manifest(manifest, source_raw)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "notice_id": NOTICE_ID,
        "state": "HISTORICAL_INTEGRITY_VERIFIED",
        "commercial_readiness": False,
        "buyer_submission_authorized": False,
        "source_ledger_sha256": manifest_state["source_sha256"],
        "questionnaire_sha256": source_state["questionnaire_declared_sha256"],
        "note": "Integrity mode does not evaluate current deadline, freshness, evidence, partner, or submission readiness.",
    }
    return Evaluation("HISTORICAL_INTEGRITY_VERIFIED", 0, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source-ledger", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument("--questionnaire", type=Path, default=None)
    parser.add_argument("--questionnaire-authority", type=Path, default=None)
    parser.add_argument("--evidence-authority", type=Path, default=None)
    parser.add_argument("--partner-authority", type=Path, default=None)
    parser.add_argument("--historical-integrity-only", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        source_raw = args.source_ledger.read_bytes()
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_path(args.manifest, "manifest")
        questionnaire_bytes = args.questionnaire.read_bytes() if args.questionnaire else None
        if args.historical_integrity_only:
            result = historical_integrity(manifest, source, source_raw, questionnaire_bytes=questionnaire_bytes)
        else:
            result = evaluate(
                manifest,
                source,
                source_raw,
                questionnaire_bytes=questionnaire_bytes,
                questionnaire_authority_raw=args.questionnaire_authority.read_bytes() if args.questionnaire_authority else None,
                evidence_authority_raw=args.evidence_authority.read_bytes() if args.evidence_authority else None,
                partner_authority_raw=args.partner_authority.read_bytes() if args.partner_authority else None,
            )
    except (OSError, QualificationError) as exc:
        payload = {"state": "INVALID_INPUT", "error": str(exc), "buyer_submission_authorized": False}
        sys.stderr.buffer.write(canonical_bytes(payload))
        return 2

    encoded = result.bytes()
    if args.output:
        args.output.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
