from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "tjlabs.ttuhsc-739-sl3821039-qualification/v1"
DEADLINE = datetime(2026, 9, 21, 21, 30, 0, tzinfo=timezone.utc)


class QualificationError(ValueError):
    pass


def _strict_object_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    value = json.loads(raw, object_pairs_hook=_strict_object_pairs)
    if type(value) is not dict:
        raise QualificationError("packet must be a JSON object")
    return value


def _dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise QualificationError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise QualificationError(f"{label} must be an array")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationError(f"{label} must be a boolean")
    return value


def _str(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise QualificationError(f"{label} must be a {'string' if allow_empty else 'non-empty string'}")
    return value


def _utc(value: Any, label: str) -> datetime:
    text = _str(value, label)
    if not text.endswith("Z"):
        raise QualificationError(f"{label} must use UTC Z form")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise QualificationError(f"{label} invalid timestamp") from exc
    if parsed.microsecond:
        raise QualificationError(f"{label} must use whole seconds")
    return parsed.astimezone(timezone.utc)


def _exact_keys(obj: dict[str, Any], expected: set[str], label: str) -> None:
    if set(obj) != expected:
        raise QualificationError(f"{label} keys invalid")


def evaluate(packet: dict[str, Any]) -> dict[str, Any]:
    packet = _dict(packet, "packet")
    _exact_keys(packet, {
        "schema", "as_of", "source", "organization", "proposal",
        "references", "team", "security", "commercial", "route"
    }, "packet")
    if packet["schema"] != SCHEMA:
        raise QualificationError("unsupported schema")

    as_of = _utc(packet["as_of"], "as_of")
    route = _str(packet["route"], "route")
    if route not in {"PRIME", "TEAM"}:
        raise QualificationError("route must be PRIME or TEAM")

    if as_of >= DEADLINE:
        return {
            "schema": SCHEMA,
            "decision": "NO_BID",
            "reason_codes": ["PROPOSAL_DEADLINE_EXPIRED"],
            "external_submission_authorized": False,
        }

    reasons: list[str] = []

    source = _dict(packet["source"], "source")
    _exact_keys(source, {
        "first_party_event_observed_at", "first_party_event_open",
        "first_party_packet_bytes_retained", "all_addenda_retained",
        "packet_mirror_only"
    }, "source")
    observed = _utc(source["first_party_event_observed_at"], "source.first_party_event_observed_at")
    if observed > as_of:
        reasons.append("SOURCE_OBSERVATION_FROM_FUTURE")
    if not _bool(source["first_party_event_open"], "source.first_party_event_open"):
        reasons.append("FIRST_PARTY_EVENT_NOT_OPEN")
    if not _bool(source["first_party_packet_bytes_retained"], "source.first_party_packet_bytes_retained"):
        reasons.append("FIRST_PARTY_PACKET_BYTES_MISSING")
    if not _bool(source["all_addenda_retained"], "source.all_addenda_retained"):
        reasons.append("ADDENDA_GENERATION_INCOMPLETE")
    if _bool(source["packet_mirror_only"], "source.packet_mirror_only"):
        reasons.append("MIRROR_ONLY_SOURCE_CANNOT_AUTHORIZE")

    org = _dict(packet["organization"], "organization")
    _exact_keys(org, {
        "legal_entity", "texas_comptroller_current", "franchise_tax_evidence",
        "vet_hub_plan_complete", "execution_of_offer_signed",
        "addenda_checklist_signed", "insurance_evidence",
        "prohibited_entity_certifications_reviewed"
    }, "organization")
    if not _str(org["legal_entity"], "organization.legal_entity", allow_empty=True).strip():
        reasons.append("LEGAL_ENTITY_MISSING")
    bool_reasons = {
        "texas_comptroller_current": "TEXAS_COMPTROLLER_STATUS_NOT_PROVEN",
        "franchise_tax_evidence": "FRANCHISE_TAX_EVIDENCE_MISSING",
        "vet_hub_plan_complete": "VETHUB_PLAN_INCOMPLETE",
        "execution_of_offer_signed": "EXECUTION_OF_OFFER_UNSIGNED",
        "addenda_checklist_signed": "ADDENDA_CHECKLIST_UNSIGNED",
        "insurance_evidence": "INSURANCE_EVIDENCE_MISSING",
        "prohibited_entity_certifications_reviewed": "PROHIBITED_ENTITY_CERTIFICATION_NOT_REVIEWED",
    }
    for key, reason in bool_reasons.items():
        if not _bool(org[key], f"organization.{key}"):
            reasons.append(reason)

    refs = _list(packet["references"], "references")
    ref_ids = set()
    valid_refs = 0
    for raw in refs:
        row = _dict(raw, "reference row")
        _exact_keys(row, {
            "reference_id", "similar_scope", "current_or_recent",
            "reachable_contact", "entity_type"
        }, "reference row")
        ref_id = _str(row["reference_id"], "reference.reference_id")
        if ref_id in ref_ids:
            reasons.append("DUPLICATE_REFERENCE_ID")
        ref_ids.add(ref_id)
        entity_type = _str(row["entity_type"], "reference.entity_type")
        if entity_type not in {"PRIME", "TEAMING_PARTNER", "SUBCONSULTANT"}:
            raise QualificationError("reference.entity_type invalid")
        if (
            _bool(row["similar_scope"], "reference.similar_scope")
            and _bool(row["current_or_recent"], "reference.current_or_recent")
            and _bool(row["reachable_contact"], "reference.reachable_contact")
        ):
            valid_refs += 1
    if valid_refs < 3:
        reasons.append("THREE_VALID_REFERENCES_REQUIRED")

    team = _dict(packet["team"], "team")
    _exact_keys(team, {
        "project_lead_named", "team_qualifications_evidenced",
        "time_commitments_defined", "subconsultants_identified_if_used",
        "delivery_capacity_for_six_deliverables"
    }, "team")
    for key, reason in {
        "project_lead_named": "PROJECT_LEAD_MISSING",
        "team_qualifications_evidenced": "TEAM_QUALIFICATIONS_NOT_EVIDENCED",
        "time_commitments_defined": "TEAM_TIME_COMMITMENTS_MISSING",
        "subconsultants_identified_if_used": "SUBCONSULTANT_DISCLOSURE_INCOMPLETE",
        "delivery_capacity_for_six_deliverables": "DELIVERY_CAPACITY_NOT_EVIDENCED",
    }.items():
        if not _bool(team[key], f"team.{key}"):
            reasons.append(reason)

    security = _dict(packet["security"], "security")
    _exact_keys(security, {
        "tx_ramp_status_resolved", "hipaa_ferpa_boundary_reviewed",
        "institutional_data_no_training", "rbac", "sso",
        "tls_1_3", "aes_256_at_rest", "unsupported_compliance_claims_absent"
    }, "security")
    for key, reason in {
        "tx_ramp_status_resolved": "TX_RAMP_STATUS_UNRESOLVED",
        "hipaa_ferpa_boundary_reviewed": "HIPAA_FERPA_BOUNDARY_UNRESOLVED",
        "institutional_data_no_training": "INSTITUTIONAL_DATA_TRAINING_PROHIBITION_NOT_BOUND",
        "rbac": "RBAC_CONTROL_MISSING",
        "sso": "SSO_CONTROL_MISSING",
        "tls_1_3": "TLS_1_3_CONTROL_MISSING",
        "aes_256_at_rest": "AES_256_AT_REST_CONTROL_MISSING",
        "unsupported_compliance_claims_absent": "UNSUPPORTED_COMPLIANCE_CLAIM_PRESENT",
    }.items():
        if not _bool(security[key], f"security.{key}"):
            reasons.append(reason)

    proposal = _dict(packet["proposal"], "proposal")
    _exact_keys(proposal, {
        "section_5_response_complete", "scope_of_work_exhibit_a_complete",
        "project_schedule_complete", "pricing_schedule_signed",
        "techbid_package_complete", "proposal_valid_90_days",
        "all_six_deliverables_covered", "oral_presentation_ready"
    }, "proposal")
    for key, reason in {
        "section_5_response_complete": "SECTION_5_RESPONSE_INCOMPLETE",
        "scope_of_work_exhibit_a_complete": "EXHIBIT_A_SCOPE_MISSING",
        "project_schedule_complete": "PROJECT_SCHEDULE_MISSING",
        "pricing_schedule_signed": "PRICING_SCHEDULE_UNSIGNED",
        "techbid_package_complete": "TECHBID_PACKAGE_INCOMPLETE",
        "proposal_valid_90_days": "NINETY_DAY_VALIDITY_MISSING",
        "all_six_deliverables_covered": "SIX_DELIVERABLE_COVERAGE_INCOMPLETE",
        "oral_presentation_ready": "ORAL_PRESENTATION_READINESS_MISSING",
    }.items():
        if not _bool(proposal[key], f"proposal.{key}"):
            reasons.append(reason)

    commercial = _dict(packet["commercial"], "commercial")
    _exact_keys(commercial, {
        "fixed_fee_nte_present", "loe_schedule_present",
        "rate_card_present_through_2027_08_31",
        "final_price_owner_approved", "contract_exceptions_reviewed"
    }, "commercial")
    for key, reason in {
        "fixed_fee_nte_present": "FIXED_FEE_NTE_MISSING",
        "loe_schedule_present": "LEVEL_OF_EFFORT_SCHEDULE_MISSING",
        "rate_card_present_through_2027_08_31": "RATE_CARD_MISSING",
        "final_price_owner_approved": "FINAL_PRICE_NOT_OWNER_APPROVED",
        "contract_exceptions_reviewed": "CONTRACT_EXCEPTIONS_NOT_REVIEWED",
    }.items():
        if not _bool(commercial[key], f"commercial.{key}"):
            reasons.append(reason)

    if route == "PRIME":
        if any(
            _dict(raw, "reference row").get("entity_type") in {"TEAMING_PARTNER", "SUBCONSULTANT"}
            for raw in refs
        ):
            reasons.append("PRIME_ROUTE_DEPENDS_ON_NON_PRIME_REFERENCE")
    else:
        if not any(
            _dict(raw, "reference row").get("entity_type") in {"TEAMING_PARTNER", "SUBCONSULTANT"}
            for raw in refs
        ):
            reasons.append("TEAM_ROUTE_HAS_NO_TEAM_REFERENCE")

    decision = "HOLD" if reasons else ("PRIME_READY" if route == "PRIME" else "TEAMING_READY")
    return {
        "schema": SCHEMA,
        "decision": decision,
        "reason_codes": sorted(set(reasons)),
        "valid_reference_count": valid_refs,
        "external_submission_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TTUHSC 739-SL3821039 internal qualification gate")
    parser.add_argument("packet")
    args = parser.parse_args(argv)
    result = evaluate(load_json(args.packet))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["decision"] in {"PRIME_READY", "TEAMING_READY"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
