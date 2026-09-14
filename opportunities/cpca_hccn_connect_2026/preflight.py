#!/usr/bin/env python3
"""Fail-closed CPCA HCCN Connect qualification gate; never submits or certifies."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "cpca.hccn.source_snapshot/v1"
OWNER_SCHEMA = "cpca.hccn.owner_inputs/v1"
RECEIPT_SCHEMA = "cpca.hccn.preflight_receipt/v1"
READY = "READY_FOR_OWNER_SUBMISSION_REVIEW"
HOLD = "HOLD"
SOURCE_REFRESH = "SOURCE_REFRESH_REQUIRED"
DEADLINE_PASSED = "DEADLINE_PASSED"
MAX_SOURCE_AGE = timedelta(days=7)
SERVICE_TYPES = {"technical_assistance", "group_training"}
SAFETY_NET_TYPES = {
    "federally_qualified_health_center",
    "health_center_program_look_alike",
    "primary_care_association_or_hccn",
    "safety_net_primary_care_organization_or_network",
}
PLACEHOLDER = re.compile(r"(?:OWNER_INPUT_REQUIRED|\bTBD\b|\bTODO\b|<[^>]+>)", re.I)
AUTHORITY = {
    key: False
    for key in (
        "external_submission_authorized",
        "external_contact_authorized",
        "qualification_assertion_authorized",
        "healthcare_experience_assertion_authorized",
        "reference_contact_authorized",
        "pricing_commitment_authorized",
        "legal_or_compliance_certification_authorized",
        "contract_or_signature_authorized",
        "award_or_revenue_claim_authorized",
    )
}


class PreflightError(ValueError):
    pass


def _bad_number(value: str) -> None:
    raise PreflightError(f"non-finite JSON number {value!r} is forbidden")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PreflightError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError(f"{label} must be UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_number)
    except PreflightError:
        raise
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical_bytes(value)).hexdigest()


def parse_utc(text: str, label: str) -> datetime:
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        raise PreflightError(f"{label} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PreflightError(f"{label} is not a valid UTC timestamp") from exc


def parse_rfc3339(text: str, label: str) -> datetime:
    if not isinstance(text, str):
        raise PreflightError(f"{label} must be a timestamp")
    try:
        value = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PreflightError(f"{label} is invalid RFC3339") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise PreflightError(f"{label} must include a timezone offset")
    return value


def trusted_time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PreflightError("trusted_now must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.search(value)


def _placeholders(value: Any, path: str = "owner") -> list[str]:
    if isinstance(value, str):
        return [path] if PLACEHOLDER.search(value) else []
    if isinstance(value, dict):
        result: list[str] = []
        for key, child in value.items():
            result.extend(_placeholders(child, f"{path}.{key}"))
        return result
    if isinstance(value, list):
        result = []
        for index, child in enumerate(value):
            result.extend(_placeholders(child, f"{path}[{index}]"))
        return result
    return []


def validate_source(source: dict[str, Any]) -> None:
    if source.get("schema") != SOURCE_SCHEMA:
        raise PreflightError("unsupported source schema")
    if source.get("buyer") != "California Primary Care Association" or source.get("program") != "CPCA HCCN Connect":
        raise PreflightError("source identity mismatch")
    packet = source.get("buyer_packet")
    if not isinstance(packet, dict):
        raise PreflightError("buyer_packet must be an object")
    if packet.get("pages") != 16 or packet.get("bytes") != 222280:
        raise PreflightError("buyer packet byte/page identity mismatch")
    sha = packet.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise PreflightError("buyer packet sha256 malformed")
    if sha != "37c61b76500fee4639e1499d7683d4882da294f65d77e5e59c224ada3fc52529":
        raise PreflightError("buyer packet sha256 mismatch")
    if packet.get("public_packet_bytes_committed") is not False:
        raise PreflightError("source must preserve no-public-packet-bytes boundary")
    parse_utc(source.get("checked_at"), "source.checked_at")
    parse_rfc3339(source.get("proposal_due_at"), "source.proposal_due_at")
    domains = source.get("domains")
    if not isinstance(domains, dict) or set(domains) != {
        "data_management_analytics",
        "data_sharing_interoperability",
        "uds_plus_implementation",
        "value_based_care",
        "artificial_intelligence",
    }:
        raise PreflightError("source domains malformed")
    if not all(isinstance(v, list) and v and all(_text(x) for x in v) for v in domains.values()):
        raise PreflightError("source domain topics malformed")
    if set(source.get("service_types", [])) != SERVICE_TYPES:
        raise PreflightError("source service_types malformed")
    marketplace = source.get("marketplace")
    if not isinstance(marketplace, dict) or marketplace.get("guaranteed_referrals_or_volume") is not False:
        raise PreflightError("source must preserve no-guaranteed-volume statement")
    weights = source.get("evaluation_weights_percent")
    if not isinstance(weights, dict) or sum(weights.values()) != 100:
        raise PreflightError("evaluation weights must total 100")
    authority = source.get("authority")
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        raise PreflightError("source authority must remain entirely false")


def validate_owner(owner: dict[str, Any]) -> None:
    if owner.get("schema") != OWNER_SCHEMA:
        raise PreflightError("unsupported owner schema")
    required_types = {
        "organization": dict,
        "selected_routes": list,
        "comparable_engagements": list,
        "safety_net_engagements": list,
        "technical_assistance_evidence": list,
        "group_training_evidence": list,
        "personnel": list,
        "subcontractors": list,
        "references": list,
        "work_samples": list,
        "regulatory_knowledge": dict,
        "cultural_competency": dict,
        "delivery_capacity": dict,
        "licensing_compliance": dict,
        "privacy_contracting": dict,
        "pricing": dict,
        "appendix_c": dict,
        "packaging": dict,
    }
    for key, expected in required_types.items():
        if not isinstance(owner.get(key), expected):
            raise PreflightError(f"owner.{key} must be {expected.__name__}")


def _route_key(route: dict[str, Any]) -> tuple[str, str] | None:
    domain = route.get("domain")
    service_type = route.get("service_type")
    if not isinstance(domain, str) or not isinstance(service_type, str):
        return None
    return domain, service_type


def _engagement_domain_rows(owner: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    rows = []
    for row in owner["comparable_engagements"]:
        if isinstance(row, dict) and domain in row.get("domains", []):
            rows.append(row)
    return rows


def _iso_date(text: Any, label: str, blockers: list[str]) -> datetime | None:
    if not isinstance(text, str):
        blockers.append(f"{label}_DATE_REQUIRED")
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        blockers.append(f"{label}_DATE_INVALID")
        return None


def evaluate(source: dict[str, Any], owner: dict[str, Any], *, trusted_now: datetime) -> dict[str, Any]:
    validate_source(source)
    validate_owner(owner)
    now = trusted_time(trusted_now)
    checked = parse_utc(source["checked_at"], "source.checked_at")
    due = parse_rfc3339(source["proposal_due_at"], "source.proposal_due_at").astimezone(timezone.utc)
    if checked > now:
        raise PreflightError("source checked_at cannot be in the future")

    blockers: list[str] = []
    warnings: list[str] = []
    state = HOLD
    if now - checked > MAX_SOURCE_AGE:
        state = SOURCE_REFRESH
        blockers.append("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS")
    if now > due:
        state = DEADLINE_PASSED
        blockers.append("PROPOSAL_DEADLINE_PASSED")

    placeholders = _placeholders(owner)
    if placeholders:
        blockers.append("PLACEHOLDERS_REMAIN:" + ",".join(sorted(placeholders)))

    org = owner["organization"]
    for key in ("legal_name", "website", "point_of_contact_name", "point_of_contact_title", "point_of_contact_email"):
        if not _text(org.get(key)):
            blockers.append(f"ORGANIZATION_{key.upper()}_REQUIRED")

    routes = owner["selected_routes"]
    if not routes:
        blockers.append("SELECT_AT_LEAST_ONE_DOMAIN_SERVICE_ROUTE")
    route_keys: list[tuple[str, str]] = []
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            blockers.append(f"ROUTE_{index}_MALFORMED")
            continue
        key = _route_key(route)
        if key is None:
            blockers.append(f"ROUTE_{index}_MALFORMED")
            continue
        domain, service_type = key
        route_keys.append(key)
        if domain not in source["domains"]:
            blockers.append(f"ROUTE_{index}_UNKNOWN_DOMAIN:{domain}")
        if service_type not in SERVICE_TYPES:
            blockers.append(f"ROUTE_{index}_UNKNOWN_SERVICE_TYPE:{service_type}")
        topics = route.get("topics")
        if not isinstance(topics, list) or not topics or not all(_text(x) for x in topics):
            blockers.append(f"ROUTE_{index}_TOPICS_REQUIRED")
        elif domain in source["domains"]:
            unknown_topics = sorted(set(topics) - set(source["domains"][domain]))
            if unknown_topics:
                blockers.append(f"ROUTE_{index}_UNKNOWN_TOPICS:" + ",".join(unknown_topics))
    if len(route_keys) != len(set(route_keys)):
        blockers.append("DUPLICATE_DOMAIN_SERVICE_ROUTE")

    selected_domains = sorted({d for d, _ in route_keys if d in source["domains"]})
    selected_services = {s for _, s in route_keys if s in SERVICE_TYPES}

    # Every selected domain needs one qualifying safety-net engagement.
    safety_net_by_domain: dict[str, int] = {domain: 0 for domain in selected_domains}
    for index, row in enumerate(owner["safety_net_engagements"]):
        if not isinstance(row, dict):
            blockers.append(f"SAFETY_NET_{index}_MALFORMED")
            continue
        required = ("engagement_id", "client_type", "scope", "evidence_ref", "personnel_names")
        if not all(_text(row.get(k)) for k in required[:-1]) or not isinstance(row.get("personnel_names"), list) or not row["personnel_names"]:
            blockers.append(f"SAFETY_NET_{index}_INCOMPLETE")
            continue
        if row.get("client_type") not in SAFETY_NET_TYPES:
            blockers.append(f"SAFETY_NET_{index}_CLIENT_TYPE_NOT_QUALIFYING")
            continue
        domains = row.get("domains")
        if not isinstance(domains, list) or not domains:
            blockers.append(f"SAFETY_NET_{index}_DOMAINS_REQUIRED")
            continue
        for domain in domains:
            if domain in safety_net_by_domain:
                safety_net_by_domain[domain] += 1
    for domain, count in safety_net_by_domain.items():
        if count < 1:
            blockers.append(f"SAFETY_NET_EXPERIENCE_REQUIRED:{domain}")

    # Comparable engagement minimums by domain.
    established = set(source["experience_rules"]["established_domains"]["domain_ids"])
    emerging = set(source["experience_rules"]["emerging_domains"]["domain_ids"])
    for domain in selected_domains:
        rows = _engagement_domain_rows(owner, domain)
        complete_rows = []
        for index, row in enumerate(rows):
            required = ("engagement_id", "status", "start_date", "end_date", "client_description", "scope", "deliverables", "evidence_ref")
            if not all(_text(row.get(k)) for k in required):
                blockers.append(f"COMPARABLE_{domain}_{index}_INCOMPLETE")
                continue
            if not isinstance(row.get("personnel_names"), list) or not row["personnel_names"]:
                blockers.append(f"COMPARABLE_{domain}_{index}_PERSONNEL_REQUIRED")
                continue
            complete_rows.append(row)
        if domain in established:
            cutoff = now - timedelta(days=365 * 3)
            qualifying = 0
            for index, row in enumerate(complete_rows):
                end = _iso_date(row.get("end_date"), f"COMPARABLE_{domain}_{index}_END", blockers)
                if row.get("status") == "completed" and end is not None and end >= cutoff:
                    qualifying += 1
            if qualifying < 3:
                blockers.append(f"ESTABLISHED_DOMAIN_THREE_RECENT_COMPLETED_REQUIRED:{domain}:{qualifying}/3")
        elif domain in emerging:
            cutoff = now - timedelta(days=365 * 2)
            recent_completed = 0
            total_relevant = 0
            for index, row in enumerate(complete_rows):
                status = row.get("status")
                if status in {"completed", "substantially_completed", "active", "pilot"}:
                    total_relevant += 1
                end = _iso_date(row.get("end_date"), f"COMPARABLE_{domain}_{index}_END", blockers)
                if status in {"completed", "substantially_completed"} and end is not None and end >= cutoff:
                    recent_completed += 1
            if recent_completed < 1:
                blockers.append(f"EMERGING_DOMAIN_RECENT_COMPLETED_REQUIRED:{domain}")
            if total_relevant < 2:
                blockers.append(f"EMERGING_DOMAIN_TWO_ENGAGEMENTS_REQUIRED:{domain}:{total_relevant}/2")

    if "technical_assistance" in selected_services:
        valid_ta = [row for row in owner["technical_assistance_evidence"] if isinstance(row, dict) and all(_text(row.get(k)) for k in ("engagement_id", "individualized_support", "deliverables", "evidence_ref"))]
        if not valid_ta:
            blockers.append("TECHNICAL_ASSISTANCE_COMPARABLE_EVIDENCE_REQUIRED")
    if "group_training" in selected_services:
        valid_gt = [row for row in owner["group_training_evidence"] if isinstance(row, dict) and all(_text(row.get(k)) for k in ("engagement_id", "curriculum", "learning_objectives", "facilitation", "evaluation", "evidence_ref"))]
        if not valid_gt:
            blockers.append("GROUP_TRAINING_COMPARABLE_EVIDENCE_REQUIRED")

    # People and evidence.
    if not owner["personnel"]:
        blockers.append("PROPOSED_PERSONNEL_REQUIRED")
    for index, row in enumerate(owner["personnel"]):
        if not isinstance(row, dict) or not all(_text(row.get(k)) for k in ("name", "role", "qualifications", "years_experience", "evidence_ref")):
            blockers.append(f"PERSONNEL_{index}_INCOMPLETE")
    for index, row in enumerate(owner["subcontractors"]):
        if not isinstance(row, dict) or not all(_text(row.get(k)) for k in ("organization", "scope", "qualification_evidence_ref")):
            blockers.append(f"SUBCONTRACTOR_{index}_INCOMPLETE")

    if len(owner["references"]) < 3:
        blockers.append("THREE_CLIENT_REFERENCES_REQUIRED")
    reference_ids = []
    for index, row in enumerate(owner["references"]):
        if not isinstance(row, dict) or not all(_text(row.get(k)) for k in ("reference_id", "organization", "relationship", "private_contact_plan")):
            blockers.append(f"REFERENCE_{index}_INCOMPLETE")
        else:
            reference_ids.append(row["reference_id"])
    if len(reference_ids) != len(set(reference_ids)):
        blockers.append("REFERENCE_IDS_MUST_BE_UNIQUE")

    if not owner["work_samples"]:
        blockers.append("RELEVANT_WORK_SAMPLE_REQUIRED")
    for index, row in enumerate(owner["work_samples"]):
        if not isinstance(row, dict) or not all(_text(row.get(k)) for k in ("title", "domain", "evidence_ref")):
            blockers.append(f"WORK_SAMPLE_{index}_INCOMPLETE")

    reg = owner["regulatory_knowledge"]
    for domain in selected_domains:
        value = reg.get(domain)
        if not isinstance(value, dict) or not _text(value.get("narrative")) or not _text(value.get("evidence_ref")):
            blockers.append(f"REGULATORY_STANDARDS_EVIDENCE_REQUIRED:{domain}")

    cultural = owner["cultural_competency"]
    if not _text(cultural.get("narrative")) or not _text(cultural.get("evidence_ref")):
        blockers.append("CULTURAL_COMPETENCY_EVIDENCE_REQUIRED")

    capacity = owner["delivery_capacity"]
    if capacity.get("virtual_delivery_supported") is not True and not _text(capacity.get("california_presence")):
        blockers.append("VIRTUAL_DELIVERY_OR_CALIFORNIA_PRESENCE_REQUIRED")
    if not _text(capacity.get("concurrent_engagement_capacity")):
        blockers.append("CONCURRENT_ENGAGEMENT_CAPACITY_REQUIRED")
    if not _text(capacity.get("reporting_invoicing_oversight_capability")):
        blockers.append("REPORTING_INVOICING_OVERSIGHT_CAPABILITY_REQUIRED")

    compliance = owner["licensing_compliance"]
    if compliance.get("requirements_reviewed") is not True:
        blockers.append("LICENSING_CERTIFICATION_REQUIREMENTS_REVIEW_REQUIRED")
    if compliance.get("all_required_licenses_certifications_current") is not True:
        blockers.append("REQUIRED_LICENSES_CERTIFICATIONS_NOT_PROVEN")
    if compliance.get("insurance_requirements_reviewed") is not True:
        blockers.append("INSURANCE_REQUIREMENTS_REVIEW_REQUIRED")
    if compliance.get("insurance_supportable") is not True:
        blockers.append("INSURANCE_NOT_PROVEN")
    if not _text(compliance.get("evidence_ref")):
        blockers.append("LICENSING_INSURANCE_EVIDENCE_REQUIRED")

    privacy = owner["privacy_contracting"]
    if privacy.get("baa_obligations_reviewed") is not True:
        blockers.append("BAA_OBLIGATIONS_REVIEW_REQUIRED")
    if not _text(privacy.get("baa_capability")):
        blockers.append("BAA_CAPABILITY_STATUS_REQUIRED")
    if not _text(privacy.get("phi_pii_delivery_boundary")):
        blockers.append("PHI_PII_DELIVERY_BOUNDARY_REQUIRED")

    pricing = owner["pricing"]
    if pricing.get("fully_loaded_basis_reviewed") is not True:
        blockers.append("FULLY_LOADED_RATE_BASIS_REVIEW_REQUIRED")
    if pricing.get("owner_approved") is not True:
        blockers.append("PRICING_OWNER_APPROVAL_REQUIRED")
    if "technical_assistance" in selected_services and not pricing.get("technical_assistance_rates_by_role"):
        blockers.append("TECHNICAL_ASSISTANCE_RATES_REQUIRED")
    if "group_training" in selected_services and not pricing.get("group_training_rates"):
        blockers.append("GROUP_TRAINING_RATES_REQUIRED")

    attestation = owner["appendix_c"]
    if attestation.get("reviewed_by_authorized_human") is not True:
        blockers.append("APPENDIX_C_HUMAN_REVIEW_REQUIRED")
    if attestation.get("signed_by_authorized_human") is not True:
        blockers.append("APPENDIX_C_HUMAN_SIGNATURE_REQUIRED")
    if not _text(attestation.get("authorized_representative_name")):
        blockers.append("AUTHORIZED_REPRESENTATIVE_REQUIRED")
    if not _text(attestation.get("conflict_status")):
        blockers.append("CONFLICT_STATUS_REQUIRED")

    packaging = owner["packaging"]
    if packaging.get("single_pdf_plan_reviewed") is not True:
        blockers.append("SINGLE_PDF_PLAN_REVIEW_REQUIRED")
    if packaging.get("smartsheet_submission_mechanics_reviewed") is not True:
        blockers.append("SMARTSHEET_SUBMISSION_REVIEW_REQUIRED")
    if packaging.get("filename_reviewed") is not True:
        blockers.append("FILENAME_REVIEW_REQUIRED")
    if owner.get("owner_final_review_complete") is not True:
        blockers.append("OWNER_FINAL_REVIEW_REQUIRED")

    blockers = sorted(set(blockers))
    if state not in {SOURCE_REFRESH, DEADLINE_PASSED}:
        state = READY if not blockers else HOLD

    missing_safety = sorted(x for x in blockers if x.startswith("SAFETY_NET_EXPERIENCE_REQUIRED:"))
    missing_comparables = sorted(
        x
        for x in blockers
        if x.startswith("EMERGING_DOMAIN_") or x.startswith("ESTABLISHED_DOMAIN_")
    )
    posture = "DIRECT_PRIME_REVIEWABLE" if state == READY else "HOLD"
    if state == HOLD and (missing_safety or missing_comparables):
        posture = "HOLD_HEALTHCARE_OR_DOMAIN_EXPERIENCE_GAP"

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "state": state,
        "posture": posture,
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_snapshot_sha256": digest(source),
        "owner_input_sha256": digest(owner),
        "buyer_packet_sha256": source["buyer_packet"]["sha256"],
        "selected_routes": routes,
        "selected_domains": selected_domains,
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
        "authority": dict(AUTHORITY),
    }
    receipt["receipt_sha256"] = digest(dict(receipt))
    return receipt


def parse_trusted_now(text: str) -> datetime:
    return parse_utc(text, "trusted-now")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--trusted-now", required=True)
    args = parser.parse_args()
    source = load_json_bytes(Path(args.source).read_bytes(), "source")
    owner = load_json_bytes(Path(args.owner).read_bytes(), "owner")
    receipt = evaluate(source, owner, trusted_now=parse_trusted_now(args.trusted_now))
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
