from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from typing import Any

SCHEMA_FACTS = "ohsu-erp-source-bound-facts/v1"
SCHEMA_PACKET = "ohsu-erp-source-bound-owner-review/v1"
SCHEMA_INPUT = "ohsu-erp-source-bound-compile-input/v1"
SCHEMA_VERIFY_INPUT = "ohsu-erp-source-bound-verify-input/v1"
OPPORTUNITY_ID = "RFP-2027-0005"
MAX_STDIN_BYTES = 1_048_576

CONTROLLING_PACK_SHA256 = "4d4c634ac5f7846dac54692c8d7d2c57a6512f8c2f6984be1c36f2a8dc99f90e"
SUPPLIER_QA_SHA256 = "40815c4a57d9d82cf07e4db6b2b6f1dfc6512c7fa4cf996af6ec364608722cf0"
INTENT_DEADLINE = _dt.datetime.fromisoformat("2026-09-16T17:00:00-07:00")
PROPOSAL_DEADLINE = _dt.datetime.fromisoformat("2026-09-25T17:00:00-07:00")

REQUIREMENT_IDS = (
    "MBR_1_01_RECENT_COMPARABLE_ERP_ASSESSMENTS",
    "MBR_1_02_ORACLE_EBS_AND_MAJOR_ERP_EVALUATION",
    "MBR_1_03_CROSS_FUNCTIONAL_ERP_EXPERTISE",
    "MBR_1_04_VENDOR_NEUTRALITY_AND_AFFILIATION_DISCLOSURE",
    "MBR_1_05_REGULATED_ENVIRONMENT_TEAM_PM_QA",
    "MBR_1_06_COMPARABLE_REFERENCES_AND_WORK_SAMPLES",
    "MBR_1_07_DATA_AND_DELIVERABLE_RIGHTS",
)
_REQUIRED_SET = frozenset(REQUIREMENT_IDS)
_SHA256_CHARS = frozenset("0123456789abcdef")


class ContractError(ValueError):
    pass


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _workshare() -> dict[str, Any]:
    return {
        "commercial_status": "PROPOSED_NOT_ACCEPTED",
        "fixed_price_usd": 12500,
        "delivery_window_status": "TO_NEGOTIATE",
        "scope": [
            "source-bound requirement register across interviews, current-state artifacts, controls, and future-state needs",
            "requirement to evidence to owner to gap/risk traceability with orphan detection",
            "deterministic coverage and contradiction reports across finance, HR, supply-chain, and administrative workflows",
            "decision receipts separating observed current-state evidence, stakeholder assertions, and consultant recommendations",
            "AI/automation opportunity entries with explicit human approval, source provenance, and control requirements",
        ],
    }


def _authority_false() -> dict[str, bool]:
    return {
        "buyer_contact_authorized": False,
        "intent_to_bid_authorized": False,
        "proposal_submission_authorized": False,
        "prime_eligibility_verified_by_ohsu": False,
        "teaming_commitment_accepted": False,
        "contract_accepted": False,
        "payment_verified": False,
        "revenue_recognized": False,
    }


def _require_keys(obj: dict[str, Any], *, exact: set[str], where: str) -> None:
    got = set(obj)
    if got != exact:
        raise ContractError(
            f"{where} keys mismatch; missing={sorted(exact - got)} extra={sorted(got - exact)}"
        )


def _require_sha256(value: Any, where: str, *, allow_none: bool = False) -> str | None:
    if allow_none and value is None:
        return None
    if not isinstance(value, str) or len(value) != 64 or any(c not in _SHA256_CHARS for c in value):
        raise ContractError(f"{where} must be exact lowercase sha256")
    return value


