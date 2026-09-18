"""Internal acceptance-evidence compiler for UNC AP automation pursuit.

This module is deliberately buyer-neutral at execution time.  It evaluates
retained research/source state and synthetic UAT evidence; it does not contact
UNC, submit to eVP, write PeopleSoft, move money, or recognize revenue.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any, Iterable

SOLICITATION_ID = "65-RFP062926KJM"
BUYER = "University of North Carolina at Chapel Hill"
FIRST_PARTY_URL = (
    "https://evp.nc.gov/solicitations/details/"
    "?id=9c0cbdc8-f373-f111-ab0d-001dd800b811"
)
COMMERCIAL_HYPOTHESIS_USD = 12_000
COMMERCIAL_STATE = "PROPOSED_NOT_ACCEPTED"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_AUDIT = (
    "received",
    "extracted",
    "validated",
    "matched",
    "routing_started",
    "routing_completed",
    "erp_staged",
)


class ContractError(ValueError):
    """Raised when an input violates the compiler contract."""


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON constant: {value}")


def _pairs_no_duplicates(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_strict_json(raw: str) -> Any:
    """Parse JSON while rejecting duplicate keys and NaN/Infinity."""
    return json.loads(
        raw,
        object_pairs_hook=_pairs_no_duplicates,
        parse_constant=_reject_constant,
    )


def canonical_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError(f"not canonical-json encodable: {exc}") from exc
    return encoded.encode("utf-8")


def receipt(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_exact_int(value: Any) -> bool:
    return type(value) is int


def _is_exact_bool(value: Any) -> bool:
    return type(value) is bool


def _require_exact_keys(obj: Any, required: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise ContractError(f"{label} must be object")
    keys = set(obj)
    missing = required - keys
    extra = keys - required
    if missing or extra:
        raise ContractError(
            f"{label} keys mismatch missing={sorted(missing)} extra={sorted(extra)}"
        )
    return obj


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ContractError(f"{label} must be non-empty string")
    return value


def _require_hash(value: Any, label: str, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ContractError(f"{label} must be lowercase sha256")
    return value


def _parse_time(value: Any, label: str) -> datetime:
    text = _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{label} must include timezone")
    return parsed


_SOURCE_KEYS = {
    "buyer",
    "solicitation_id",
    "first_party_url",
    "status",
    "observed_at",
    "offer_due_at",
    "exact_current_bytes_sha256",
    "addenda_complete",
}


def compile_source(source: Any) -> dict[str, Any]:
    """Compile research/source state into a fail-closed internal posture."""
    source = _require_exact_keys(source, _SOURCE_KEYS, "source")
    if source["buyer"] != BUYER:
        raise ContractError("buyer identity drift")
    if source["solicitation_id"] != SOLICITATION_ID:
        raise ContractError("solicitation identity drift")
    if source["first_party_url"] != FIRST_PARTY_URL:
        raise ContractError("first-party URL drift")
    if source["status"] != "OPEN":
        state = "HOLD_NOT_OPEN"
    else:
        state = "SOURCE_CANDIDATE"

    observed = _parse_time(source["observed_at"], "observed_at")
    due = _parse_time(source["offer_due_at"], "offer_due_at")
    source_hash = _require_hash(
        source["exact_current_bytes_sha256"],
        "exact_current_bytes_sha256",
        allow_none=True,
    )
    if not _is_exact_bool(source["addenda_complete"]):
        raise ContractError("addenda_complete must be bool")

    if observed >= due:
        state = "HOLD_DEADLINE"
    elif source_hash is None:
        state = "HOLD_SOURCE_BYTES"
    elif not source["addenda_complete"]:
        state = "HOLD_ADDENDA"
    elif state == "SOURCE_CANDIDATE":
        state = "SOURCE_BOUND"

    compiled = {
        "buyer": BUYER,
        "solicitation_id": SOLICITATION_ID,
        "first_party_url": FIRST_PARTY_URL,
        "status": source["status"],
        "observed_at": source["observed_at"],
        "offer_due_at": source["offer_due_at"],
        "exact_current_bytes_sha256": source_hash,
        "addenda_complete": source["addenda_complete"],
        "state": state,
        "authority": {
            "buyer_contact": False,
            "partner_contact": False,
            "evp_mutation": False,
            "submission": False,
            "peoplesoft_write": False,
            "payment": False,
            "contract_acceptance": False,
            "revenue_recognition": False,
        },
    }
    compiled["receipt_sha256"] = receipt(compiled)
    return compiled


_INTEGRATION_KEYS = {
    "request_sha256",
    "ack_sha256",
    "effect_key",
    "retry_effect_key",
    "effect_count",
    "retry_count",
}

_CASE_KEYS = {
    "invoice_id",
    "supplier_id",
    "extracted_supplier_id",
    "expected_amount_cents",
    "extracted_amount_cents",
    "match_mode",
    "purchase_order_amount_cents",
    "receipt_amount_cents",
    "routing_signoff_needed",
    "routing_signoff_present",
    "extraction_fields_total",
    "extraction_fields_correct",
    "duplicate_seen",
    "integration",
    "audit_events",
}


def _ordered_contains(events: list[str], required: tuple[str, ...]) -> bool:
    position = 0
    for event in events:
        if position < len(required) and event == required[position]:
            position += 1
    return position == len(required)


def evaluate_invoice_case(
    case: Any,
    *,
    extraction_threshold_basis_points: int,
) -> dict[str, Any]:
    """Evaluate one synthetic invoice/UAT evidence case deterministically."""
    case = _require_exact_keys(case, _CASE_KEYS, "case")
    invoice_id = _require_text(case["invoice_id"], "invoice_id")
    supplier_id = _require_text(case["supplier_id"], "supplier_id")
    extracted_supplier = _require_text(
        case["extracted_supplier_id"], "extracted_supplier_id"
    )

    for name in (
        "expected_amount_cents",
        "extracted_amount_cents",
        "extraction_fields_total",
        "extraction_fields_correct",
    ):
        if not _is_exact_int(case[name]):
            raise ContractError(f"{name} must be int")
    if case["expected_amount_cents"] < 0 or case["extracted_amount_cents"] < 0:
        raise ContractError("amount cents must be non-negative")
    if case["extraction_fields_total"] <= 0:
        raise ContractError("extraction_fields_total must be positive")
    if not 0 <= case["extraction_fields_correct"] <= case["extraction_fields_total"]:
        raise ContractError("extraction_fields_correct out of range")

    if not _is_exact_int(extraction_threshold_basis_points):
        raise ContractError("extraction threshold must be int")
    if not 0 <= extraction_threshold_basis_points <= 10_000:
        raise ContractError("extraction threshold out of range")

    for name in (
        "routing_signoff_needed",
        "routing_signoff_present",
        "duplicate_seen",
    ):
        if not _is_exact_bool(case[name]):
            raise ContractError(f"{name} must be bool")

    mode = case["match_mode"]
    if mode not in {"NONE", "TWO_WAY", "THREE_WAY"}:
        raise ContractError("match_mode unsupported")

    for name in ("purchase_order_amount_cents", "receipt_amount_cents"):
        value = case[name]
        if value is not None and (not _is_exact_int(value) or value < 0):
            raise ContractError(f"{name} must be null or non-negative int")

    integration = _require_exact_keys(case["integration"], _INTEGRATION_KEYS, "integration")
    _require_hash(integration["request_sha256"], "request_sha256")
    _require_hash(integration["ack_sha256"], "ack_sha256")
    effect_key = _require_text(integration["effect_key"], "effect_key")
    retry_effect_key = integration["retry_effect_key"]
    if retry_effect_key is not None and (
        type(retry_effect_key) is not str or not retry_effect_key
    ):
        raise ContractError("retry_effect_key must be null or non-empty string")
    for name in ("effect_count", "retry_count"):
        if not _is_exact_int(integration[name]) or integration[name] < 0:
            raise ContractError(f"{name} must be non-negative int")

    events = case["audit_events"]
    if type(events) is not list or not all(type(event) is str for event in events):
        raise ContractError("audit_events must be list[str]")
    if len(set(events)) != len(events):
        raise ContractError("audit_events must not contain duplicates")

    accuracy_bp = (
        case["extraction_fields_correct"] * 10_000 // case["extraction_fields_total"]
    )

    disposition = "PASS"
    if case["duplicate_seen"]:
        disposition = "HOLD_DUPLICATE"
    elif accuracy_bp < extraction_threshold_basis_points:
        disposition = "HOLD_EXTRACTION"
    elif supplier_id != extracted_supplier:
        disposition = "HOLD_SUPPLIER"
    elif case["expected_amount_cents"] != case["extracted_amount_cents"]:
        disposition = "HOLD_AMOUNT"
    elif mode == "TWO_WAY" and (
        case["purchase_order_amount_cents"] is None
        or case["purchase_order_amount_cents"] != case["expected_amount_cents"]
    ):
        disposition = "HOLD_MATCH"
    elif mode == "THREE_WAY" and (
        case["purchase_order_amount_cents"] is None
        or case["receipt_amount_cents"] is None
        or case["purchase_order_amount_cents"] != case["expected_amount_cents"]
        or case["receipt_amount_cents"] != case["expected_amount_cents"]
    ):
        disposition = "HOLD_MATCH"
    elif case["routing_signoff_needed"] and not case["routing_signoff_present"]:
        disposition = "HOLD_ROUTING_SIGNOFF"
    elif integration["effect_count"] != 1:
        disposition = "HOLD_INTEGRATION"
    elif integration["retry_count"] > 0 and retry_effect_key != effect_key:
        disposition = "HOLD_INTEGRATION"
    elif not _ordered_contains(events, _REQUIRED_AUDIT):
        disposition = "HOLD_AUDIT"

    result = {
        "invoice_id": invoice_id,
        "match_mode": mode,
        "extraction_accuracy_basis_points": accuracy_bp,
        "internal_threshold_basis_points": extraction_threshold_basis_points,
        "disposition": disposition,
        "people_soft_effect_key": effect_key,
        "audit_sequence_complete": _ordered_contains(events, _REQUIRED_AUDIT),
    }
    result["receipt_sha256"] = receipt(result)
    return result


_PARTNER_KEYS = {
    "name",
    "ap_automation_evidence",
    "peoplesoft_evidence",
    "route",
    "researched_at",
}


def compile_partner(candidate: Any) -> dict[str, Any]:
    candidate = _require_exact_keys(candidate, _PARTNER_KEYS, "partner")
    name = _require_text(candidate["name"], "partner.name")
    ap = _require_text(candidate["ap_automation_evidence"], "ap_automation_evidence")
    ps = _require_text(candidate["peoplesoft_evidence"], "peoplesoft_evidence")
    route = _require_text(candidate["route"], "partner.route")
    researched = _parse_time(candidate["researched_at"], "partner.researched_at")
    del researched

    result = {
        "name": name,
        "qualification_state": "RESEARCH_CANDIDATE",
        "ap_automation_evidence": ap,
        "peoplesoft_evidence": ps,
        "route": route,
        "outbound_authorized": False,
        "muse_clearance": False,
    }
    result["receipt_sha256"] = receipt(result)
    return result


def compile_bundle(
    source: Any,
    cases: Any,
    partners: Any,
    *,
    extraction_threshold_basis_points: int = 9_900,
) -> dict[str, Any]:
    if type(cases) is not list or not cases:
        raise ContractError("cases must be non-empty list")
    if type(partners) is not list or not partners:
        raise ContractError("partners must be non-empty list")

    source_result = compile_source(source)
    case_results = [
        evaluate_invoice_case(
            case,
            extraction_threshold_basis_points=extraction_threshold_basis_points,
        )
        for case in cases
    ]
    partner_results = [compile_partner(candidate) for candidate in partners]

    if source_result["state"] != "SOURCE_BOUND":
        state = source_result["state"]
    elif any(case["disposition"] != "PASS" for case in case_results):
        state = "HOLD_UAT"
    else:
        state = "INTERNAL_WORKSHARE_READY"

    bundle = {
        "pursuit": "UNC_AP_AI_PEOPLESOFT",
        "commercial_hypothesis_usd": COMMERCIAL_HYPOTHESIS_USD,
        "commercial_state": COMMERCIAL_STATE,
        "booked_revenue_usd": 0,
        "cash_received_usd": 0,
        "source": source_result,
        "cases": case_results,
        "partners": partner_results,
        "state": state,
        "authority": {
            "buyer_contact": False,
            "partner_contact": False,
            "submission": False,
            "peoplesoft_write": False,
            "payment": False,
            "contract_acceptance": False,
            "revenue_recognition": False,
        },
    }
    bundle["receipt_sha256"] = receipt(bundle)
    return bundle
