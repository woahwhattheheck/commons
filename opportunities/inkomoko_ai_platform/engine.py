"""Fail-closed qualification and proposal-readiness carrier for Inkomoko.

The carrier is intentionally conservative: public reproductions may shape an
internal technical plan but cannot become buyer-authoritative submission facts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any

from .acceptance import AcceptanceError, evaluate_acceptance


class CarrierError(ValueError):
    pass


CONTRACT_VERSION = "inkomoko-response-carrier/v1"
OPPORTUNITY_ID = "INKOMOKO-AI-TRAINING-PLATFORM-2026"
SOURCE_AUTHORITY = {"BUYER_OFFICIAL", "PUBLIC_REPRODUCTION"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,95}$")

TECHNICAL_REQUIREMENTS = (
    "PROGRESSIVE_TRAINING",
    "ALWAYS_ON_SUPPORT",
    "HUMAN_ESCALATION_CONTEXT",
    "DYNAMIC_KNOWLEDGE",
    "FINANCIAL_PRODUCT_ENQUIRIES",
    "CBS_INKOBOOK_POWERBI_BOUNDARIES",
    "WHATSAPP_MULTICHANNEL",
    "RBAC_AUDIT_LOGGING",
    "MULTILINGUAL_EN_FR_RW_SW",
    "CONFIGURABLE_WORKFLOWS",
    "REALTIME_ANALYTICS_APIS",
    "PRIVACY_SECURITY_SCALABILITY",
)

QUALIFICATION_GATES = (
    "THREE_COMPARABLE_REFERENCES",
    "PRODUCTION_AI_CONVERSATIONAL_EXPERIENCE",
    "WHATSAPP_MULTICHANNEL_EXPERIENCE",
    "SENSITIVE_CBS_INTEGRATION_EXPERIENCE",
    "MULTILINGUAL_NLP_CAPABILITY",
    "SECURITY_PRIVACY_TRACK_RECORD",
    "EMERGING_MARKET_LOW_CONNECTIVITY_EXPERIENCE",
    "MULTIYEAR_FINANCIAL_CAPACITY",
    "LEGAL_COMPANY_DOCUMENTS",
    "NAMED_TEAM_CVS",
    "ITEMIZED_COMMERCIAL_PRICE",
)

SUBMISSION_GATES = (
    "CONTROLLING_BUYER_PACKET",
    "TECHNICAL_PROPOSAL_COMPLETE",
    "FINANCIAL_PROPOSAL_COMPLETE",
    "REFERENCES_VERIFIED",
    "LEGAL_DOCUMENTS_VERIFIED",
    "TEAM_AND_CVS_VERIFIED",
    "PROJECT_PLAN_VERIFIED",
    "SUPPORT_MODEL_VERIFIED",
    "RISK_REGISTER_VERIFIED",
    "PRICE_OWNER_APPROVED",
)


class _Pairs(list):
    pass


def _reject_constant(value: str) -> None:
    raise CarrierError(f"non-finite JSON number is forbidden: {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> _Pairs:
    seen: set[str] = set()
    out = _Pairs()
    for key, value in pairs:
        if key in seen:
            raise CarrierError(f"duplicate JSON key: {key}")
        seen.add(key)
        out.append((key, value))
    return out


def _materialize(value: Any) -> Any:
    if isinstance(value, _Pairs):
        return {key: _materialize(item) for key, item in value}
    if type(value) is list:
        return [_materialize(item) for item in value]
    return value


def strict_json_loads(text: str) -> Any:
    try:
        parsed = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (json.JSONDecodeError, CarrierError) as exc:
        if isinstance(exc, CarrierError):
            raise
        raise CarrierError("invalid JSON") from exc
    value = _materialize(parsed)
    _reject_nonfinite(value)
    return value


def _reject_nonfinite(value: Any) -> None:
    if type(value) is float and not math.isfinite(value):
        raise CarrierError("non-finite number")
    if type(value) is list:
        for item in value:
            _reject_nonfinite(item)
    if type(value) is dict:
        for item in value.values():
            _reject_nonfinite(item)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str, maximum: int = 300) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise CarrierError(f"{field} must be bounded non-empty text")
    return value


def _sha(value: Any, field: str) -> str:
    value = _text(value, field, 64)
    if not SHA256_RE.fullmatch(value):
        raise CarrierError(f"{field} must be lowercase sha256")
    return value


def _id(value: Any, field: str) -> str:
    value = _text(value, field, 96)
    if not ID_RE.fullmatch(value):
        raise CarrierError(f"{field} must be a safe uppercase identifier")
    return value


def _time(value: Any, field: str) -> str:
    value = _text(value, field, 32)
    if not value.endswith("Z"):
        raise CarrierError(f"{field} must be canonical UTC with Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CarrierError(f"{field} invalid UTC") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise CarrierError(f"{field} invalid UTC")
    if dt.microsecond:
        raise CarrierError(f"{field} must use whole seconds")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _https(value: Any, field: str) -> str:
    value = _text(value, field, 500)
    if not value.startswith("https://") or any(ch.isspace() for ch in value):
        raise CarrierError(f"{field} must be HTTPS")
    return value


def _status_rows(raw: Any, universe: tuple[str, ...], field: str) -> dict[str, dict[str, Any]]:
    if type(raw) is not list or len(raw) != len(universe):
        raise CarrierError(f"{field} must cover the exact contract universe")
    rows: dict[str, dict[str, Any]] = {}
    for row in raw:
        if type(row) is not dict or set(row) != {"id", "state", "evidence_sha256"}:
            raise CarrierError(f"{field} row keys are exact")
        rid = _id(row["id"], f"{field}.id")
        if rid in rows or rid not in universe:
            raise CarrierError(f"{field} unknown/duplicate id")
        state = row["state"]
        if state not in {"SUPPORTED", "OWNER_EVIDENCE_REQUIRED", "GAP"}:
            raise CarrierError(f"{field} invalid state")
        evidence = row["evidence_sha256"]
        if state == "SUPPORTED":
            evidence = _sha(evidence, f"{field}.evidence_sha256")
        elif evidence is not None:
            raise CarrierError(f"{field} non-supported row cannot claim evidence")
        rows[rid] = {"id": rid, "state": state, "evidence_sha256": evidence}
    if set(rows) != set(universe):
        raise CarrierError(f"{field} universe mismatch")
    return rows


def _validate_sources(raw: Any, evaluated_at: str) -> tuple[list[dict[str, Any]], bool]:
    if type(raw) is not list or not raw or len(raw) > 8:
        raise CarrierError("sources must be a bounded non-empty list")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    eval_dt = datetime.fromisoformat(evaluated_at[:-1] + "+00:00")
    official = False
    for row in raw:
        if type(row) is not dict or set(row) != {"id", "authority", "url", "content_sha256", "captured_at", "reviewed"}:
            raise CarrierError("source keys are exact")
        sid = _id(row["id"], "source.id")
        if sid in seen:
            raise CarrierError("duplicate source id")
        seen.add(sid)
        authority = row["authority"]
        if authority not in SOURCE_AUTHORITY:
            raise CarrierError("invalid source authority")
        url = _https(row["url"], "source.url")
        sha = _sha(row["content_sha256"], "source.content_sha256")
        captured_at = _time(row["captured_at"], "source.captured_at")
        captured_dt = datetime.fromisoformat(captured_at[:-1] + "+00:00")
        if captured_dt > eval_dt:
            raise CarrierError("source capture cannot be in the future")
        if type(row["reviewed"]) is not bool:
            raise CarrierError("source.reviewed must be boolean")
        if authority == "BUYER_OFFICIAL" and row["reviewed"]:
            official = True
        rows.append({"id": sid, "authority": authority, "url": url, "content_sha256": sha, "captured_at": captured_at, "reviewed": row["reviewed"]})
    return sorted(rows, key=lambda item: item["id"]), official


def compile_carrier(packet: Any, acceptance_cases: Any, evaluated_at: str) -> dict[str, Any]:
    evaluated_at = _time(evaluated_at, "evaluated_at")
    if type(packet) is not dict or set(packet) != {"opportunity_id", "sources", "technical", "qualification", "submission"}:
        raise CarrierError("packet keys are exact")
    if packet["opportunity_id"] != OPPORTUNITY_ID:
        raise CarrierError("opportunity identity mismatch")

    sources, has_reviewed_official = _validate_sources(packet["sources"], evaluated_at)
    technical = _status_rows(packet["technical"], TECHNICAL_REQUIREMENTS, "technical")
    qualification = _status_rows(packet["qualification"], QUALIFICATION_GATES, "qualification")
    submission = _status_rows(packet["submission"], SUBMISSION_GATES, "submission")
    try:
        acceptance = evaluate_acceptance(acceptance_cases)
    except AcceptanceError as exc:
        raise CarrierError(str(exc)) from exc

    tech_supported = all(row["state"] == "SUPPORTED" for row in technical.values())
    prime_supported = all(row["state"] == "SUPPORTED" for row in qualification.values())
    submission_supported = all(row["state"] == "SUPPORTED" for row in submission.values())
    technical_ready = tech_supported and acceptance["passed"]

    reasons: list[str] = []
    if not has_reviewed_official:
        reasons.append("CONTROLLING_BUYER_SOURCE_NOT_RETAINED")
    if not technical_ready:
        reasons.append("TECHNICAL_EVIDENCE_INCOMPLETE")
    if not prime_supported:
        reasons.append("PRIME_QUALIFICATION_EVIDENCE_INCOMPLETE")
    if not submission_supported:
        reasons.append("PROPOSAL_COMPLETENESS_INCOMPLETE")

    if prime_supported and technical_ready:
        posture = "PRIME_CANDIDATE"
    elif technical_ready:
        posture = "TEAMING_CANDIDATE"
    else:
        posture = "HOLD"

    if has_reviewed_official and technical_ready and prime_supported and submission_supported:
        proposal_state = "READY_FOR_OWNER_PROPOSAL_REVIEW"
    elif not has_reviewed_official:
        proposal_state = "HOLD_CONTROLLING_SOURCE"
    else:
        proposal_state = "HOLD_OWNER_EVIDENCE"

    normalized_packet = {
        "opportunity_id": OPPORTUNITY_ID,
        "sources": sources,
        "technical": [technical[rid] for rid in sorted(technical)],
        "qualification": [qualification[rid] for rid in sorted(qualification)],
        "submission": [submission[rid] for rid in sorted(submission)],
    }
    normalized_acceptance_input = sorted(acceptance_cases, key=lambda case: case["scenario_id"])
    source_digest = digest(sources)
    packet_digest = digest(normalized_packet)
    acceptance_digest = digest(normalized_acceptance_input)
    projection = {
        "contract_version": CONTRACT_VERSION,
        "opportunity_id": OPPORTUNITY_ID,
        "evaluated_at": evaluated_at,
        "pursuit_posture": posture,
        "proposal_state": proposal_state,
        "reasons": reasons,
        "source_set_sha256": source_digest,
        "packet_sha256": packet_digest,
        "acceptance_input_sha256": acceptance_digest,
        "technical_supported": sum(row["state"] == "SUPPORTED" for row in technical.values()),
        "technical_total": len(TECHNICAL_REQUIREMENTS),
        "qualification_supported": sum(row["state"] == "SUPPORTED" for row in qualification.values()),
        "qualification_total": len(QUALIFICATION_GATES),
        "submission_supported": sum(row["state"] == "SUPPORTED" for row in submission.values()),
        "submission_total": len(SUBMISSION_GATES),
        "synthetic_acceptance": acceptance,
        "external_contact_authorized": False,
        "proposal_submission_authorized": False,
        "pricing_commitment_authorized": False,
        "production_access_authorized": False,
        "contract_acceptance_authorized": False,
        "payment_or_revenue_claim": False,
    }
    return {"projection": projection, "receipt_sha256": digest(projection)}


def verify_carrier(packet: Any, acceptance_cases: Any, evaluated_at: str, report: Any) -> bool:
    if type(report) is not dict or set(report) != {"projection", "receipt_sha256"}:
        return False
    try:
        expected = compile_carrier(packet, acceptance_cases, evaluated_at)
    except CarrierError:
        return False
    return canonical_json(expected) == canonical_json(report)
