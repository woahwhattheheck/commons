from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parent
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISO_CURRENCY = re.compile(r"^[A-Z]{3}$")
_DEADLINE = datetime.fromisoformat("2026-10-01T10:00:00-04:00")

_EXPECTED_TOP = {
    "source_manifest_digest",
    "evaluated_at",
    "candidate",
    "commercial",
    "submission",
}
_EXPECTED_CANDIDATE = {
    "degree_evidence_digest",
    "experience_years",
    "experience_evidence_digest",
    "reference_evidence_digests",
    "nine_month_availability",
    "in_country_availability",
    "availability_evidence_digest",
    "lims_health_system_evidence_digest",
    "cross_sector_integration_evidence_digest",
    "training_evidence_digest",
    "conflict_disclosure",
}
_EXPECTED_COMMERCIAL = {"currency", "price_rows_minor", "all_inclusive_owner_confirmed"}
_EXPECTED_SUBMISSION = {"email", "subject", "validity_days"}
_PRICE_ROWS = (
    "Inception Report, Work Plan and Methodology",
    "Initial Assessment and GAP Analysis",
    "Cross-Sector SOPs, Policies and Practices for Data Exchange",
    "Recommendations for Adapting Existing LIMS Systems",
    "Data Collection and Standardisation",
    "End-User Training and Training Report",
    "Final Report",
)
_AUTHORITY_FALSE = {
    "buyer_contact_authorized": False,
    "clarification_authorized": False,
    "submission_authorized": False,
    "signature_authorized": False,
    "pricing_commitment_authorized": False,
    "travel_spend_authorized": False,
    "contract_acceptance_authorized": False,
    "award_claimed": False,
    "payment_claimed": False,
    "revenue_claimed": False,
}


