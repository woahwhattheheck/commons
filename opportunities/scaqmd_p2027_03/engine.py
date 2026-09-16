from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import date, datetime
from typing import Any

SCHEMA = "scaqmd-p2027-03/v1"
AUTH_SCHEMA = "scaqmd-p2027-03-source-authority/v1"
ASSESSMENT_SCHEMA = "scaqmd-p2027-03-assessment/v1"
SOLICITATION_ID = "P2027-03"
TITLE = "Software Systems Development, Maintenance and Support Services"
OFFICIAL_URL = "https://www.aqmd.gov/docs/default-source/bids/p2027-03.pdf?sfvrsn=98f8637e_2"
PROPOSAL_DEADLINE = "2026-12-04T13:00:00-08:00"
CONFERENCE_DATE = "2026-10-21T10:00:00-07:00"
PROJECT_CUTOFF = date(2021, 12, 4)
CORE_TECH = {
    "PEOPLESOFT_PEOPLETOOLS", "SITEFINITY", "ESRI_ARCGIS", "ONBASE",
    "DOTNET_CSHARP", "SQL_SERVER", "ORACLE", "MICROSOFT_AZURE",
}
REQUIRED_TEAM_GATES = {
    "STAFFING_BENCH", "MANAGEMENT_PLAN", "QA_QC_PROGRAM",
    "BACKGROUND_CHECK_PROCESS", "FINANCIAL_CORPORATE_PACKET",
    "CERTIFICATIONS_REPRESENTATIONS", "PHYSICAL_SUBMISSION_OWNER",
}
REQUIRED_CAPABILITIES = {
    "DATA_INTEGRATION_ENGINEERING", "MODERNIZATION_API_CLOUD",
    "DEVSECOPS", "AUTOMATED_TESTING", "AI_SYSTEM_EVALUATION",
    "MIGRATION_CUTOVER_ACCEPTANCE",
}
ALLOWED_OWNERS = {"PRIME", "TJL", "SUBCONTRACTOR", "SHARED", "BUYER"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{1,79}$")

class ValidationError(ValueError):
    pass


def _exact(obj: Any, keys: set[str], label: str) -> None:
    if not isinstance(obj, dict):
        raise ValidationError(f"{label}: expected object")
    got = set(obj)
    if got != keys:
        raise ValidationError(f"{label}: keys mismatch missing={sorted(keys-got)} extra={sorted(got-keys)}")


def _canonical(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _sha(v: Any) -> str:
    return hashlib.sha256(_canonical(v)).hexdigest()


def _time(s: str, label: str) -> datetime:
    if not isinstance(s, str):
        raise ValidationError(f"{label}: expected string")
    try:
        v = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label}: invalid ISO-8601") from exc
    if v.tzinfo is None:
        raise ValidationError(f"{label}: timezone required")
    return v


def _refs(v: Any, label: str, *, allow_empty=True) -> None:
    if not isinstance(v, list) or len(v) > 64:
        raise ValidationError(f"{label}: expected bounded list")
    if not allow_empty and not v:
        raise ValidationError(f"{label}: evidence required")
    seen = set()
    for x in v:
        if not isinstance(x, str) or not x or len(x) > 240 or x in seen:
            raise ValidationError(f"{label}: invalid/duplicate ref")
        seen.add(x)


def validate_source(source: Any) -> dict[str, Any]:
    keys = {"solicitation_id", "title", "official_url", "page_count", "observed_date", "raw_status", "raw_sha256", "raw_size_bytes"}
    _exact(source, keys, "source")
    if source["solicitation_id"] != SOLICITATION_ID or source["title"] != TITLE or source["official_url"] != OFFICIAL_URL:
        raise ValidationError("source: official identity mismatch")
    if source["page_count"] != 70 or isinstance(source["page_count"], bool):
        raise ValidationError("source: page_count mismatch")
    if not isinstance(source["observed_date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["observed_date"]):
        raise ValidationError("source: invalid observed_date")
    if source["raw_status"] not in {"RAW_BYTES_UNBOUND", "RAW_BYTES_BOUND"}:
        raise ValidationError("source: invalid raw_status")
    if source["raw_status"] == "RAW_BYTES_BOUND":
        if not isinstance(source["raw_sha256"], str) or not HEX64.fullmatch(source["raw_sha256"]):
            raise ValidationError("source: bound raw bytes require sha256")
        if not isinstance(source["raw_size_bytes"], int) or isinstance(source["raw_size_bytes"], bool) or source["raw_size_bytes"] <= 0:
            raise ValidationError("source: bound raw bytes require positive size")
    else:
        if source["raw_sha256"] is not None or source["raw_size_bytes"] != 0:
            raise ValidationError("source: unbound raw bytes cannot claim digest/size")
    return source


def build_source_authority(source: Any, *, key_id: str, key: bytes, issued_at: str) -> dict[str, Any]:
    source = validate_source(source)
    if not isinstance(key_id, str) or not re.fullmatch(r"[a-z0-9_.-]{3,48}", key_id):
        raise ValidationError("authority: invalid key_id")
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ValidationError("authority: key must be >=32 bytes")
    _time(issued_at, "authority.issued_at")
    payload = {"schema": AUTH_SCHEMA, "key_id": key_id, "issued_at": issued_at, "source": source}
    return {**payload, "mac_sha256": hmac.new(bytes(key), _canonical(payload), hashlib.sha256).hexdigest()}


def verify_source_authority(authority: Any, *, key: bytes, expected_key_id: str) -> dict[str, Any]:
    _exact(authority, {"schema", "key_id", "issued_at", "source", "mac_sha256"}, "authority")
    if authority["schema"] != AUTH_SCHEMA or authority["key_id"] != expected_key_id:
        raise ValidationError("authority: schema/key mismatch")
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ValidationError("authority: key must be >=32 bytes")
    _time(authority["issued_at"], "authority.issued_at")
    source = validate_source(authority["source"])
    mac = authority["mac_sha256"]
    if not isinstance(mac, str) or not HEX64.fullmatch(mac):
        raise ValidationError("authority: invalid MAC")
    payload = {"schema": authority["schema"], "key_id": authority["key_id"], "issued_at": authority["issued_at"], "source": source}
    expected = hmac.new(bytes(key), _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        raise ValidationError("authority: MAC mismatch")
    return source


def _validate_solicitation(v: Any) -> None:
    _exact(v, {"id", "title", "proposal_deadline", "conference_at", "evaluation_points", "commercial_posture"}, "solicitation")
    if v["id"] != SOLICITATION_ID or v["title"] != TITLE or v["proposal_deadline"] != PROPOSAL_DEADLINE or v["conference_at"] != CONFERENCE_DATE:
        raise ValidationError("solicitation: controlling identity mismatch")
    if v["evaluation_points"] != {"understanding":20,"technical_management":20,"qualifications":20,"similar_experience":10,"cost":30}:
        raise ValidationError("solicitation: evaluation points mismatch")
    if v["commercial_posture"] != "TEAMING_TASK_ORDER_SPECIALIST_FIRST":
        raise ValidationError("solicitation: posture mismatch")


def _validate_conference(v: Any) -> tuple[dict[str, Any], bool]:
    _exact(v, {"state", "evidence_refs"}, "conference")
    if v["state"] not in {"NOT_REGISTERED", "REGISTERED", "ATTENDED"}:
        raise ValidationError("conference: invalid state")
    _refs(v["evidence_refs"], "conference.evidence_refs")
    if v["state"] in {"REGISTERED", "ATTENDED"} and not v["evidence_refs"]:
        raise ValidationError("conference: claimed state requires evidence")
    return v, v["state"] == "ATTENDED"


def _validate_projects(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows, list) or len(rows) > 20:
        raise ValidationError("projects: bounded list expected")
    keys = {"id","client","completed_date","public_or_regulated","value_minor","duration_months","technologies","client_reference","challenge_corrective_documented","evidence_refs"}
    seen = set(); normalized=[]
    for row in rows:
        _exact(row, keys, "project")
        pid=row["id"]
        if not isinstance(pid,str) or not ID_RE.fullmatch(pid) or pid in seen:
            raise ValidationError("project: invalid/duplicate id")
        seen.add(pid)
        if not isinstance(row["client"],str) or not row["client"].strip():
            raise ValidationError(f"project {pid}: client required")
        try: d=date.fromisoformat(row["completed_date"])
        except Exception as exc: raise ValidationError(f"project {pid}: bad completed_date") from exc
        if d < PROJECT_CUTOFF:
            raise ValidationError(f"project {pid}: outside five-year qualification window")
        if not isinstance(row["public_or_regulated"],bool): raise ValidationError(f"project {pid}: public flag bool required")
        if row["value_minor"] is not None and (not isinstance(row["value_minor"],int) or isinstance(row["value_minor"],bool) or row["value_minor"] < 0):
            raise ValidationError(f"project {pid}: invalid value")
        if row["duration_months"] is not None and (not isinstance(row["duration_months"],int) or isinstance(row["duration_months"],bool) or row["duration_months"] < 0):
            raise ValidationError(f"project {pid}: invalid duration")
        tech=row["technologies"]
        if not isinstance(tech,list) or not tech or any(x not in CORE_TECH for x in tech) or len(set(tech)) != len(tech):
            raise ValidationError(f"project {pid}: technologies must be unique known values")
        if not isinstance(row["client_reference"],str) or not row["client_reference"].strip():
            raise ValidationError(f"project {pid}: client reference required")
        if not isinstance(row["challenge_corrective_documented"],bool): raise ValidationError(f"project {pid}: challenge flag bool required")
        _refs(row["evidence_refs"], f"project {pid}.evidence_refs", allow_empty=False)
        normalized.append(row)
    gaps=[]
    if len(normalized) < 3: gaps.append("THREE_COMPARABLE_PROJECTS")
    if normalized and not any(x["public_or_regulated"] for x in normalized): gaps.append("PUBLIC_OR_REGULATED_PROJECT")
    if normalized and not any((x["value_minor"] is not None and x["value_minor"] >= 10_000_000) or (x["duration_months"] is not None and x["duration_months"] >= 12) for x in normalized): gaps.append("VALUE_100K_OR_DURATION_12MO")
    if normalized and not any(set(x["technologies"]) & CORE_TECH for x in normalized): gaps.append("CORE_PLATFORM_TECHNOLOGY")
    if normalized and not any(x["challenge_corrective_documented"] for x in normalized): gaps.append("CHALLENGE_CORRECTIVE_EXAMPLE")
    return sorted(normalized,key=lambda x:x["id"]), gaps


def _validate_gates(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows,list) or len(rows) != len(REQUIRED_TEAM_GATES): raise ValidationError("team_gates: exact gate set required")
    keys={"id","state","responsible_party","evidence_refs"}; by={}; gaps=[]
    for row in rows:
        _exact(row,keys,"team_gate"); gid=row["id"]
        if gid not in REQUIRED_TEAM_GATES or gid in by: raise ValidationError("team_gate: unknown/duplicate id")
        if row["state"] not in {"PROVEN","UNKNOWN","NOT_APPLICABLE_WITH_EVIDENCE"}: raise ValidationError(f"team_gate {gid}: bad state")
        if row["responsible_party"] not in {"PRIME","TJL","OWNER"}: raise ValidationError(f"team_gate {gid}: bad party")
        _refs(row["evidence_refs"],f"team_gate {gid}.evidence_refs")
        if row["state"] != "UNKNOWN" and not row["evidence_refs"]: raise ValidationError(f"team_gate {gid}: evidenced state requires refs")
        if row["state"] == "UNKNOWN": gaps.append(gid)
        by[gid]=row
    return [by[x] for x in sorted(by)], sorted(gaps)


def _validate_capabilities(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(rows,list) or len(rows) > 30: raise ValidationError("capabilities: bounded list expected")
    keys={"id","kind","state","owner","evidence_refs"}; seen_id=set(); seen_kind=set(); missing=set(REQUIRED_CAPABILITIES); out=[]
    for row in rows:
        _exact(row,keys,"capability")
        if not isinstance(row["id"],str) or not ID_RE.fullmatch(row["id"]) or row["id"] in seen_id: raise ValidationError("capability: invalid/duplicate id")
        seen_id.add(row["id"]); kind=row["kind"]
        if kind not in REQUIRED_CAPABILITIES or kind in seen_kind: raise ValidationError("capability: invalid/duplicate kind")
        seen_kind.add(kind)
        if row["state"] not in {"DEFINED","PROVEN","HOLD"}: raise ValidationError("capability: bad state")
        if row["owner"] not in ALLOWED_OWNERS: raise ValidationError("capability: bad owner")
        _refs(row["evidence_refs"],f"capability {row['id']}.evidence_refs")
        if row["state"] == "PROVEN" and not row["evidence_refs"]: raise ValidationError("capability: PROVEN requires evidence")
        if row["state"] in {"DEFINED","PROVEN"}: missing.discard(kind)
        out.append(row)
    return sorted(out,key=lambda x:x["id"]), sorted(missing)


def _validate_commercial(v: Any) -> None:
    _exact(v,{"state","proposed_workshare_minor","currency","preference_points_claimed","external_contact_authorized","price_commitment_authorized"},"commercial")
    if v["state"] != "PROPOSED_NOT_ACCEPTED" or v["currency"] != "USD": raise ValidationError("commercial: state/currency mismatch")
    if v["proposed_workshare_minor"] is not None and (not isinstance(v["proposed_workshare_minor"],int) or isinstance(v["proposed_workshare_minor"],bool) or v["proposed_workshare_minor"] <= 0): raise ValidationError("commercial: invalid proposed workshare")
    if v["preference_points_claimed"] != 0: raise ValidationError("commercial: carrier may not self-mint preference points")
    if v["external_contact_authorized"] is not False or v["price_commitment_authorized"] is not False: raise ValidationError("commercial: authority escalation forbidden")


def compile_assessment(packet: Any, authority: Any, *, key: bytes, expected_key_id: str, as_of: str) -> dict[str, Any]:
    _exact(packet,{"schema","solicitation","source","conference","projects","team_gates","capabilities","commercial"},"packet")
    if packet["schema"] != SCHEMA: raise ValidationError("packet: schema mismatch")
    _validate_solicitation(packet["solicitation"]); _validate_commercial(packet["commercial"])
    now=_time(as_of,"as_of"); deadline=_time(PROPOSAL_DEADLINE,"proposal_deadline")
    source=verify_source_authority(authority,key=key,expected_key_id=expected_key_id)
    if _canonical(validate_source(packet["source"])) != _canonical(source): raise ValidationError("packet source differs from authenticated source")
    conference, attended=_validate_conference(packet["conference"])
    projects,project_gaps=_validate_projects(packet["projects"])
    gates,gate_gaps=_validate_gates(packet["team_gates"])
    capabilities,capability_gaps=_validate_capabilities(packet["capabilities"])
    reasons=[]
    if source["raw_status"] != "RAW_BYTES_BOUND": state="HOLD_SOURCE_BYTES_REQUIRED"; reasons.append("current official raw RFP bytes are not bound")
    elif now > deadline: state="HOLD_DEADLINE_PASSED"; reasons.append("proposal deadline passed")
    elif not attended: state="HOLD_CONFERENCE_ATTENDANCE"; reasons.append("mandatory bidder conference attendance is not evidenced")
    elif project_gaps: state="HOLD_PAST_PROJECT_QUALIFICATION"; reasons.append("past-project qualification gaps: "+",".join(project_gaps))
    elif capability_gaps: state="HOLD_CAPABILITY_PLAN"; reasons.append("missing task-order capability plan: "+",".join(capability_gaps))
    elif gate_gaps: state="HOLD_TEAM_QUALIFICATION"; reasons.append(f"unproven team gates: {len(gate_gaps)}")
    else: state="READY_FOR_OWNER_PROPOSAL_REVIEW"; reasons.append("source, conference, project pedigree, capability plan and team gates are evidenced")
    core={
        "schema":ASSESSMENT_SCHEMA,"solicitation_id":SOLICITATION_ID,"state":state,"as_of":as_of,"reasons":reasons,
        "source_raw_status":source["raw_status"],"source_raw_sha256":source["raw_sha256"],"source_authority_receipt_sha256":_sha(authority),
        "conference_state":conference["state"],"project_count":len(projects),"project_gaps":project_gaps,"team_gate_gaps":gate_gaps,"capability_plan_gaps":capability_gaps,
        "evaluation_points":packet["solicitation"]["evaluation_points"],"commercial_state":packet["commercial"]["state"],"proposed_workshare_minor":packet["commercial"]["proposed_workshare_minor"],
        "authority":{"conference_registration":False,"buyer_contact":False,"question_submission":False,"proposal_submission":False,"signature":False,"certification":False,"preference_claim":False,"price_commitment":False,"contract_acceptance":False,"production_access":False,"award_claim":False,"payment_claim":False,"revenue_claim":False},
    }
    return {**core,"receipt_sha256":_sha(core)}


def verify_assessment(packet: Any, authority: Any, assessment: Any, *, key: bytes, expected_key_id: str) -> bool:
    if not isinstance(assessment,dict) or "as_of" not in assessment: raise ValidationError("assessment missing as_of")
    expected=compile_assessment(packet,authority,key=key,expected_key_id=expected_key_id,as_of=assessment["as_of"])
    if _canonical(expected) != _canonical(assessment): raise ValidationError("assessment semantic verification failed")
    return True
