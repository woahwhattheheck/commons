from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any

SCHEMA = "tjlabs.umissouri-27-0012-finance-pursuit/v1"
PARTNER_SCHEMA = "tjlabs.umissouri-27-0012-partners/v1"
CASE_SCHEMA = "tjlabs.umissouri-27-0012-reconciliation-case/v1"
BUNDLE_SCHEMA = "tjlabs.umissouri-27-0012-finance-evidence-bundle/v1"

SOLICITATION_ID = "27-0012"
BUYER = "University of Missouri System"
TITLE = "Payables Program and Merchant Services"
DUE_UTC = "2026-09-25T19:00:00Z"
QUESTION_CUTOFF_UTC = "2026-09-10T19:00:00Z"
MAX_SOURCE_AGE_SECONDS = 48 * 60 * 60

AUTHORITY_FALSE = {
    "buyer_contact_authorized": False,
    "partner_contact_authorized": False,
    "submission_authorized": False,
    "contract_acceptance_authorized": False,
    "banking_authorized": False,
    "merchant_acquiring_authorized": False,
    "card_issuance_authorized": False,
    "payment_authorized": False,
    "production_erp_write_authorized": False,
    "compliance_certification_authorized": False,
    "revenue_recognized": False,
}

TERMINAL_DECISIONS = (
    "EVIDENCE_READY",
    "REJECT_SENSITIVE_DATA",
    "HOLD_MISSING_SETTLEMENT",
    "HOLD_MERCHANT_TOTAL_MISMATCH",
    "HOLD_GL_MAPPING",
    "HOLD_CHARGEBACK_EXCEPTION",
    "HOLD_PAYABLES_SUPPLIER",
    "HOLD_FUTURE_ERP",
    "HOLD_AUDIT_CHAIN",
    "HOLD_STALE_EVIDENCE",
)

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class ContractError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON constant rejected: {value}")


def strict_loads(text: str) -> Any:
    if type(text) is not str:
        raise ContractError("JSON input must be str")

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ContractError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=_reject_constant)
    except ContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc


