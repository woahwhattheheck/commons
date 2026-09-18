from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA = "vctc-erp-gms-pursuit/v1"
ASSESSMENT_SCHEMA = "vctc-erp-gms-assessment/v1"
AUTH_SCHEMA = "vctc-source-authority/v1"
SOLICITATION_ID = "VCTC-ERP-GMS-2026-09-14"
TITLE = "Enterprise Resource Planning (ERP) System, Grants Management System, and Implementation Services"
PROPOSAL_DEADLINE = "2026-11-09T15:00:00-08:00"

OFFICIAL_SOURCES = {
    "rfp": {
        "kind": "RFP",
        "url": "https://www.goventura.org/wp-content/uploads/2026/09/RFP-Enterprise-Resource-Planning-System.pdf",
    },
    "appendix_a": {
        "kind": "APPENDIX_A_FUNCTIONAL_REQUIREMENTS",
        "url": "https://www.goventura.org/wp-content/uploads/2026/09/Appendix-A-Functional-Requirements-ERP-091426.xlsx",
    },
    "appendix_b": {
        "kind": "APPENDIX_B_COST_PROPOSAL",
        "url": "https://www.goventura.org/wp-content/uploads/2026/09/Appendix-B-Cost-Proposal-ERP-091426.xlsx",
    },
    "appendix_c": {
        "kind": "APPENDIX_C_PROFESSIONAL_SERVICES_AGREEMENT",
        "url": "https://www.goventura.org/wp-content/uploads/2026/09/Appendix-C-Professional-Services-Agreement-ERP.pdf",
    },
}

REQUIRED_TEAM_GATES = {
    "ERP_OR_GMS_PRODUCT_AUTHORITY",
    "THREE_SIMILAR_PUBLIC_SECTOR_PROJECTS",
    "PUBLIC_SECTOR_REFERENCES",
    "IMPLEMENTATION_LEAD",
    "SUPPORT_MAINTENANCE_MODEL",
    "SHORTLIST_DEMO_READINESS",
    "PHYSICAL_SUBMISSION_OWNER",
    "INSURANCE_BINDABILITY_PLAN",
    "SUBCONTRACT_DISCLOSURE_AND_CONSENT_PLAN",
}

REQUIRED_IMPLEMENTATION_KINDS = {
    "MIGRATION_RECONCILIATION",
    "INTERFACE_REPLAY",
    "REQUIREMENT_UAT_TRACE",
    "EXCEPTION_DISPOSITION",
    "HUMAN_ACCEPTANCE_BOUNDARY",
}

ALLOWED_REQUIREMENT_DOMAINS = {
    "AP", "AR_BILLING", "BUDGET", "COA_GL", "CONTRACTS", "DOCUMENTS",
    "FIXED_ASSETS", "GRANTS", "PAYROLL_TIME", "PROCUREMENT", "PROJECTS",
    "REPORTING", "VENDOR", "WORKFLOW", "TECHNICAL", "IMPLEMENTATION",
    "SUPPORT", "COMMERCIAL", "CONTRACTUAL"
}
ALLOWED_OWNERS = {"ERP_PRIME", "GMS_PARTNER", "TJL", "BUYER", "SHARED"}
RESPONSE_STATES = {"READY", "GAP", "HOLD", "NA_WITH_REASON"}
EVIDENCE_STATES = {"PROVEN", "UNKNOWN", "NOT_APPLICABLE"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{1,79}$")

class ValidationError(ValueError):
    pass


def _require_exact_keys(value: dict[str, Any], keys: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label}: expected object")
    got = set(value)
    if got != keys:
        raise ValidationError(f"{label}: keys mismatch missing={sorted(keys-got)} extra={sorted(got-keys)}")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(text: str, label: str) -> datetime:
    if not isinstance(text, str):
        raise ValidationError(f"{label}: expected string")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label}: invalid ISO-8601") from exc
    if dt.tzinfo is None:
        raise ValidationError(f"{label}: timezone required")
    return dt


