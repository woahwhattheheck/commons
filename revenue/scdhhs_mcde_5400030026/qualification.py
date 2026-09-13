"""Fail-closed qualification compiler for SCDHHS solicitation 5400030026.

The repository-owned source contract is the trust root.  Candidate packets can
provide evidence, but cannot lower thresholds, replace Amendment 1, authorize a
submission, or convert subcontractor experience into a claim that the offeror
itself satisfies an offeror-specific mandatory minimum.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
HERE = Path(__file__).resolve().parent
SOURCE_CONTRACT = json.loads((HERE / "source_contract.json").read_text(encoding="utf-8"))
OPERATION_KEY = SOURCE_CONTRACT["operation_key"]
ROUTES = {"prime_offeror", "subcontractor_to_qualified_prime"}


class QualificationError(ValueError):
    """Malformed or ambiguous evidence packet."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise QualificationError(f"value is not canonical finite JSON: {exc}") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def source_contract_sha256() -> str:
    return _sha256(SOURCE_CONTRACT)


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualificationError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise QualificationError(f"{path} must be an array")
    return value


def _str(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise QualificationError(f"{path} must be a string")
    if nonempty and not value.strip():
        raise QualificationError(f"{path} must not be empty")
    return value.strip() if nonempty else value


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise QualificationError(f"{path} must be a boolean")
    return value


def _int(value: Any, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise QualificationError(f"{path} must be an integer")
    if value < minimum:
        raise QualificationError(f"{path} must be >= {minimum}")
    return value


def _evidence_refs(value: Any, path: str) -> list[str]:
    refs = _list(value, path)
    out = [_str(item, f"{path}[{index}]") for index, item in enumerate(refs)]
    if len(set(out)) != len(out):
        raise QualificationError(f"{path} contains duplicate references")
    return out


def _validate_source_observation(observed: Any) -> tuple[bool, list[str]]:
    """Compare a human/tool capture of the official index to the repo trust root."""
    obs = _mapping(observed, "source_observation")
    reasons: list[str] = []

    if obs.get("solicitation_number") != SOURCE_CONTRACT["solicitation"]["number"]:
        reasons.append("SOURCE_SOLICITATION_MISMATCH")

    observed_count = _int(obs.get("attachment_count"), "source_observation.attachment_count")
    observed_attachments = _list(obs.get("attachments"), "source_observation.attachments")
    if observed_count != len(observed_attachments):
        reasons.append("SOURCE_OBSERVATION_COUNT_INCONSISTENT")

    normalized: list[dict[str, str]] = []
    names: list[str] = []
    for i, raw in enumerate(observed_attachments):
        item = _mapping(raw, f"source_observation.attachments[{i}]")
        name = _str(item.get("name"), f"source_observation.attachments[{i}].name")
        posted = _str(item.get("posted_at"), f"source_observation.attachments[{i}].posted_at")
        normalized.append({"name": name, "posted_at": posted})
        names.append(name)
    if len(names) != len(set(names)):
        reasons.append("SOURCE_DUPLICATE_ATTACHMENT_NAME")

    trusted = SOURCE_CONTRACT["attachment_manifest"]
    if observed_count != len(trusted) or normalized != trusted:
        reasons.append("SOURCE_ATTACHMENT_MANIFEST_MISMATCH")

    controlling = _mapping(obs.get("controlling_document"), "source_observation.controlling_document")
    expected_control = SOURCE_CONTRACT["controlling_document"]
    if (
        controlling.get("name") != expected_control["name"]
        or controlling.get("posted_at") != expected_control["posted_at"]
    ):
        reasons.append("SOURCE_CONTROLLING_DOCUMENT_MISMATCH")

    return not reasons, sorted(set(reasons))


def _validate_entity_evidence(entities: Any) -> list[dict[str, Any]]:
    rows = _list(entities, "offeror.similar_healthcare_entities")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(rows):
        item = _mapping(raw, f"offeror.similar_healthcare_entities[{i}]")
        name = _str(item.get("entity_name"), f"offeror.similar_healthcare_entities[{i}].entity_name")
        key = name.casefold()
        if key in seen:
            raise QualificationError("offeror.similar_healthcare_entities must be distinct")
        seen.add(key)
        out.append(
            {
                "entity_name": name,
                "as_prime_contractor": _bool(
                    item.get("as_prime_contractor"),
                    f"offeror.similar_healthcare_entities[{i}].as_prime_contractor",
                ),
                "similar_size_scope": _bool(
                    item.get("similar_size_scope"),
                    f"offeror.similar_healthcare_entities[{i}].similar_size_scope",
                ),
                "evidence_refs": _evidence_refs(
                    item.get("evidence_refs"),
                    f"offeror.similar_healthcare_entities[{i}].evidence_refs",
                ),
            }
        )
    return out


def _validate_million_life_implementations(items: Any) -> list[dict[str, Any]]:
    rows = _list(items, "offeror.adt_implementations")
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        item = _mapping(raw, f"offeror.adt_implementations[{i}]")
        out.append(
            {
                "environment": _str(item.get("environment"), f"offeror.adt_implementations[{i}].environment"),
                "covered_lives": _int(
                    item.get("covered_lives"),
                    f"offeror.adt_implementations[{i}].covered_lives",
                ),
                "successful": _bool(
                    item.get("successful"),
                    f"offeror.adt_implementations[{i}].successful",
                ),
                "evidence_refs": _evidence_refs(
                    item.get("evidence_refs"),
                    f"offeror.adt_implementations[{i}].evidence_refs",
                ),
            }
        )
    return out


def _validate_subcontractors(items: Any) -> tuple[list[dict[str, Any]], list[str]]:
    rows = _list(items, "subcontractors")
    out: list[dict[str, Any]] = []
    reasons: list[str] = []
    for i, raw in enumerate(rows):
        item = _mapping(raw, f"subcontractors[{i}]")
        cost_share = _int(item.get("cost_share_percent"), f"subcontractors[{i}].cost_share_percent")
        if cost_share > 100:
            raise QualificationError(f"subcontractors[{i}].cost_share_percent must be <= 100")
        government_access = _bool(
            item.get("government_information_access"),
            f"subcontractors[{i}].government_information_access",
        )
        critical = _bool(item.get("critical_services"), f"subcontractors[{i}].critical_services")
        identification_complete = _bool(
            item.get("identification_complete"),
            f"subcontractors[{i}].identification_complete",
        )
        relationship_explained = _bool(
            item.get("relationship_explained"),
            f"subcontractors[{i}].relationship_explained",
        )
        evidence_refs = _evidence_refs(item.get("evidence_refs"), f"subcontractors[{i}].evidence_refs")
        record = {
            "business_name": _str(item.get("business_name"), f"subcontractors[{i}].business_name"),
            "scope": _str(item.get("scope"), f"subcontractors[{i}].scope"),
            "cost_share_percent": cost_share,
            "government_information_access": government_access,
            "critical_services": critical,
            "identification_complete": identification_complete,
            "relationship_explained": relationship_explained,
            "evidence_refs": evidence_refs,
        }
        must_identify = cost_share > 10 or government_access or critical
        if must_identify and not identification_complete:
            reasons.append("SUBCONTRACTOR_IDENTIFICATION_INCOMPLETE")
        # Amendment 1 §5.2 requires the relationship explanation when the
        # offeror asks the State to consider a subcontractor's qualifications.
        if evidence_refs and not relationship_explained:
            reasons.append("SUBCONTRACTOR_RELATIONSHIP_UNEXPLAINED")
        out.append(record)
    return out, sorted(set(reasons))


def _validate_security(readiness: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    obj = _mapping(readiness, "proposal_readiness.security_controls")
    required = SOURCE_CONTRACT["proposal_readiness"]["security_controls"]
    extra = sorted(set(obj) - set(required))
    if extra:
        raise QualificationError(f"unknown security controls: {', '.join(extra)}")
    normalized: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for key in required:
        item = _mapping(obj.get(key), f"proposal_readiness.security_controls.{key}")
        ready = _bool(item.get("ready"), f"proposal_readiness.security_controls.{key}.ready")
        refs = _evidence_refs(
            item.get("evidence_refs"),
            f"proposal_readiness.security_controls.{key}.evidence_refs",
        )
        normalized[key] = {"ready": ready, "evidence_refs": refs}
        if not ready or not refs:
            missing.append(f"READINESS_SECURITY_{key.upper()}")
    return normalized, missing


def compile_qualification(packet: Any, *, source_observation: Any) -> dict[str, Any]:
    """Compile evidence into a deterministic, non-authoritative qualification receipt."""
    packet = _mapping(packet, "packet")
    route = _str(packet.get("route"), "packet.route")
    if route not in ROUTES:
        raise QualificationError(f"packet.route must be one of {sorted(ROUTES)}")

    # These fields are intentionally ignored for policy authority, but bound by packet digest.
    # A candidate may carry notes/threshold guesses without ever altering repository minima.
    offeror = _mapping(packet.get("offeror"), "packet.offeror")
    legal_name = _str(offeror.get("legal_name"), "offeror.legal_name")
    prime_months = _int(offeror.get("prime_contractor_months"), "offeror.prime_contractor_months")
    prime_experience_refs = _evidence_refs(
        offeror.get("prime_experience_evidence_refs"),
        "offeror.prime_experience_evidence_refs",
    )
    adt_months = _int(offeror.get("realtime_adt_months"), "offeror.realtime_adt_months")
    healthcare_adt_months = _int(offeror.get("healthcare_adt_months"), "offeror.healthcare_adt_months")
    adt_experience_refs = _evidence_refs(
        offeror.get("adt_experience_evidence_refs"),
        "offeror.adt_experience_evidence_refs",
    )
    entities = _validate_entity_evidence(offeror.get("similar_healthcare_entities"))
    implementations = _validate_million_life_implementations(offeror.get("adt_implementations"))
    subcontractors, subcontractor_reasons = _validate_subcontractors(packet.get("subcontractors"))

    readiness = _mapping(packet.get("proposal_readiness"), "packet.proposal_readiness")
    pm_mcde = _int(readiness.get("project_manager_mcde_months"), "proposal_readiness.project_manager_mcde_months")
    pm_health = _int(
        readiness.get("project_manager_healthcare_months"),
        "proposal_readiness.project_manager_healthcare_months",
    )
    pm_evidence_refs = _evidence_refs(
        readiness.get("project_manager_evidence_refs"),
        "proposal_readiness.project_manager_evidence_refs",
    )
    security, security_reasons = _validate_security(readiness.get("security_controls"))

    source_current, source_reasons = _validate_source_observation(source_observation)
    minimums = SOURCE_CONTRACT["mandatory_minimums"]
    mandatory_reasons: list[str] = []

    qualifying_entities = [
        row
        for row in entities
        if row["as_prime_contractor"] and row["similar_size_scope"] and row["evidence_refs"]
    ]
    successful_million_life = [
        row
        for row in implementations
        if row["successful"]
        and row["covered_lives"] >= minimums["successful_adt_min_lives"]
        and row["evidence_refs"]
    ]

    if prime_months < minimums["prime_contractor_months"] or not prime_experience_refs:
        mandatory_reasons.append("MANDATORY_PRIME_CONTRACTOR_EXPERIENCE")
    if len(qualifying_entities) < minimums["similar_size_scope_healthcare_entities"]:
        mandatory_reasons.append("MANDATORY_THREE_SIMILAR_HEALTHCARE_ENTITIES")
    if adt_months < minimums["realtime_adt_months"] or not adt_experience_refs:
        mandatory_reasons.append("MANDATORY_REALTIME_ADT_EXPERIENCE")
    if healthcare_adt_months < minimums["healthcare_adt_months"] or not adt_experience_refs:
        mandatory_reasons.append("MANDATORY_HEALTHCARE_ADT_EXPERIENCE")
    if not successful_million_life:
        mandatory_reasons.append("MANDATORY_SUCCESSFUL_ONE_MILLION_LIVES_ADT")

    readiness_reasons: list[str] = list(subcontractor_reasons) + list(security_reasons)
    if (
        pm_mcde < SOURCE_CONTRACT["proposal_readiness"]["project_manager_mcde_months"]
        or not pm_evidence_refs
    ):
        readiness_reasons.append("READINESS_PROJECT_MANAGER_MCDE_EXPERIENCE")
    if (
        pm_health < SOURCE_CONTRACT["proposal_readiness"]["project_manager_healthcare_months"]
        or not pm_evidence_refs
    ):
        readiness_reasons.append("READINESS_PROJECT_MANAGER_HEALTHCARE_EXPERIENCE")

    prime_qualified = False
    teaming_prime_name: str | None = None
    if source_reasons:
        decision = "HOLD_SOURCE_NOT_CURRENT"
        reasons = source_reasons
    elif route == "prime_offeror" and mandatory_reasons:
        decision = "PRIME_NO_GO_MANDATORY_EXPERIENCE"
        reasons = sorted(set(mandatory_reasons))
    elif route == "prime_offeror" and readiness_reasons:
        decision = "HOLD_PROPOSAL_READINESS"
        reasons = sorted(set(readiness_reasons))
    elif route == "prime_offeror":
        # This is an internal evidence result, not State qualification or authority to bid.
        decision = "PRIME_QUALIFICATION_CANDIDATE"
        reasons = []
        prime_qualified = True
    else:
        teaming = _mapping(packet.get("teaming"), "packet.teaming")
        teaming_prime_name = _str(teaming.get("qualified_prime_legal_name"), "teaming.qualified_prime_legal_name")
        relationship = _bool(teaming.get("relationship_explained"), "teaming.relationship_explained")
        prime_refs = _evidence_refs(
            teaming.get("prime_qualification_evidence_refs"),
            "teaming.prime_qualification_evidence_refs",
        )
        if not relationship or not prime_refs:
            decision = "TEAMING_DISCOVERY"
            reasons = ["TEAMING_PRIME_EVIDENCE_OR_RELATIONSHIP_INCOMPLETE"]
        else:
            decision = "TEAM_AS_SUBCONTRACTOR"
            reasons = sorted(set(subcontractor_reasons))
            if subcontractor_reasons:
                decision = "TEAMING_DISCOVERY"
        # Deliberately never infer that this offeror meets prime-offeror minima from
        # a partner's qualifications.
        prime_qualified = False

    result = {
        "schema_version": SCHEMA_VERSION,
        "operation_key": OPERATION_KEY,
        "route": route,
        "offeror_legal_name": legal_name,
        "teaming_prime_legal_name": teaming_prime_name,
        "source_contract_sha256": source_contract_sha256(),
        "source_observation_sha256": _sha256(source_observation),
        "packet_sha256": _sha256(packet),
        "source_current": source_current,
        "decision": decision,
        "reasons": reasons,
        "prime_qualification_candidate": prime_qualified,
        "submission_authorized": False,
        "authority": dict(SOURCE_CONTRACT["authority"]),
        "evidence_summary": {
            "qualifying_similar_healthcare_entities": len(qualifying_entities),
            "successful_million_life_adt_implementations": len(successful_million_life),
            "subcontractor_count": len(subcontractors),
            "security_controls_ready": sum(
                1 for value in security.values() if value["ready"] and value["evidence_refs"]
            ),
            "security_controls_required": len(security),
        },
    }
    receipt_basis = dict(result)
    result["receipt_sha256"] = _sha256(receipt_basis)
    return result


def verify_receipt(packet: Any, *, source_observation: Any, receipt: Any) -> bool:
    """Byte-exact verification: any changed evidence, source capture, or result fails."""
    try:
        expected = compile_qualification(packet, source_observation=source_observation)
        return _canonical(expected) == _canonical(receipt)
    except (QualificationError, TypeError, ValueError):
        return False