def strict_load(path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return strict_loads(handle.read())


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError(f"not canonicalizable: {exc}") from exc


def sha256_hex(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _add_receipt(value: dict[str, Any]) -> dict[str, Any]:
    base = dict(value)
    base.pop("receipt_sha256", None)
    base["receipt_sha256"] = sha256_hex(canonical_json(base))
    return base


def _exact(obj: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise ContractError(f"{label}: object required")
    got = set(obj)
    if got != keys:
        raise ContractError(
            f"{label}: exact keys required; "
            f"missing={sorted(keys - got)} extra={sorted(got - keys)}"
        )
    return obj


def _text(value: Any, label: str, max_len: int = 1024) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise ContractError(f"{label}: bounded non-empty string required")
    return value


def _id(value: Any, label: str) -> str:
    value = _text(value, label, 128)
    if not _ID.fullmatch(value):
        raise ContractError(f"{label}: invalid identifier")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{label}: bool required")
    return value


def _int(value: Any, label: str, low: int = 0, high: int = 10**15) -> int:
    if type(value) is not int or not (low <= value <= high):
        raise ContractError(f"{label}: integer in [{low},{high}] required")
    return value


def _utc(value: Any, label: str) -> datetime:
    value = _text(value, label, 40)
    if not value.endswith("Z"):
        raise ContractError(f"{label}: UTC Z timestamp required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{label}: invalid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ContractError(f"{label}: UTC required")
    return parsed


def _https(value: Any, label: str) -> str:
    value = _text(value, label, 2048)
    if not value.startswith("https://"):
        raise ContractError(f"{label}: https URL required")
    return value


def _validate_authority(obj: Any, label: str) -> None:
    authority = _exact(obj, set(AUTHORITY_FALSE), label)
    for field in AUTHORITY_FALSE:
        if _bool(authority[field], f"{label}.{field}") is not False:
            raise ContractError(f"{label}.{field}: must remain false")


def validate_manifest(manifest: Any, trusted_as_of: str) -> dict[str, Any]:
    doc = _exact(
        manifest,
        {
            "schema",
            "solicitation",
            "source_evidence",
            "buyer_packet",
            "requirements",
            "commercial_offer",
            "authority",
        },
        "manifest",
    )
    if doc["schema"] != SCHEMA:
        raise ContractError("manifest.schema: unsupported")

    sol = _exact(
        doc["solicitation"],
        {"id", "buyer", "title", "due_utc", "question_cutoff_utc"},
        "manifest.solicitation",
    )
    if (
        sol["id"] != SOLICITATION_ID
        or sol["buyer"] != BUYER
        or sol["title"] != TITLE
    ):
        raise ContractError("manifest.solicitation: solicitation identity drift")
    if (
        sol["due_utc"] != DUE_UTC
        or sol["question_cutoff_utc"] != QUESTION_CUTOFF_UTC
    ):
        raise ContractError("manifest.solicitation: deadline drift")

    as_of = _utc(trusted_as_of, "trusted_as_of")
    source = _exact(
        doc["source_evidence"],
        {"notice", "scope"},
        "manifest.source_evidence",
    )
    source_fresh = True
    for key in ("notice", "scope"):
        row = _exact(
            source[key],
            {"url", "captured_at_utc", "source_class"},
            f"manifest.source_evidence.{key}",
        )
        _https(row["url"], f"manifest.source_evidence.{key}.url")
        if row["source_class"] not in {
            "SECONDARY_PUBLIC_INDEX",
            "PROVIDER_PUBLIC",
            "BUYER_PUBLIC",
        }:
            raise ContractError(
                f"manifest.source_evidence.{key}.source_class: unsupported"
            )
        captured = _utc(
            row["captured_at_utc"],
            f"manifest.source_evidence.{key}.captured_at_utc",
        )
        if captured > as_of:
            raise ContractError("manifest.source_evidence: future capture")
        if int((as_of - captured).total_seconds()) > MAX_SOURCE_AGE_SECONDS:
            source_fresh = False

    buyer_packet = _exact(
        doc["buyer_packet"],
        {"retained", "sha256", "authority"},
        "manifest.buyer_packet",
    )
    retained = _bool(
        buyer_packet["retained"], "manifest.buyer_packet.retained"
    )
    digest = buyer_packet["sha256"]
    if retained:
        raise ContractError(
            "manifest.buyer_packet.retained: verifier-owned packet bytes "
            "are required; caller metadata cannot mint buyer authority"
        )
    if digest is not None or buyer_packet["authority"] != "NOT_RETAINED":
        raise ContractError(
            "manifest.buyer_packet: absent packet must remain unasserted"
        )

    req = _exact(
        doc["requirements"],
        {
            "merchant_services",
            "payables_program",
            "current_peoplesoft_integration",
            "future_erp_support",
            "reconciliation_reporting",
            "fraud_liability_controls",
            "commercial_card_epayables",
            "security_questionnaires",
            "accessibility_evidence",
        },
        "manifest.requirements",
    )
    for field in req:
        if _bool(req[field], f"manifest.requirements.{field}") is not True:
            raise ContractError(
                f"manifest.requirements.{field}: requirement cannot be weakened"
            )

    offer = _exact(
        doc["commercial_offer"],
        {
            "state",
            "fixed_fee_usd_cents",
            "optional_cutover_usd_cents",
            "name",
            "external_send_authorized",
        },
        "manifest.commercial_offer",
    )
    if offer["state"] != "PROPOSED_NOT_ACCEPTED":
        raise ContractError(
            "manifest.commercial_offer.state: must remain PROPOSED_NOT_ACCEPTED"
        )
    if (
        _int(
            offer["fixed_fee_usd_cents"],
            "manifest.commercial_offer.fixed_fee_usd_cents",
            1,
            100_000_000,
        )
        != 1_800_000
    ):
        raise ContractError(
            "manifest.commercial_offer.fixed_fee_usd_cents: reference fee drift"
        )
    if (
        _int(
            offer["optional_cutover_usd_cents"],
            "manifest.commercial_offer.optional_cutover_usd_cents",
            0,
            100_000_000,
        )
        != 600_000
    ):
        raise ContractError(
            "manifest.commercial_offer.optional_cutover_usd_cents: reference option drift"
        )
    if (
        _text(offer["name"], "manifest.commercial_offer.name", 180)
        != "Payables and Merchant Reconciliation Acceptance Workshare"
    ):
        raise ContractError(
            "manifest.commercial_offer.name: exact bounded offer required"
        )
    if (
        _bool(
            offer["external_send_authorized"],
            "manifest.commercial_offer.external_send_authorized",
        )
        is not False
    ):
        raise ContractError(
            "manifest.commercial_offer.external_send_authorized: must remain false"
        )

    _validate_authority(doc["authority"], "manifest.authority")

    packet = {
        "schema": SCHEMA,
        "solicitation_id": SOLICITATION_ID,
        "source_authority_state": (
            "BUYER_PACKET_RETAINED"
            if retained
            else "HOLD_BUYER_PACKET_REQUIRED"
        ),
        "teaming_build_state": (
            "HOLD_RESPONSE_WINDOW"
            if as_of >= _utc(DUE_UTC, "due")
            else (
                "READY_FOR_PARTNER_REVIEW"
                if source_fresh
                else "HOLD_SOURCE_REFRESH_REQUIRED"
            )
        ),
        "direct_prime_state": "HOLD_PRIME_CAPABILITY_REQUIRED",
        "commercial_offer_state": offer["state"],
        "fixed_fee_usd_cents": offer["fixed_fee_usd_cents"],
        "optional_cutover_usd_cents": offer["optional_cutover_usd_cents"],
        **AUTHORITY_FALSE,
    }
    return _add_receipt(packet)


def evaluate_partner(candidate: Any) -> dict[str, Any]:
    row = _exact(
        candidate,
        {
            "partner_id",
            "name",
            "evidence_url",
            "evidence_class",
            "public_merchant_capability",
            "public_payables_or_card_capability",
            "public_higher_ed_or_public_sector_fit",
            "peoplesoft_or_erp_fit_confirmed",
            "rfp_participation_confirmed",
            "contact_authorized",
            "evidence_note",
        },
        "partner",
    )
    partner_id = _id(row["partner_id"], "partner.partner_id")
    name = _text(row["name"], "partner.name", 200)
    _https(row["evidence_url"], "partner.evidence_url")
    if row["evidence_class"] not in {"BUYER_PUBLIC", "PROVIDER_PUBLIC"}:
        raise ContractError("partner.evidence_class: unsupported")
    merchant = _bool(
        row["public_merchant_capability"],
        "partner.public_merchant_capability",
    )
    payables = _bool(
        row["public_payables_or_card_capability"],
        "partner.public_payables_or_card_capability",
    )
    sector = _bool(
        row["public_higher_ed_or_public_sector_fit"],
        "partner.public_higher_ed_or_public_sector_fit",
    )
    erp = _bool(
        row["peoplesoft_or_erp_fit_confirmed"],
        "partner.peoplesoft_or_erp_fit_confirmed",
    )
    rfp = _bool(
        row["rfp_participation_confirmed"],
        "partner.rfp_participation_confirmed",
    )
    if _bool(row["contact_authorized"], "partner.contact_authorized") is not False:
        raise ContractError("partner.contact_authorized: must remain false")
    _text(row["evidence_note"], "partner.evidence_note", 1000)

    public_fit = merchant and payables and sector
    if not public_fit:
        status = "HOLD_PUBLIC_FIT_GAP"
    elif not erp:
        status = "RESEARCH_ERP_INTEGRATION"
    else:
        status = "QUALIFIED_FOR_HUMAN_PARTNER_REVIEW"

    return _add_receipt(
        {
            "schema": PARTNER_SCHEMA,
            "partner_id": partner_id,
            "name": name,
            "status": status,
            "rfp_participation_confirmed": rfp,
            "contact_authorized": False,
            "selection_authorized": False,
            "external_send_authorized": False,
        }
    )


def evaluate_partners(document: Any) -> dict[str, Any]:
    doc = _exact(document, {"schema", "candidates"}, "partners")
    if doc["schema"] != PARTNER_SCHEMA:
        raise ContractError("partners.schema: unsupported")
    rows = doc["candidates"]
    if type(rows) is not list or not (3 <= len(rows) <= 12):
        raise ContractError("partners.candidates: 3..12 candidates required")

    seen = set()
    results = []
    for raw in rows:
        result = evaluate_partner(raw)
        if result["partner_id"] in seen:
            raise ContractError("partners: duplicate partner_id")
        seen.add(result["partner_id"])
        results.append(result)

    return _add_receipt(
        {
            "schema": PARTNER_SCHEMA,
            "candidate_count": len(results),
            "candidates": results,
            "selection_authorized": False,
            "external_send_authorized": False,
        }
    )


def evaluate_reconciliation_case(
    case: Any, trusted_as_of: str
) -> dict[str, Any]:
    row = _exact(
        case,
        {
            "schema",
            "case_id",
            "merchant_id",
            "settlement_file_present",
            "processor_total_cents",
            "erp_total_cents",
            "gl_mapping_complete",
            "unresolved_chargeback_count",
            "payables_supplier_match",
            "future_erp_contract_evidenced",
            "audit_chain_complete",
            "sensitive_cardholder_data_present",
            "observed_at_utc",
        },
        "case",
    )
    if row["schema"] != CASE_SCHEMA:
        raise ContractError("case.schema: unsupported")

    case_id = _id(row["case_id"], "case.case_id")
    merchant_id = _id(row["merchant_id"], "case.merchant_id")
    settlement = _bool(
        row["settlement_file_present"], "case.settlement_file_present"
    )
    processor = _int(row["processor_total_cents"], "case.processor_total_cents")
    erp = _int(row["erp_total_cents"], "case.erp_total_cents")
    gl = _bool(row["gl_mapping_complete"], "case.gl_mapping_complete")
    chargebacks = _int(
        row["unresolved_chargeback_count"],
        "case.unresolved_chargeback_count",
        0,
        1_000_000,
    )
    supplier = _bool(
        row["payables_supplier_match"], "case.payables_supplier_match"
    )
    future_erp = _bool(
        row["future_erp_contract_evidenced"],
        "case.future_erp_contract_evidenced",
    )
    audit = _bool(row["audit_chain_complete"], "case.audit_chain_complete")
    sensitive = _bool(
        row["sensitive_cardholder_data_present"],
        "case.sensitive_cardholder_data_present",
    )
    observed = _utc(row["observed_at_utc"], "case.observed_at_utc")
    as_of = _utc(trusted_as_of, "trusted_as_of")
    if observed > as_of:
        raise ContractError("case.observed_at_utc: future evidence")
    age_seconds = int((as_of - observed).total_seconds())

    if sensitive:
        decision = "REJECT_SENSITIVE_DATA"
    elif age_seconds > 7 * 24 * 3600:
        decision = "HOLD_STALE_EVIDENCE"
    elif not settlement:
        decision = "HOLD_MISSING_SETTLEMENT"
    elif processor != erp:
        decision = "HOLD_MERCHANT_TOTAL_MISMATCH"
    elif not gl:
        decision = "HOLD_GL_MAPPING"
    elif chargebacks:
        decision = "HOLD_CHARGEBACK_EXCEPTION"
    elif not supplier:
        decision = "HOLD_PAYABLES_SUPPLIER"
    elif not future_erp:
        decision = "HOLD_FUTURE_ERP"
    elif not audit:
        decision = "HOLD_AUDIT_CHAIN"
    else:
        decision = "EVIDENCE_READY"

    return _add_receipt(
        {
            "schema": CASE_SCHEMA,
            "case_id": case_id,
            "merchant_id": merchant_id,
            "decision": decision,
            "variance_cents": processor - erp,
            "unresolved_chargeback_count": chargebacks,
            "evidence_age_seconds": age_seconds,
            **AUTHORITY_FALSE,
        }
    )


def evaluate_matrix(document: Any, trusted_as_of: str) -> dict[str, Any]:
    doc = _exact(document, {"schema", "cases"}, "matrix")
    if doc["schema"] != CASE_SCHEMA:
        raise ContractError("matrix.schema: unsupported")
    rows = doc["cases"]
    if type(rows) is not list or len(rows) < len(TERMINAL_DECISIONS):
        raise ContractError("matrix.cases: terminal coverage required")

    seen = set()
    counts = {decision: 0 for decision in TERMINAL_DECISIONS}
    results = []
    for index, raw in enumerate(rows):
        wrap = _exact(
            raw,
            {"expected_decision", "case"},
            f"matrix.cases[{index}]",
        )
        expected = _text(
            wrap["expected_decision"],
            f"matrix.cases[{index}].expected_decision",
            64,
        )
        if expected not in counts:
            raise ContractError(
                f"matrix.cases[{index}].expected_decision: unsupported"
            )
        result = evaluate_reconciliation_case(wrap["case"], trusted_as_of)
        if result["case_id"] in seen:
            raise ContractError("matrix: duplicate case_id")
        seen.add(result["case_id"])
        if result["decision"] != expected:
            raise ContractError(
                f"matrix.cases[{index}]: expected {expected}, "
                f"got {result['decision']}"
            )
        counts[expected] += 1
        results.append(result)

    missing = [key for key, count in counts.items() if count == 0]
    if missing:
        raise ContractError(f"matrix: missing terminal decisions {missing}")

    return _add_receipt(
        {
            "schema": CASE_SCHEMA,
            "case_count": len(results),
            "decision_counts": counts,
            "results": results,
            **AUTHORITY_FALSE,
        }
    )


def compile_bundle(
    manifest: Any,
    partners: Any,
    matrix: Any,
    trusted_as_of: str,
) -> dict[str, Any]:
    pursuit = validate_manifest(manifest, trusted_as_of)
    partner_result = evaluate_partners(partners)
    matrix_result = evaluate_matrix(matrix, trusted_as_of)

    return _add_receipt(
        {
            "schema": BUNDLE_SCHEMA,
            "solicitation_id": SOLICITATION_ID,
            "pursuit": pursuit,
            "partners": partner_result,
            "reconciliation_matrix": matrix_result,
            "partner_outreach_state": "HOLD_MUSE_ARBITRATION_REQUIRED",
            "submission_state": (
                "HOLD_BUYER_PACKET_REQUIRED"
                if pursuit["source_authority_state"]
                != "BUYER_PACKET_RETAINED"
                else "OWNER_REVIEW_REQUIRED"
            ),
            **AUTHORITY_FALSE,
        }
    )


def verify_bundle(
    bundle: Any,
    manifest: Any,
    partners: Any,
    matrix: Any,
    trusted_as_of: str,
) -> bool:
    if type(bundle) is not dict:
        return False
    return canonical_json(bundle) == canonical_json(
        compile_bundle(manifest, partners, matrix, trusted_as_of)
    )
