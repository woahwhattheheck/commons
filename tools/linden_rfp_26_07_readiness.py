#!/usr/bin/env python3
"""Fail-closed readiness gate for Linden Housing Authority RFP 26-07.

The public notice is useful deadline/submission metadata, but it is not the
controlling RFP package.  This gate deliberately refuses to infer package-only
requirements or to equate a drafted response with authority to register, price,
contact the buyer, or submit.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

SOURCE_SCHEMA = "commons/procurement-source-register/v1"
STATE_SCHEMA = "commons/procurement-readiness-state/v1"
PACKAGE_SOURCE_ID = "controlling_rfp_package_26_07"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PACKAGE_BOOL_GATES = (
    "addenda_current",
    "requirements_extracted",
    "evaluation_extracted",
    "forms_extracted",
    "insurance_extracted",
    "contract_terms_extracted",
    "pricing_fields_mapped",
    "security_privacy_extracted",
)
PORTAL_BOOL_GATES = (
    "vendor_registration_verified",
    "legal_company_identity_verified",
    "authorized_site_administrator_verified",
    "authorized_agent_for_vendor_agreement_verified",
    "company_information_truthfulness_attested",
    "submission_session_verified",
)
RESPONSE_BOOL_GATES = (
    "minimum_qualifications_satisfied",
    "required_references_satisfied",
    "required_staffing_satisfied",
    "insurance_satisfied",
    "mandatory_forms_complete",
    "technical_response_complete",
    "pricing_complete",
    "package_addenda_acknowledged",
)
SUBMISSION_AUTHORITY_GATES = (
    "owner_authorized_pricing_commitment",
    "owner_authorized_submission",
)
REGISTRATION_AUTHORITY_GATES = (
    "owner_authorized_portal_registration",
)


class ReadinessError(ValueError):
    """Raised when source/readiness data violates the fail-closed contract."""


def _reject_duplicate_pairs(pairs: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReadinessError("duplicate JSON key: %s" % key)
        out[key] = value
    return out


def load_json_bytes(raw: bytes) -> Dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("invalid UTF-8 JSON: %s" % exc) from exc
    if type(value) is not dict:
        raise ReadinessError("top-level JSON must be an object")
    return value


def load_json(path: Path) -> Dict[str, Any]:
    return load_json_bytes(path.read_bytes())


def _aware_dt(value: Any, name: str) -> datetime:
    if type(value) is not str:
        raise ReadinessError("%s must be an ISO-8601 string" % name)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReadinessError("%s must be valid ISO-8601" % name) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReadinessError("%s must include an explicit UTC offset" % name)
    return parsed


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ReadinessError("%s must be a JSON boolean" % name)
    return value


def _dict(value: Any, name: str) -> Dict[str, Any]:
    if type(value) is not dict:
        raise ReadinessError("%s must be an object" % name)
    return value


def _list(value: Any, name: str) -> List[Any]:
    if type(value) is not list:
        raise ReadinessError("%s must be a list" % name)
    return value


def validate_source_register(source: Dict[str, Any]) -> Dict[str, Any]:
    if source.get("schema") != SOURCE_SCHEMA:
        raise ReadinessError("unexpected source-register schema")
    solicitation = _dict(source.get("solicitation"), "solicitation")
    if solicitation.get("solicitation_id") != "26-07":
        raise ReadinessError("source register is not Linden RFP 26-07")

    sources = _list(source.get("sources"), "sources")
    by_id: Dict[str, Dict[str, Any]] = {}
    for index, raw in enumerate(sources):
        row = _dict(raw, "sources[%d]" % index)
        source_id = row.get("source_id")
        if type(source_id) is not str or not source_id:
            raise ReadinessError("sources[%d].source_id must be non-empty text" % index)
        if source_id in by_id:
            raise ReadinessError("duplicate source_id: %s" % source_id)
        by_id[source_id] = row

    package = by_id.get(PACKAGE_SOURCE_ID)
    if package is None:
        raise ReadinessError("controlling package source is missing")
    if package.get("kind") != "CONTROLLING_RFP_PACKAGE":
        raise ReadinessError("controlling package source kind changed")
    if package.get("controls_package_requirements") is not True:
        raise ReadinessError("controlling package must control package requirements")
    package_status = package.get("status")
    package_sha = package.get("sha256")
    if package_status == "MISSING_PACKAGE":
        if package_sha is not None:
            raise ReadinessError("missing package may not carry a sha256")
    elif package_status == "VERIFIED_PACKAGE":
        if type(package_sha) is not str or SHA256_RE.fullmatch(package_sha) is None:
            raise ReadinessError("verified package requires lowercase sha256")
    else:
        raise ReadinessError("unsupported controlling package status")

    public_sources = [row for row in sources if row.get("kind") == "PUBLIC_NOTICE"]
    if not public_sources:
        raise ReadinessError("at least one public notice source is required")
    for row in public_sources:
        if row.get("controls_package_requirements") is not False:
            raise ReadinessError("public notice may not be promoted to controlling package")

    notice = _dict(source.get("public_notice_facts"), "public_notice_facts")
    questions = _aware_dt(notice.get("questions_deadline"), "questions_deadline")
    proposal = _aware_dt(notice.get("proposal_deadline"), "proposal_deadline")
    if questions >= proposal:
        raise ReadinessError("questions deadline must precede proposal deadline")
    if notice.get("submission_method") != "PORTAL_ONLY":
        raise ReadinessError("public notice must preserve portal-only submission")
    if _bool(notice.get("hard_copy_allowed"), "hard_copy_allowed") is not False:
        raise ReadinessError("public notice must preserve no-hard-copy rule")
    if notice.get("pricing_route") != "DESIGNATED_MARKETPLACE_FIELDS_ONLY":
        raise ReadinessError("public notice pricing route changed")

    package_only = _dict(source.get("package_only_truth"), "package_only_truth")
    if package_status == "MISSING_PACKAGE":
        promoted = [key for key, value in package_only.items() if value != "MISSING_PACKAGE"]
        if promoted:
            raise ReadinessError(
                "package-only facts promoted without package: %s" % ", ".join(sorted(promoted))
            )

    support = _dict(source.get("support_route_observations"), "support_route_observations")
    observations = _list(support.get("observed"), "support_route_observations.observed")
    phones = {row.get("phone") for row in observations if type(row) is dict and row.get("phone")}
    if len(phones) > 1:
        if support.get("status") != "CONFLICT_OBSERVED":
            raise ReadinessError("conflicting support phones must remain explicit")
        if support.get("do_not_guess_operational_phone") is not True:
            raise ReadinessError("support-phone conflict must fail closed")

    boundaries = _dict(source.get("truth_boundaries"), "truth_boundaries")
    hard_false = (
        "public_notice_is_controlling_package",
        "marketplace_signup_is_package_acquisition",
        "portal_registration_authorized",
        "buyer_contact_authorized",
        "pricing_commitment_authorized",
        "submission_authorized",
        "contract_acceptance_authorized",
        "revenue_recognition_authorized",
    )
    for key in hard_false:
        if _bool(boundaries.get(key), "truth_boundaries.%s" % key):
            raise ReadinessError("truth boundary must stay false: %s" % key)

    return {
        "package_status": package_status,
        "package_sha256": package_sha,
        "questions_deadline": questions,
        "proposal_deadline": proposal,
        "support_phone_conflict": len(phones) > 1,
    }


def validate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("schema") != STATE_SCHEMA:
        raise ReadinessError("unexpected readiness-state schema")
    if state.get("solicitation_id") != "26-07":
        raise ReadinessError("readiness state is not Linden RFP 26-07")
    as_of = _aware_dt(state.get("as_of"), "state.as_of")

    package = _dict(state.get("package"), "package")
    portal = _dict(state.get("portal"), "portal")
    response = _dict(state.get("response"), "response")
    authority = _dict(state.get("authority"), "authority")

    for key in PACKAGE_BOOL_GATES:
        _bool(package.get(key), "package.%s" % key)
    for key in PORTAL_BOOL_GATES:
        _bool(portal.get(key), "portal.%s" % key)
    _bool(portal.get("support_route_conflict_resolved"), "portal.support_route_conflict_resolved")
    for key in RESPONSE_BOOL_GATES:
        _bool(response.get(key), "response.%s" % key)
    for key, value in authority.items():
        _bool(value, "authority.%s" % key)

    package_status = package.get("status")
    package_sha = package.get("sha256")
    if package_status == "MISSING_PACKAGE":
        if package_sha is not None:
            raise ReadinessError("missing readiness package may not carry a sha256")
        if any(package[key] for key in PACKAGE_BOOL_GATES):
            raise ReadinessError("package-derived gates may not be true while package is missing")
        if any(response[key] for key in RESPONSE_BOOL_GATES):
            raise ReadinessError("response-completion gates may not be true while package is missing")
    elif package_status == "VERIFIED_PACKAGE":
        if type(package_sha) is not str or SHA256_RE.fullmatch(package_sha) is None:
            raise ReadinessError("verified readiness package requires lowercase sha256")
    else:
        raise ReadinessError("unsupported readiness package status")

    deadlines = _dict(state.get("known_deadlines"), "known_deadlines")
    questions = _aware_dt(deadlines.get("questions_deadline"), "known_deadlines.questions_deadline")
    proposal = _aware_dt(deadlines.get("proposal_deadline"), "known_deadlines.proposal_deadline")
    if questions >= proposal:
        raise ReadinessError("state questions deadline must precede proposal deadline")

    return {
        "as_of": as_of,
        "package": package,
        "portal": portal,
        "response": response,
        "authority": authority,
        "questions_deadline": questions,
        "proposal_deadline": proposal,
    }


def _missing_true(section: Dict[str, Any], keys: Iterable[str], prefix: str) -> List[str]:
    return ["%s.%s" % (prefix, key) for key in keys if section.get(key) is not True]


def build_report(
    source: Dict[str, Any],
    state: Dict[str, Any],
    *,
    as_of_override: Optional[str] = None,
) -> Dict[str, Any]:
    source_view = validate_source_register(source)
    state_view = validate_state(state)
    as_of = state_view["as_of"] if as_of_override is None else _aware_dt(as_of_override, "as_of_override")

    if source_view["questions_deadline"] != state_view["questions_deadline"]:
        raise ReadinessError("source/state questions deadline mismatch")
    if source_view["proposal_deadline"] != state_view["proposal_deadline"]:
        raise ReadinessError("source/state proposal deadline mismatch")
    if source_view["package_status"] != state_view["package"].get("status"):
        raise ReadinessError("source/state package status mismatch")
    if source_view["package_sha256"] != state_view["package"].get("sha256"):
        raise ReadinessError("source/state package sha256 mismatch")

    questions_open = as_of < source_view["questions_deadline"]
    proposal_open = as_of < source_view["proposal_deadline"]

    registration_blockers: List[str] = []
    if state_view["portal"].get("legal_company_identity_verified") is not True:
        registration_blockers.append("portal.legal_company_identity_verified")
    if state_view["portal"].get("authorized_site_administrator_verified") is not True:
        registration_blockers.append("portal.authorized_site_administrator_verified")
    if state_view["portal"].get("authorized_agent_for_vendor_agreement_verified") is not True:
        registration_blockers.append("portal.authorized_agent_for_vendor_agreement_verified")
    if state_view["portal"].get("company_information_truthfulness_attested") is not True:
        registration_blockers.append("portal.company_information_truthfulness_attested")
    registration_blockers.extend(
        _missing_true(state_view["authority"], REGISTRATION_AUTHORITY_GATES, "authority")
    )
    registration_ready = not registration_blockers

    submission_blockers: List[str] = []
    if not proposal_open:
        submission_blockers.append("proposal_deadline_passed")
    if state_view["package"].get("status") != "VERIFIED_PACKAGE":
        submission_blockers.append("package.status")
    if not state_view["package"].get("sha256"):
        submission_blockers.append("package.sha256")
    submission_blockers.extend(
        _missing_true(state_view["package"], PACKAGE_BOOL_GATES, "package")
    )
    submission_blockers.extend(
        _missing_true(state_view["portal"], PORTAL_BOOL_GATES, "portal")
    )
    submission_blockers.extend(
        _missing_true(state_view["response"], RESPONSE_BOOL_GATES, "response")
    )
    submission_blockers.extend(
        _missing_true(state_view["authority"], SUBMISSION_AUTHORITY_GATES, "authority")
    )

    question_blockers: List[str] = []
    if not questions_open:
        question_blockers.append("questions_deadline_passed")
    if state_view["package"].get("status") != "VERIFIED_PACKAGE":
        question_blockers.append("package.status")
    if state_view["package"].get("requirements_extracted") is not True:
        question_blockers.append("package.requirements_extracted")
    if state_view["authority"].get("owner_authorized_buyer_question") is not True:
        question_blockers.append("authority.owner_authorized_buyer_question")
    if state_view["authority"].get("muse_outbound_clearance") is not True:
        question_blockers.append("authority.muse_outbound_clearance")

    next_actions = _list(state.get("next_actions"), "next_actions")
    recommended = None
    for row in sorted(next_actions, key=lambda item: item.get("priority", 999999)):
        if row.get("status") != "DONE":
            recommended = row
            break

    return {
        "schema": "commons/procurement-readiness-report/v1",
        "solicitation_id": "26-07",
        "as_of": as_of.isoformat(),
        "questions_window_open": questions_open,
        "proposal_window_open": proposal_open,
        "support_phone_conflict_observed": source_view["support_phone_conflict"],
        "portal_registration_ready": registration_ready,
        "portal_registration_blockers": sorted(set(registration_blockers)),
        "buyer_question_ready": not question_blockers,
        "buyer_question_blockers": sorted(set(question_blockers)),
        "submission_ready": not submission_blockers,
        "submission_blockers": sorted(set(submission_blockers)),
        "recommended_next_action": recommended,
        "authority": {
            "this_report_authorizes_portal_registration": False,
            "this_report_authorizes_buyer_contact": False,
            "this_report_authorizes_pricing_commitment": False,
            "this_report_authorizes_submission": False,
            "this_report_authorizes_contract_acceptance": False,
            "this_report_authorizes_payment_or_revenue_claim": False,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--expect-not-ready", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = build_report(
            load_json(args.sources),
            load_json(args.state),
            as_of_override=args.as_of,
        )
    except (OSError, ReadinessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.expect_not_ready and report["submission_ready"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