class CarrierError(ValueError):
    pass


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CarrierError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CarrierError(f"non-finite JSON number: {token}")
            ),
        )
    except CarrierError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise CarrierError(f"invalid JSON: {exc}") from exc


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load_manifest() -> dict[str, Any]:
    manifest = loads_strict((_ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    if type(manifest) is not dict:
        raise CarrierError("source manifest must be an object")
    return manifest


_SOURCE = _load_manifest()
_SOURCE_DIGEST = _digest(_SOURCE)
_BUYER = deepcopy(_SOURCE["buyer_facts"])


def source_manifest_digest() -> str:
    return _SOURCE_DIGEST


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CarrierError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise CarrierError(f"{label} keys mismatch missing={missing} extra={extra}")
    return value


def _sha_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise CarrierError(f"{label} must be null or lowercase sha256")
    return value


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise CarrierError(f"{label} must be boolean")
    return value


def _strict_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CarrierError(f"{label} must be integer >= {minimum}")
    return value


def _evaluation_time(value: Any) -> datetime:
    if type(value) is not str:
        raise CarrierError("evaluated_at must be an ISO timestamp string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CarrierError("evaluated_at is not valid ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CarrierError("evaluated_at must include an offset")
    return parsed


def _validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    _exact_object(candidate, _EXPECTED_CANDIDATE, "candidate")
    digests: dict[str, str | None] = {}
    for key in (
        "degree_evidence_digest",
        "experience_evidence_digest",
        "availability_evidence_digest",
        "lims_health_system_evidence_digest",
        "cross_sector_integration_evidence_digest",
        "training_evidence_digest",
    ):
        digests[key] = _sha_or_none(candidate[key], f"candidate.{key}")

    years = _strict_int(candidate["experience_years"], "candidate.experience_years")
    nine_month = _strict_bool(
        candidate["nine_month_availability"], "candidate.nine_month_availability"
    )
    in_country = _strict_bool(
        candidate["in_country_availability"], "candidate.in_country_availability"
    )

    refs = candidate["reference_evidence_digests"]
    if type(refs) is not list:
        raise CarrierError("candidate.reference_evidence_digests must be an array")
    if len(refs) > 20:
        raise CarrierError("candidate.reference_evidence_digests is unbounded")
    checked_refs: list[str] = []
    seen: set[str] = set()
    for idx, value in enumerate(refs):
        digest = _sha_or_none(value, f"candidate.reference_evidence_digests[{idx}]")
        if digest is None:
            raise CarrierError("reference digest cannot be null")
        if digest in seen:
            raise CarrierError("duplicate reference evidence digest")
        seen.add(digest)
        checked_refs.append(digest)

    conflict = candidate["conflict_disclosure"]
    if conflict not in {"UNKNOWN", "NO_KNOWN_CONFLICT", "DISCLOSED_CONFLICT"}:
        raise CarrierError("candidate.conflict_disclosure invalid")

    return {
        **digests,
        "experience_years": years,
        "reference_evidence_digests": checked_refs,
        "nine_month_availability": nine_month,
        "in_country_availability": in_country,
        "conflict_disclosure": conflict,
    }


def _validate_commercial(commercial: dict[str, Any]) -> dict[str, Any]:
    _exact_object(commercial, _EXPECTED_COMMERCIAL, "commercial")
    currency = commercial["currency"]
    if currency is not None and (
        type(currency) is not str or not _ISO_CURRENCY.fullmatch(currency)
    ):
        raise CarrierError("commercial.currency must be null or 3-letter uppercase code")

    rows = commercial["price_rows_minor"]
    if type(rows) is not dict:
        raise CarrierError("commercial.price_rows_minor must be an object")
    if set(rows) != set(_PRICE_ROWS):
        raise CarrierError("commercial.price_rows_minor must contain exactly seven buyer rows")

    normalized: dict[str, int | None] = {}
    for name in _PRICE_ROWS:
        value = rows[name]
        if value is None:
            normalized[name] = None
        else:
            normalized[name] = _strict_int(value, f"commercial.price_rows_minor[{name}]")
    all_inclusive = _strict_bool(
        commercial["all_inclusive_owner_confirmed"],
        "commercial.all_inclusive_owner_confirmed",
    )
    return {
        "currency": currency,
        "price_rows_minor": normalized,
        "all_inclusive_owner_confirmed": all_inclusive,
    }


def _validate_submission(submission: dict[str, Any]) -> dict[str, Any]:
    _exact_object(submission, _EXPECTED_SUBMISSION, "submission")
    email = submission["email"]
    subject = submission["subject"]
    validity = _strict_int(submission["validity_days"], "submission.validity_days", 1)
    if type(email) is not str or type(subject) is not str:
        raise CarrierError("submission email/subject must be strings")
    return {"email": email, "subject": subject, "validity_days": validity}


def _score_readiness(candidate: Mapping[str, Any]) -> dict[str, Any]:
    evidence_present = {
        "minimum_education": candidate["degree_evidence_digest"] is not None,
        "minimum_experience": (
            candidate["experience_years"] >= int(_BUYER["minimum_experience_years"])
            and candidate["experience_evidence_digest"] is not None
        ),
        "three_references": (
            len(candidate["reference_evidence_digests"])
            >= int(_BUYER["minimum_references"])
        ),
        "nine_month_availability": (
            candidate["nine_month_availability"]
            and candidate["availability_evidence_digest"] is not None
        ),
        "in_country_availability": (
            candidate["in_country_availability"]
            and candidate["availability_evidence_digest"] is not None
        ),
    }
    optional_score_evidence = {
        "lims_health_system": candidate["lims_health_system_evidence_digest"] is not None,
        "cross_sector_integration": (
            candidate["cross_sector_integration_evidence_digest"] is not None
        ),
        "training": candidate["training_evidence_digest"] is not None,
    }
    return {
        "essential_owner_evidence_present": evidence_present,
        "score_bearing_owner_evidence_present": optional_score_evidence,
        "all_essential_owner_evidence_present": all(evidence_present.values()),
    }


def compile_packet(owner_input: Mapping[str, Any]) -> dict[str, Any]:
    top = _exact_object(dict(owner_input), _EXPECTED_TOP, "owner_input")
    if top["source_manifest_digest"] != _SOURCE_DIGEST:
        raise CarrierError("source_manifest_digest mismatch")
    evaluated = _evaluation_time(top["evaluated_at"])
    candidate = _validate_candidate(top["candidate"])
    commercial = _validate_commercial(top["commercial"])
    submission = _validate_submission(top["submission"])

    readiness = _score_readiness(candidate)
    deadline_open = evaluated.astimezone(_DEADLINE.tzinfo) <= _DEADLINE
    commercial_complete = (
        commercial["currency"] is not None
        and commercial["all_inclusive_owner_confirmed"]
        and all(value is not None for value in commercial["price_rows_minor"].values())
    )
    submission_matches_buyer = (
        submission["email"] == _BUYER["submission_email"]
        and submission["subject"] == _BUYER["submission_subject"]
        and submission["validity_days"] >= int(_BUYER["proposal_validity_days"])
    )
    conflict_resolved = candidate["conflict_disclosure"] != "UNKNOWN"

    blockers: list[str] = []
    if not deadline_open:
        blockers.append("PROPOSAL_DEADLINE_PASSED")
    if not readiness["all_essential_owner_evidence_present"]:
        blockers.append("OWNER_CREDENTIAL_EVIDENCE_INCOMPLETE")
    if not commercial_complete:
        blockers.append("OWNER_PRICING_INCOMPLETE")
    if not submission_matches_buyer:
        blockers.append("SUBMISSION_METADATA_MISMATCH")
    if not conflict_resolved:
        blockers.append("CONFLICT_DISCLOSURE_UNRESOLVED")

    if not deadline_open:
        posture = "NO_BID_DEADLINE_PASSED"
    elif blockers:
        posture = "HOLD_OWNER_EVIDENCE"
    else:
        posture = "OWNER_REVIEW_PACKET_COMPLETE_NOT_SUBMISSION_AUTHORITY"

    packet = {
        "schema": "tt-one-lab-lims-owner-review-packet/v1",
        "source_manifest_digest": _SOURCE_DIGEST,
        "evaluated_at": top["evaluated_at"],
        "buyer": {
            "procuring_entity": _BUYER["procuring_entity"],
            "project": _BUYER["project"],
            "consultancy": _BUYER["consultancy"],
            "deadline_local": _BUYER["proposal_deadline_local"],
            "submission_email": _BUYER["submission_email"],
            "submission_subject": _BUYER["submission_subject"],
            "clarification_cutoff_date": _BUYER["clarification_cutoff_date"],
            "clarification_email_as_printed_in_pdf": _BUYER[
                "clarification_email_as_printed_in_pdf"
            ],
            "clarification_route_conflict": _BUYER["clarification_route_conflict"],
        },
        "candidate_evidence": deepcopy(candidate),
        "readiness": readiness,
        "commercial": deepcopy(commercial),
        "submission": deepcopy(submission),
        "blockers": blockers,
        "posture": posture,
        "evaluation_weights": deepcopy(_BUYER["evaluation_weights"]),
        "authority": deepcopy(_AUTHORITY_FALSE),
    }
    packet["input_digest"] = _digest(top)
    packet["packet_digest"] = _digest(packet)
    return packet


def verify_packet(packet: Mapping[str, Any], owner_input: Mapping[str, Any]) -> bool:
    if type(packet) is not dict:
        return False
    expected = compile_packet(owner_input)
    return _canonical(dict(packet)) == _canonical(expected)


def example_owner_input() -> dict[str, Any]:
    return {
        "source_manifest_digest": _SOURCE_DIGEST,
        "evaluated_at": "2026-09-17T01:00:00-04:00",
        "candidate": {
            "degree_evidence_digest": None,
            "experience_years": 0,
            "experience_evidence_digest": None,
            "reference_evidence_digests": [],
            "nine_month_availability": False,
            "in_country_availability": False,
            "availability_evidence_digest": None,
            "lims_health_system_evidence_digest": None,
            "cross_sector_integration_evidence_digest": None,
            "training_evidence_digest": None,
            "conflict_disclosure": "UNKNOWN",
        },
        "commercial": {
            "currency": None,
            "price_rows_minor": {name: None for name in _PRICE_ROWS},
            "all_inclusive_owner_confirmed": False,
        },
        "submission": {
            "email": _BUYER["submission_email"],
            "subject": _BUYER["submission_subject"],
            "validity_days": _BUYER["proposal_validity_days"],
        },
    }