def _require_utc_instant(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{where} must be UTC Z timestamp")
    try:
        parsed = _dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{where} invalid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != _dt.timedelta(0):
        raise ContractError(f"{where} must be UTC")
    return parsed.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_strict_json(raw: bytes, where: str) -> Any:
    if len(raw) > MAX_STDIN_BYTES:
        raise ContractError(f"{where} exceeds {MAX_STDIN_BYTES} bytes")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{where} is not strict UTF-8") from exc

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ContractError(f"{where} duplicate JSON key: {key}")
            out[key] = value
        return out

    def bad_constant(token: str) -> Any:
        raise ContractError(f"{where} non-finite JSON number: {token}")

    try:
        return json.loads(text, object_pairs_hook=hook, parse_constant=bad_constant)
    except ContractError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ContractError(f"{where} invalid JSON") from exc


def _normalize_source_binding(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError("facts.source_binding must be object")
    _require_keys(
        value,
        exact={"controlling_pack_sha256", "supplier_qa_sha256"},
        where="facts.source_binding",
    )
    pack = _require_sha256(value["controlling_pack_sha256"], "facts.source_binding.controlling_pack_sha256")
    qa = _require_sha256(value["supplier_qa_sha256"], "facts.source_binding.supplier_qa_sha256")
    if pack != CONTROLLING_PACK_SHA256:
        raise ContractError("controlling pack digest differs from received source binding")
    if qa != SUPPLIER_QA_SHA256:
        raise ContractError("supplier Q&A digest differs from received source binding")
    return {"controlling_pack_sha256": pack, "supplier_qa_sha256": qa}


def _normalize_commitment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("facts.teaming_commitment must be object")
    _require_keys(
        value,
        exact={"status", "partner_ref", "evidence_sha256"},
        where="facts.teaming_commitment",
    )
    status = value["status"]
    if status not in {"UNCONFIRMED", "CONFIRMED"}:
        raise ContractError("facts.teaming_commitment.status invalid")
    partner_ref = value["partner_ref"]
    evidence = _require_sha256(
        value["evidence_sha256"],
        "facts.teaming_commitment.evidence_sha256",
        allow_none=True,
    )
    if status == "UNCONFIRMED":
        if partner_ref is not None or evidence is not None:
            raise ContractError("unconfirmed teaming commitment cannot carry partner identity or evidence")
        return {"status": status, "partner_ref": None, "evidence_sha256": None}
    if not isinstance(partner_ref, str) or not partner_ref.strip() or len(partner_ref) > 128:
        raise ContractError("confirmed teaming commitment requires bounded partner_ref")
    if evidence is None:
        raise ContractError("confirmed teaming commitment requires evidence_sha256")
    return {"status": status, "partner_ref": partner_ref.strip(), "evidence_sha256": evidence}


def _normalize_requirements(value: Any, *, route: str, commitment: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ContractError("facts.requirements must be list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        where = f"facts.requirements[{index}]"
        if not isinstance(raw, dict):
            raise ContractError(f"{where} must be object")
        _require_keys(
            raw,
            exact={"requirement_id", "state", "basis", "entity_ref", "evidence_sha256"},
            where=where,
        )
        rid = raw["requirement_id"]
        if rid not in _REQUIRED_SET:
            raise ContractError(f"{where}.requirement_id is not a normalized minimum gate")
        if rid in seen:
            raise ContractError(f"duplicate requirement_id: {rid}")
        seen.add(rid)

        state = raw["state"]
        if state not in {"SATISFIED", "MISSING", "UNKNOWN"}:
            raise ContractError(f"{where}.state invalid")
        basis = raw["basis"]
        if basis not in {"NONE", "RESPONDENT", "NAMED_COMMITTED_TEAM_PARTNER"}:
            raise ContractError(f"{where}.basis invalid")
        entity_ref = raw["entity_ref"]
        evidence = _require_sha256(raw["evidence_sha256"], f"{where}.evidence_sha256", allow_none=True)

        if state != "SATISFIED":
            if basis != "NONE" or entity_ref is not None or evidence is not None:
                raise ContractError(f"{where} non-SATISFIED gate cannot carry qualification evidence")
        else:
            if basis == "NONE" or evidence is None:
                raise ContractError(f"{where} SATISFIED requires explicit basis and evidence")
            if not isinstance(entity_ref, str) or not entity_ref.strip() or len(entity_ref) > 128:
                raise ContractError(f"{where} SATISFIED requires bounded entity_ref")
            entity_ref = entity_ref.strip()
            if basis == "NAMED_COMMITTED_TEAM_PARTNER":
                if route != "TEAMING":
                    raise ContractError("team-partner qualification basis is forbidden outside TEAMING route")
                if commitment["status"] != "CONFIRMED":
                    raise ContractError("unconfirmed outreach target contributes zero qualifications")
                if entity_ref != commitment["partner_ref"]:
                    raise ContractError("team qualification entity does not match confirmed partner")
            elif basis == "RESPONDENT" and commitment["partner_ref"] is not None and entity_ref == commitment["partner_ref"]:
                raise ContractError("confirmed partner qualification cannot be relabeled RESPONDENT")

        out.append(
            {
                "requirement_id": rid,
                "state": state,
                "basis": basis,
                "entity_ref": entity_ref,
                "evidence_sha256": evidence,
            }
        )

    if seen != _REQUIRED_SET:
        raise ContractError(
            f"facts.requirements must cover exact normalized gate set; missing={sorted(_REQUIRED_SET - seen)}"
        )
    out.sort(key=lambda row: row["requirement_id"])
    return out


def _normalize_intent_receipt(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContractError("facts.intent_receipt must be object or null")
    _require_keys(value, exact={"provider_event_sha256", "submitted_at"}, where="facts.intent_receipt")
    return {
        "provider_event_sha256": _require_sha256(
            value["provider_event_sha256"], "facts.intent_receipt.provider_event_sha256"
        ),
        "submitted_at": _require_utc_instant(value["submitted_at"], "facts.intent_receipt.submitted_at"),
    }


def _normalize_facts(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ContractError("facts must be object")
    _require_keys(
        obj,
        exact={
            "schema",
            "route",
            "source_binding",
            "requirements",
            "teaming_commitment",
            "intent_receipt",
            "owner_reviewed",
        },
        where="facts",
    )
    if obj["schema"] != SCHEMA_FACTS:
        raise ContractError("facts.schema invalid")
    route = obj["route"]
    if route not in {"UNKNOWN", "TEAMING", "PRIME"}:
        raise ContractError("facts.route invalid")
    if type(obj["owner_reviewed"]) is not bool:
        raise ContractError("facts.owner_reviewed must be bool")

    source_binding = _normalize_source_binding(obj["source_binding"])
    commitment = _normalize_commitment(obj["teaming_commitment"])
    if route != "TEAMING" and commitment["status"] == "CONFIRMED":
        raise ContractError("confirmed teaming commitment requires TEAMING route")
    requirements = _normalize_requirements(obj["requirements"], route=route, commitment=commitment)
    return {
        "schema": SCHEMA_FACTS,
        "route": route,
        "source_binding": source_binding,
        "requirements": requirements,
        "teaming_commitment": commitment,
        "intent_receipt": _normalize_intent_receipt(obj["intent_receipt"]),
        "owner_reviewed": obj["owner_reviewed"],
    }


def _as_utc(value: _dt.datetime) -> _dt.datetime:
    if type(value) is not _dt.datetime or value.tzinfo is None:
        raise ContractError("internal evaluation instant must be timezone-aware datetime")
    return value.astimezone(_dt.timezone.utc)


def _gap_blockers(requirements: list[dict[str, Any]]) -> list[str]:
    return [
        f"{row['state']}:{row['requirement_id']}"
        for row in requirements
        if row["state"] != "SATISFIED"
    ]


def _basis_counts(requirements: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"RESPONDENT": 0, "NAMED_COMMITTED_TEAM_PARTNER": 0, "UNSATISFIED": 0}
    for row in requirements:
        if row["state"] != "SATISFIED":
            counts["UNSATISFIED"] += 1
        else:
            counts[row["basis"]] += 1
    return counts


def _compile_at(facts_obj: Any, now: _dt.datetime) -> dict[str, Any]:
    facts = _normalize_facts(facts_obj)
    now_utc = _as_utc(now)
    intent_utc = INTENT_DEADLINE.astimezone(_dt.timezone.utc)
    proposal_utc = PROPOSAL_DEADLINE.astimezone(_dt.timezone.utc)
    blockers: list[str] = []
    actions: list[str] = []
    gaps = _gap_blockers(facts["requirements"])

    if now_utc >= proposal_utc:
        status = "CLOSED_DEADLINE"
        blockers.append("PROPOSAL_DEADLINE_REACHED")
        actions.append("ARCHIVE_OR_WAIT_FOR_REISSUE")
    else:
        receipt = facts["intent_receipt"]
        if receipt is None and now_utc >= intent_utc:
            status = "HOLD_INTENT_DEADLINE"
            blockers.append("NO_INTENT_RECEIPT_AT_OR_AFTER_DEADLINE")
            actions.append("VERIFY_WITH_PROCUREMENT_WHETHER_RESPONSE_REMAINS_ELIGIBLE")
        elif receipt is not None and _dt.datetime.fromisoformat(
            receipt["submitted_at"].replace("Z", "+00:00")
        ) > intent_utc:
            status = "HOLD_INTENT_CHRONOLOGY"
            blockers.append("INTENT_RECEIPT_AFTER_CONFIRMED_DEADLINE")
            actions.append("VERIFY_INTENT_ACCEPTANCE_WITH_PROCUREMENT")
        elif facts["route"] == "UNKNOWN":
            status = "HOLD_ROUTE_UNKNOWN"
            blockers.append("PRIME_OR_TEAMING_ROUTE_NOT_SELECTED")
            blockers.extend(gaps)
            actions.append("SELECT_PRIME_OR_TEAMING_ROUTE")
        elif facts["route"] == "PRIME":
            if gaps:
                status = "HOLD_PRIME_QUALIFICATION"
                blockers.extend(gaps)
                actions.append("DO_NOT_CLAIM_PRIME_ELIGIBILITY_WITHOUT_RESPONDENT_EVIDENCE")
            elif not facts["owner_reviewed"]:
                status = "HOLD_OWNER_REVIEW"
                blockers.append("FACTS_NOT_OWNER_REVIEWED")
                actions.append("OWNER_REVIEW_SOURCE_BOUND_REQUIREMENTS")
            else:
                status = "READY_FOR_OWNER_PRIME_REVIEW"
                actions.append("OWNER_REVIEW_PRIME_RESPONSE_PLAN")
        else:
            commitment = facts["teaming_commitment"]
            if commitment["status"] != "CONFIRMED":
                status = "TEAMING_CANDIDATE"
                blockers.append("NO_NAMED_COMMITTED_TEAM_PARTNER")
                blockers.extend(gaps)
                actions.extend(
                    [
                        "OBTAIN_NAMED_COMMITTED_TEAM_PARTNER",
                        "CLOSE_TEAM_COMPOSABLE_GAPS_WITH_SOURCE_EVIDENCE",
                    ]
                )
            elif gaps:
                status = "HOLD_TEAM_QUALIFICATION"
                blockers.extend(gaps)
                actions.append("CLOSE_REMAINING_TEAM_QUALIFICATION_GAPS")
            elif not facts["owner_reviewed"]:
                status = "HOLD_OWNER_REVIEW"
                blockers.append("FACTS_NOT_OWNER_REVIEWED")
                actions.append("OWNER_REVIEW_SOURCE_BOUND_TEAM_EVIDENCE")
            else:
                status = "READY_FOR_OWNER_TEAMING_REVIEW"
                actions.append("OWNER_REVIEW_PAID_WORKSHARE_WITH_CONFIRMED_PRIME")

    packet = {
        "schema": SCHEMA_PACKET,
        "opportunity_id": OPPORTUNITY_ID,
        "evaluation_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "deadlines": {
            "intent_to_bid": INTENT_DEADLINE.isoformat(),
            "proposal_due": PROPOSAL_DEADLINE.isoformat(),
            "intent_route": "BRIEF_EMAIL_TO_ISSUING_CONTACT",
        },
        "source_binding": facts["source_binding"],
        "source_policy": {
            "buyer_workbooks_published_to_public_repo": False,
            "source_digest_match_required": True,
            "attachment_provenance_authenticated_by_code": False,
        },
        "route": facts["route"],
        "status": status,
        "blockers": sorted(set(blockers)),
        "next_actions": actions,
        "requirements": facts["requirements"],
        "qualification_basis_counts": _basis_counts(facts["requirements"]),
        "teaming_commitment": facts["teaming_commitment"],
        "facts_sha256": _sha(facts),
        "workshare": _workshare(),
        "authority": _authority_false(),
        "truth_boundary": {
            "unconfirmed_outreach_target_contributes_qualifications": False,
            "named_committed_team_partner_may_supply_source_bound_qualification_evidence": True,
            "prime_remains_responsible": True,
            "strongest_output_is_owner_review_only": True,
            "external_send_authorized": False,
        },
    }
    packet["packet_sha256"] = _sha(packet)
    return packet


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def compile_current(facts_obj: Any) -> dict[str, Any]:
    return _compile_at(facts_obj, _now_utc())


def _packet_evaluation_instant(packet_obj: dict[str, Any]) -> _dt.datetime:
    evaluation = _require_utc_instant(packet_obj.get("evaluation_utc"), "packet.evaluation_utc")
    return _dt.datetime.fromisoformat(evaluation.replace("Z", "+00:00"))


def _operational_projection(packet_obj: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "opportunity_id",
        "deadlines",
        "source_binding",
        "source_policy",
        "route",
        "status",
        "blockers",
        "next_actions",
        "requirements",
        "qualification_basis_counts",
        "teaming_commitment",
        "facts_sha256",
        "workshare",
        "authority",
        "truth_boundary",
    )
    try:
        return {key: packet_obj[key] for key in keys}
    except KeyError as exc:
        raise ContractError(f"packet missing operational field: {exc.args[0]}") from exc


def verify_current(packet_obj: Any, facts_obj: Any) -> bool:
    if not isinstance(packet_obj, dict):
        raise ContractError("packet must be object")

    # First prove exact package integrity at the packet's own bound evaluation
    # instant. This prevents a fresh wall-clock sample from invalidating a
    # packet solely because evaluation_utc advanced by milliseconds.
    bound_instant = _packet_evaluation_instant(packet_obj)
    expected_at_bound = _compile_at(facts_obj, bound_instant)
    if _canonical(packet_obj) != _canonical(expected_at_bound):
        raise ContractError("packet integrity does not match bound source compilation")

    # Then ask whether the packet still represents current operational truth.
    # Only currentness-sensitive fields are compared; evaluation_utc and the
    # receipt digest are intentionally excluded after bound-integrity proof.
    current = compile_current(facts_obj)
    if _canonical(_operational_projection(packet_obj)) != _canonical(_operational_projection(current)):
        raise ContractError("packet operational state is stale")
    return True


def _read_stdin() -> bytes:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ContractError(f"stdin exceeds {MAX_STDIN_BYTES} bytes")
    return raw


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in (["compile"], ["verify"]):
        print(
            "usage: python -m revenue.ohsu_erp_rfp_2027_0005.source_bound {compile|verify}",
            file=sys.stderr,
        )
        return 2
    try:
        obj = _parse_strict_json(_read_stdin(), "stdin")
        if not isinstance(obj, dict):
            raise ContractError("stdin root must be object")
        if args == ["compile"]:
            _require_keys(obj, exact={"schema", "facts"}, where="compile input")
            if obj["schema"] != SCHEMA_INPUT:
                raise ContractError("compile input schema invalid")
            out = compile_current(obj["facts"])
        else:
            _require_keys(obj, exact={"schema", "facts", "packet"}, where="verify input")
            if obj["schema"] != SCHEMA_VERIFY_INPUT:
                raise ContractError("verify input schema invalid")
            verify_current(obj["packet"], obj["facts"])
            out = {
                "schema": "ohsu-erp-source-bound-verification/v1",
                "valid": True,
                "packet_sha256": obj["packet"]["packet_sha256"],
            }
        sys.stdout.buffer.write(_canonical(out) + b"\n")
        return 0
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