def _validate_ref_list(values: Any, label: str) -> None:
    if not isinstance(values, list) or len(values) > 64:
        raise ValidationError(f"{label}: expected bounded list")
    seen = set()
    for item in values:
        if not isinstance(item, str) or not item or len(item) > 240:
            raise ValidationError(f"{label}: invalid ref")
        if item in seen:
            raise ValidationError(f"{label}: duplicate ref {item}")
        seen.add(item)


def validate_sources(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != len(OFFICIAL_SOURCES):
        raise ValidationError("sources: exactly four official source rows required")
    by_id: dict[str, dict[str, Any]] = {}
    keys = {"id", "kind", "url", "retrieved", "current", "sha256", "size_bytes", "issued_date", "supersedes"}
    for row in rows:
        _require_exact_keys(row, keys, "source")
        sid = row["id"]
        if sid not in OFFICIAL_SOURCES or sid in by_id:
            raise ValidationError("source: unknown or duplicate id")
        spec = OFFICIAL_SOURCES[sid]
        if row["kind"] != spec["kind"] or row["url"] != spec["url"]:
            raise ValidationError(f"source {sid}: official identity mismatch")
        if not isinstance(row["retrieved"], bool) or not isinstance(row["current"], bool):
            raise ValidationError(f"source {sid}: retrieved/current must be bool")
        if not _is_int(row["size_bytes"]) or row["size_bytes"] < 0 or row["size_bytes"] > 50_000_000:
            raise ValidationError(f"source {sid}: invalid size")
        if row["retrieved"]:
            if not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"]):
                raise ValidationError(f"source {sid}: retrieved source needs sha256")
            if row["size_bytes"] <= 0:
                raise ValidationError(f"source {sid}: retrieved source needs positive size")
        else:
            if row["sha256"] is not None or row["size_bytes"] != 0 or row["current"]:
                raise ValidationError(f"source {sid}: unretrieved source cannot claim digest/currentness")
        if not isinstance(row["issued_date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["issued_date"]):
            raise ValidationError(f"source {sid}: invalid issued_date")
        _validate_ref_list(row["supersedes"], f"source {sid}.supersedes")
        by_id[sid] = row
    return [by_id[sid] for sid in sorted(OFFICIAL_SOURCES)]


def build_source_authority(source_rows: Any, *, key_id: str, key: bytes, issued_at: str) -> dict[str, Any]:
    sources = validate_sources(source_rows)
    if not isinstance(key_id, str) or not re.fullmatch(r"[a-z0-9_.-]{3,48}", key_id):
        raise ValidationError("authority key_id invalid")
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ValidationError("authority key must be at least 32 bytes")
    _parse_time(issued_at, "authority.issued_at")
    payload = {
        "schema": AUTH_SCHEMA,
        "solicitation_id": SOLICITATION_ID,
        "key_id": key_id,
        "issued_at": issued_at,
        "sources": sources,
    }
    mac = hmac.new(bytes(key), _canonical(payload), hashlib.sha256).hexdigest()
    return {**payload, "mac_sha256": mac}


def verify_source_authority(authority: Any, *, key: bytes, expected_key_id: str) -> list[dict[str, Any]]:
    keys = {"schema", "solicitation_id", "key_id", "issued_at", "sources", "mac_sha256"}
    _require_exact_keys(authority, keys, "authority")
    if authority["schema"] != AUTH_SCHEMA or authority["solicitation_id"] != SOLICITATION_ID:
        raise ValidationError("authority: schema/solicitation mismatch")
    if authority["key_id"] != expected_key_id:
        raise ValidationError("authority: wrong key id")
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ValidationError("authority key must be at least 32 bytes")
    _parse_time(authority["issued_at"], "authority.issued_at")
    sources = validate_sources(authority["sources"])
    mac = authority["mac_sha256"]
    if not isinstance(mac, str) or not HEX64.fullmatch(mac):
        raise ValidationError("authority: invalid MAC")
    payload = {k: authority[k] for k in ["schema", "solicitation_id", "key_id", "issued_at", "sources"]}
    expected = hmac.new(bytes(key), _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        raise ValidationError("authority: MAC mismatch")
    return sources


def _validate_solicitation(value: Any) -> None:
    keys = {"id", "title", "proposal_deadline", "evaluation_points", "submission_mode", "prime_posture"}
    _require_exact_keys(value, keys, "solicitation")
    if value["id"] != SOLICITATION_ID or value["title"] != TITLE or value["proposal_deadline"] != PROPOSAL_DEADLINE:
        raise ValidationError("solicitation: controlling identity mismatch")
    if value["submission_mode"] != "PHYSICAL_PAPER_PLUS_THUMB_DRIVE":
        raise ValidationError("solicitation: submission mode mismatch")
    if value["prime_posture"] != "TEAMING_SPECIALIST_SUBCONTRACT_FIRST":
        raise ValidationError("solicitation: posture mismatch")
    points = value["evaluation_points"]
    expected = {
        "firm_qualifications": 15,
        "proposed_solution": 10,
        "functional_requirements": 20,
        "implementation_approach": 20,
        "support_maintenance": 15,
        "cost": 20,
    }
    if points != expected:
        raise ValidationError("solicitation: evaluation points mismatch")


def _validate_requirements(rows: Any, trusted_sources: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValidationError("requirements: expected bounded list")
    keys = {"id", "source_id", "source_sha256", "domain", "mandatory", "text_fingerprint", "response_state", "owner", "evidence_refs"}
    seen_id = set()
    seen_semantic = set()
    gaps = []
    normalized = []
    for row in rows:
        _require_exact_keys(row, keys, "requirement")
        rid = row["id"]
        if not isinstance(rid, str) or not ID_RE.fullmatch(rid) or rid in seen_id:
            raise ValidationError("requirement: invalid/duplicate id")
        seen_id.add(rid)
        sid = row["source_id"]
        if sid not in trusted_sources:
            raise ValidationError(f"requirement {rid}: unknown source")
        source = trusted_sources[sid]
        if not source["retrieved"] or not source["current"]:
            raise ValidationError(f"requirement {rid}: source not current/retrieved")
        if row["source_sha256"] != source["sha256"]:
            raise ValidationError(f"requirement {rid}: source digest mismatch")
        if row["domain"] not in ALLOWED_REQUIREMENT_DOMAINS:
            raise ValidationError(f"requirement {rid}: invalid domain")
        if not isinstance(row["mandatory"], bool):
            raise ValidationError(f"requirement {rid}: mandatory must be bool")
        if not isinstance(row["text_fingerprint"], str) or not HEX64.fullmatch(row["text_fingerprint"]):
            raise ValidationError(f"requirement {rid}: invalid text fingerprint")
        semantic = (sid, row["text_fingerprint"])
        if semantic in seen_semantic:
            raise ValidationError(f"requirement {rid}: reminted semantic duplicate")
        seen_semantic.add(semantic)
        if row["response_state"] not in RESPONSE_STATES or row["owner"] not in ALLOWED_OWNERS:
            raise ValidationError(f"requirement {rid}: invalid response state/owner")
        _validate_ref_list(row["evidence_refs"], f"requirement {rid}.evidence_refs")
        if row["response_state"] == "READY" and not row["evidence_refs"]:
            raise ValidationError(f"requirement {rid}: READY requires evidence")
        if row["mandatory"] and row["response_state"] != "READY":
            gaps.append(rid)
        normalized.append(row)
    return sorted(normalized, key=lambda x: x["id"]), sorted(gaps)


def _validate_team_gates(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows, list) or len(rows) != len(REQUIRED_TEAM_GATES):
        raise ValidationError("team_gates: exactly required gate set expected")
    keys = {"id", "evidence_state", "evidence_refs", "responsible_party"}
    by_id = {}
    missing = []
    for row in rows:
        _require_exact_keys(row, keys, "team_gate")
        gid = row["id"]
        if gid not in REQUIRED_TEAM_GATES or gid in by_id:
            raise ValidationError("team_gate: unknown/duplicate id")
        if row["evidence_state"] not in EVIDENCE_STATES:
            raise ValidationError(f"team_gate {gid}: bad state")
        if row["responsible_party"] not in {"PRIME", "ERP_OEM", "GMS_PARTNER", "TJL", "OWNER"}:
            raise ValidationError(f"team_gate {gid}: bad party")
        _validate_ref_list(row["evidence_refs"], f"team_gate {gid}.evidence_refs")
        if row["evidence_state"] == "PROVEN" and not row["evidence_refs"]:
            raise ValidationError(f"team_gate {gid}: PROVEN requires evidence")
        if row["evidence_state"] != "PROVEN":
            missing.append(gid)
        by_id[gid] = row
    return [by_id[x] for x in sorted(by_id)], sorted(missing)


def _validate_implementation(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValidationError("implementation_evidence: bounded list expected")
    keys = {"id", "kind", "state", "evidence_refs", "owner"}
    seen_id = set()
    seen_kind = set()
    missing = set(REQUIRED_IMPLEMENTATION_KINDS)
    normalized = []
    for row in rows:
        _require_exact_keys(row, keys, "implementation_evidence")
        if not isinstance(row["id"], str) or not ID_RE.fullmatch(row["id"]) or row["id"] in seen_id:
            raise ValidationError("implementation_evidence: bad/duplicate id")
        seen_id.add(row["id"])
        kind = row["kind"]
        if kind not in REQUIRED_IMPLEMENTATION_KINDS or kind in seen_kind:
            raise ValidationError("implementation_evidence: bad/duplicate kind")
        seen_kind.add(kind)
        if row["state"] not in {"DEFINED", "PROVEN", "HOLD"}:
            raise ValidationError("implementation_evidence: bad state")
        if row["owner"] not in ALLOWED_OWNERS:
            raise ValidationError("implementation_evidence: bad owner")
        _validate_ref_list(row["evidence_refs"], f"implementation {row['id']}.evidence_refs")
        if row["state"] == "PROVEN" and not row["evidence_refs"]:
            raise ValidationError("implementation_evidence: PROVEN requires evidence")
        if row["state"] in {"DEFINED", "PROVEN"}:
            missing.discard(kind)
        normalized.append(row)
    return sorted(normalized, key=lambda x: x["id"]), sorted(missing)


def _validate_commercial(value: Any) -> None:
    keys = {"state", "workshare_minor", "currency", "pricing_authorized", "external_contact_authorized"}
    _require_exact_keys(value, keys, "commercial")
    if value["state"] != "PROPOSED_NOT_ACCEPTED" or value["currency"] != "USD":
        raise ValidationError("commercial: state/currency mismatch")
    if value["workshare_minor"] is not None and (not _is_int(value["workshare_minor"]) or value["workshare_minor"] <= 0):
        raise ValidationError("commercial: invalid proposed workshare")
    if value["pricing_authorized"] is not False or value["external_contact_authorized"] is not False:
        raise ValidationError("commercial: carrier cannot authorize price/contact")


def compile_assessment(packet: Any, authority: Any, *, key: bytes, expected_key_id: str, as_of: str) -> dict[str, Any]:
    keys = {"schema", "solicitation", "sources", "requirements", "team_gates", "implementation_evidence", "commercial"}
    _require_exact_keys(packet, keys, "packet")
    if packet["schema"] != SCHEMA:
        raise ValidationError("packet: schema mismatch")
    _validate_solicitation(packet["solicitation"])
    _validate_commercial(packet["commercial"])
    as_of_dt = _parse_time(as_of, "as_of")
    if as_of_dt > datetime.now(timezone.utc).astimezone(as_of_dt.tzinfo) + __import__("datetime").timedelta(days=3660):
        raise ValidationError("as_of: implausibly future")

    trusted_rows = verify_source_authority(authority, key=key, expected_key_id=expected_key_id)
    packet_rows = validate_sources(packet["sources"])
    if _canonical(packet_rows) != _canonical(trusted_rows):
        raise ValidationError("packet sources do not match authenticated authority")
    trusted = {x["id"]: x for x in trusted_rows}

    requirements, requirement_gaps = _validate_requirements(packet["requirements"], trusted)
    team_gates, team_gaps = _validate_team_gates(packet["team_gates"])
    implementation, implementation_gaps = _validate_implementation(packet["implementation_evidence"])

    missing_sources = [sid for sid, row in trusted.items() if not row["retrieved"] or not row["current"]]
    deadline = _parse_time(PROPOSAL_DEADLINE, "proposal_deadline")

    reasons: list[str] = []
    if "rfp" in missing_sources:
        state = "HOLD_CONTROLLING_RFP_REQUIRED"
        reasons.append("official RFP bytes/current generation not authenticated")
    elif "appendix_c" in missing_sources:
        state = "HOLD_CONTRACT_APPENDIX_REQUIRED"
        reasons.append("official Appendix C bytes/current generation not authenticated")
    elif any(s in missing_sources for s in ("appendix_a", "appendix_b")):
        state = "HOLD_APPENDIX_BYTES_REQUIRED"
        reasons.extend([f"{sid} bytes/current generation not authenticated" for sid in ("appendix_a", "appendix_b") if sid in missing_sources])
    elif as_of_dt > deadline:
        state = "HOLD_DEADLINE_PASSED"
        reasons.append("proposal deadline passed")
    elif not requirements:
        state = "HOLD_REQUIREMENT_MATRIX_REQUIRED"
        reasons.append("no authenticated requirement rows")
    elif requirement_gaps:
        state = "HOLD_MANDATORY_REQUIREMENT_GAPS"
        reasons.append(f"mandatory requirement gaps: {len(requirement_gaps)}")
    elif implementation_gaps:
        state = "HOLD_IMPLEMENTATION_EVIDENCE_PLAN"
        reasons.append(f"missing implementation evidence kinds: {','.join(implementation_gaps)}")
    elif team_gaps:
        state = "HOLD_TEAM_QUALIFICATION"
        reasons.append(f"unproven team gates: {len(team_gaps)}")
    else:
        state = "READY_FOR_OWNER_PROPOSAL_REVIEW"
        reasons.append("source, requirements, implementation plan and team gates are evidence-backed")

    source_roots = {sid: trusted[sid]["sha256"] for sid in sorted(trusted)}
    assessment_core = {
        "schema": ASSESSMENT_SCHEMA,
        "solicitation_id": SOLICITATION_ID,
        "state": state,
        "as_of": as_of,
        "reasons": reasons,
        "source_roots": source_roots,
        "authority_receipt_sha256": _sha(authority),
        "requirement_count": len(requirements),
        "mandatory_requirement_gaps": requirement_gaps,
        "team_gate_gaps": team_gaps,
        "implementation_plan_gaps": implementation_gaps,
        "evaluation_points": packet["solicitation"]["evaluation_points"],
        "commercial_state": packet["commercial"]["state"],
        "proposed_workshare_minor": packet["commercial"]["workshare_minor"],
        "authority": {
            "buyer_contact": False,
            "preproposal_registration": False,
            "question_submission": False,
            "proposal_submission": False,
            "signature": False,
            "price_commitment": False,
            "contract_acceptance": False,
            "insurance_certification": False,
            "production_mutation": False,
            "award_claim": False,
            "payment_claim": False,
            "revenue_claim": False,
        },
    }
    return {**assessment_core, "receipt_sha256": _sha(assessment_core)}


def verify_assessment(packet: Any, authority: Any, assessment: Any, *, key: bytes, expected_key_id: str) -> bool:
    if not isinstance(assessment, dict) or "as_of" not in assessment:
        raise ValidationError("assessment missing as_of")
    expected = compile_assessment(packet, authority, key=key, expected_key_id=expected_key_id, as_of=assessment["as_of"])
    if _canonical(expected) != _canonical(assessment):
        raise ValidationError("assessment semantic verification failed")
    return True
