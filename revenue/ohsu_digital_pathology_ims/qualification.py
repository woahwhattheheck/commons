# SPDX-License-Identifier: Apache-2.0
"""Deterministic, evidence-only qualification gate for OHSU RFP-2027-2012.

The public OHSU bid listing establishes opportunity identity and broad capability
needs, but explicitly says minimum bidder requirements live in the full RFP
package. This module therefore never infers bid eligibility from public summary
text. A READY decision requires an explicit, source-bound minimum-qualification
snapshot plus evidence for every declared minimum.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Iterable

OPPORTUNITY_ID = "RFP-2027-2012"
PUBLIC_SOURCE = "https://www.ohsu.edu/procurement/bids"
ISSUE_DATE = "2026-09-11"
DUE_DATE = "2026-10-11"
AUTHORITY = "EVIDENCE_ONLY_NO_BID_SUBMISSION"

PUBLIC_CAPABILITIES = (
    "epic_beaker_bidirectional_integration",
    "end_to_end_digital_pathology_workflow",
    "native_and_third_party_ai_ia_integration",
    "centralized_image_management_viewing_sharing_analysis",
    "clinical_education_research_missions",
)

class QualificationError(ValueError):
    """Input is malformed or violates deterministic evidence rules."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise QualificationError("timestamps must be UTC strings ending in Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise QualificationError("invalid UTC timestamp") from exc
    if dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise QualificationError("timestamp must resolve to UTC")
    return dt


def _nonempty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualificationError(f"{field} must be a non-empty string")
    return value.strip()


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise QualificationError(f"{field} must be boolean")
    return value


def _finite_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise QualificationError(f"{field} must be numeric")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise QualificationError(f"{field} must be numeric") from exc
    if not out.is_finite():
        raise QualificationError(f"{field} must be finite")
    return out


def _unique_rows(rows: Iterable[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise QualificationError("evidence rows must be objects")
        ident = _nonempty_str(row.get(key), key)
        if ident in out:
            raise QualificationError(f"duplicate {key}: {ident}")
        out[ident] = row
    return out


def evaluate(payload: dict[str, Any], *, evaluated_at: str) -> dict[str, Any]:
    """Evaluate a captured qualification bundle.

    `evaluated_at` is trusted verifier time supplied outside the evidence. The
    receipt binds source, minimum requirements, capability claims and evidence;
    it never authorizes outreach, intent-to-bid or proposal submission.
    """
    if not isinstance(payload, dict):
        raise QualificationError("payload must be an object")
    now = _parse_utc(evaluated_at)

    opportunity = payload.get("opportunity")
    if not isinstance(opportunity, dict):
        raise QualificationError("opportunity must be an object")
    if opportunity.get("id") != OPPORTUNITY_ID:
        raise QualificationError("wrong opportunity id")
    if opportunity.get("public_source") != PUBLIC_SOURCE:
        raise QualificationError("wrong public source")
    if opportunity.get("issue_date") != ISSUE_DATE or opportunity.get("due_date") != DUE_DATE:
        raise QualificationError("opportunity date mismatch")

    captured_at = _parse_utc(_nonempty_str(payload.get("captured_at"), "captured_at"))
    if captured_at > now:
        raise QualificationError("capture time is in the future")
    due = datetime.fromisoformat(DUE_DATE + "T23:59:59+00:00")

    full_rfp = payload.get("full_rfp")
    holds: list[str] = []
    if not isinstance(full_rfp, dict):
        holds.append("FULL_RFP_PACKAGE_NOT_CAPTURED")
        full_rfp = {}
    else:
        if not _strict_bool(full_rfp.get("captured", False), "full_rfp.captured"):
            holds.append("FULL_RFP_PACKAGE_NOT_CAPTURED")
        source = full_rfp.get("source")
        sha256 = full_rfp.get("sha256")
        if full_rfp.get("captured"):
            if not isinstance(source, str) or not source.strip():
                holds.append("FULL_RFP_SOURCE_MISSING")
            if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
                holds.append("FULL_RFP_DIGEST_INVALID")

    minimums = payload.get("minimum_qualifications")
    if not isinstance(minimums, list) or not minimums:
        holds.append("MINIMUM_QUALIFICATIONS_NOT_CAPTURED")
        minimums = []
    min_rows = _unique_rows(minimums, "id") if minimums else {}

    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise QualificationError("evidence must be a list")
    evidence_rows = _unique_rows(evidence, "requirement_id")

    missing_minimum_evidence: list[str] = []
    failed_minimums: list[str] = []
    for requirement_id, row in min_rows.items():
        if type(row.get("mandatory")) is not bool:
            raise QualificationError(f"minimum {requirement_id} mandatory must be boolean")
        if not row["mandatory"]:
            continue
        proof = evidence_rows.get(requirement_id)
        if proof is None:
            missing_minimum_evidence.append(requirement_id)
            continue
        result = proof.get("result")
        if result not in {"PASS", "FAIL"}:
            raise QualificationError(f"evidence result for {requirement_id} must be PASS or FAIL")
        _nonempty_str(proof.get("reference"), f"evidence reference for {requirement_id}")
        _nonempty_str(proof.get("sha256"), f"evidence sha256 for {requirement_id}")
        if len(proof["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in proof["sha256"]):
            raise QualificationError(f"evidence sha256 for {requirement_id} must be lowercase hex")
        if result == "FAIL":
            failed_minimums.append(requirement_id)

    if missing_minimum_evidence:
        holds.append("MANDATORY_EVIDENCE_MISSING")
    if failed_minimums:
        holds.append("MANDATORY_QUALIFICATION_FAILED")
    if now > due:
        holds.append("OPPORTUNITY_DEADLINE_PASSED")

    capabilities = payload.get("public_capability_claims", [])
    if not isinstance(capabilities, list):
        raise QualificationError("public_capability_claims must be a list")
    capability_set = set()
    for capability in capabilities:
        capability_set.add(_nonempty_str(capability, "capability"))
    unknown = sorted(capability_set - set(PUBLIC_CAPABILITIES))
    if unknown:
        raise QualificationError("unknown public capability claim: " + ",".join(unknown))
    missing_public = sorted(set(PUBLIC_CAPABILITIES) - capability_set)
    if missing_public:
        holds.append("PUBLIC_CAPABILITY_MATRIX_INCOMPLETE")

    decision = "READY_FOR_INTERNAL_BID_REVIEW" if not holds else "HOLD"
    evidence_digest = digest({
        "opportunity": opportunity,
        "captured_at": payload.get("captured_at"),
        "full_rfp": full_rfp,
        "minimum_qualifications": minimums,
        "public_capability_claims": sorted(capability_set),
        "evidence": evidence,
    })
    receipt = {
        "schema": "ohsu-digital-pathology-qualification/v1",
        "opportunity_id": OPPORTUNITY_ID,
        "decision": decision,
        "holds": sorted(set(holds)),
        "missing_mandatory_evidence": sorted(missing_minimum_evidence),
        "failed_mandatory_qualifications": sorted(failed_minimums),
        "missing_public_capabilities": missing_public,
        "evaluated_at": evaluated_at,
        "evidence_digest": evidence_digest,
        "authority": AUTHORITY,
        "outreach_authorized": False,
        "intent_to_bid_authorized": False,
        "proposal_submission_authorized": False,
        "clinical_use_authorized": False,
    }
    receipt["receipt_digest"] = digest(receipt)
    return receipt


def verify(payload: dict[str, Any], receipt: dict[str, Any], *, evaluated_at: str) -> bool:
    expected = evaluate(payload, evaluated_at=evaluated_at)
    return expected == receipt
