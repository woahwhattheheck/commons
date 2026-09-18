"""Internal acceptance-evidence compiler for UNC AP automation pursuit.

This module is deliberately buyer-neutral at execution time.  It evaluates
retained research/source state and synthetic UAT evidence; it does not contact
UNC, submit to eVP, write PeopleSoft, move money, or recognize revenue.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any

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


from source_custody import (
    ContractError, canonical_bytes, load_strict_json, receipt,
    load_admitted_bundle,
)

# A SHA-256 of a reviewed manifest is a deployment/source-code decision, never
# an input field. No official buyer bundle has been retained by this package.
_SOURCE_ADMISSION_SHA256: str | None = None
_SOURCE_ROOT = Path(__file__).resolve().parent / "retained_source"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_admitted_sources() -> dict[str, Any] | None:
    if _SOURCE_ADMISSION_SHA256 is None:
        return None
    return load_admitted_bundle(_SOURCE_ROOT, _SOURCE_ADMISSION_SHA256)


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
    source = load_strict_json(canonical_bytes(source))
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

    checked_at = _utc_now()
    custody = None
    custody_error = None
    if checked_at >= due or observed >= due:
        state = "HOLD_DEADLINE"
    elif observed > checked_at:
        state = "HOLD_FUTURE_SOURCE"
    elif checked_at - observed > timedelta(hours=24):
        state = "HOLD_STALE_SOURCE"
    elif source["status"] != "OPEN":
        state = "HOLD_NOT_OPEN"
    elif source_hash is None:
        state = "HOLD_SOURCE_BYTES"
    elif not source["addenda_complete"]:
        state = "HOLD_ADDENDA"
    else:
        try:
            custody = _load_admitted_sources()
        except ContractError as exc:
            custody_error = str(exc)
            state = "HOLD_SOURCE_CUSTODY"
        else:
            if custody is None:
                state = "HOLD_SOURCE_MANIFEST"
            else:
                trusted = custody["source"]
                trusted_due = _parse_time(trusted["offer_due_at"], "admitted offer_due_at")
                if checked_at >= trusted_due:
                    state = "HOLD_DEADLINE"
                elif canonical_bytes(source) != canonical_bytes(trusted):
                    state = "HOLD_SOURCE_GENERATION"
                else:
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
        "checked_at": checked_at.isoformat(),
        "source_input_sha256": receipt(source),
        "custody": custody,
        "custody_error": custody_error,
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
    case = load_strict_json(canonical_bytes(case))
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
    if type(mode) is not str or mode not in {"NONE", "TWO_WAY", "THREE_WAY"}:
        raise ContractError("match_mode unsupported")

    for name in ("purchase_order_amount_cents", "receipt_amount_cents"):
        value = case[name]
        if value is not None and (not _is_exact_int(value) or value < 0):
            raise ContractError(f"{name} must be null or non-negative int")

    integration = case["integration"]
    if type(integration) is not dict:
        raise ContractError("integration must be object")
    retained_keys = {"request", "ack", "attempts"}
    if set(integration) not in (_INTEGRATION_KEYS, _INTEGRATION_KEYS | retained_keys):
        raise ContractError("integration requires all retained evidence fields or legacy fields only")
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

    integration_bound = _integration_is_bound(case, integration)

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
    elif not integration_bound:
        disposition = "HOLD_INTEGRATION"
    elif integration["effect_count"] != 1:
        disposition = "HOLD_INTEGRATION"
    elif integration["retry_count"] > 0 and retry_effect_key != effect_key:
        disposition = "HOLD_INTEGRATION"
    elif not _ordered_contains(events, _REQUIRED_AUDIT):
        disposition = "HOLD_AUDIT"

    result = {
        "invoice_id": invoice_id,
        "supplier_id": supplier_id,
        "expected_amount_cents": case["expected_amount_cents"],
        "extracted_amount_cents": case["extracted_amount_cents"],
        "case_input_sha256": receipt(case),
        "integration_evidence_bound": integration_bound,
        "evidence_class": "RETAINED_UAT_CONSISTENCY_ONLY",
        "match_mode": mode,
        "extraction_accuracy_basis_points": accuracy_bp,
        "internal_threshold_basis_points": extraction_threshold_basis_points,
        "disposition": disposition,
        "people_soft_effect_key": effect_key,
        "audit_sequence_complete": _ordered_contains(events, _REQUIRED_AUDIT),
    }
    result["receipt_sha256"] = receipt(result)
    return result


def expected_request(case: dict[str, Any]) -> dict[str, Any]:
    """The USD-only staging contract; any business-input change remints the key."""
    core = {key: case[key] for key in _CASE_KEYS - {"integration", "audit_events"}}
    return {
        "version": 1,
        "system": "PEOPLESOFT",
        "operation": "STAGE_AP_INVOICE",
        "invoice_id": case["invoice_id"],
        "supplier_id": case["extracted_supplier_id"],
        "amount_cents": case["extracted_amount_cents"],
        "currency": "USD",
        "case_generation_sha256": receipt(core),
    }


def _integration_is_bound(case: dict[str, Any], integration: dict[str, Any]) -> bool:
    if "request" not in integration:
        return False
    wanted_request = expected_request(case)
    request = integration["request"]
    request_sha = receipt(wanted_request)
    wanted_effect = f"peoplesoft:ap:{case['invoice_id']}:{request_sha}"
    wanted_ack = {
        "version": 1,
        "system": "PEOPLESOFT",
        "invoice_id": case["invoice_id"],
        "request_sha256": request_sha,
        "effect_key": wanted_effect,
        "outcome": "STAGED",
        "effect_count": 1,
    }
    ack_sha = receipt(wanted_ack)
    # Canonical byte equality prevents True == 1 and dict-subclass coercion.
    if canonical_bytes(request) != canonical_bytes(wanted_request):
        return False
    if canonical_bytes(integration["ack"]) != canonical_bytes(wanted_ack):
        return False
    if (integration["request_sha256"] != request_sha
            or integration["ack_sha256"] != ack_sha
            or integration["effect_key"] != wanted_effect
            or integration["effect_count"] != 1):
        return False
    retries = integration["retry_count"]
    if retries > 100 or (retries == 0 and integration["retry_effect_key"] is not None):
        return False
    if retries > 0 and integration["retry_effect_key"] != wanted_effect:
        return False
    attempts = integration["attempts"]
    if type(attempts) is not list or len(attempts) != retries + 1:
        return False
    for number, attempt in enumerate(attempts):
        wanted = {"attempt": number, "request_sha256": request_sha,
                  "ack_sha256": ack_sha, "effect_key": wanted_effect}
        if canonical_bytes(attempt) != canonical_bytes(wanted):
            return False
    return True


_PARTNER_KEYS = {
    "name",
    "ap_automation_evidence",
    "peoplesoft_evidence",
    "route",
    "researched_at",
}


def compile_partner(candidate: Any) -> dict[str, Any]:
    candidate = load_strict_json(canonical_bytes(candidate))
    candidate = _require_exact_keys(candidate, _PARTNER_KEYS, "partner")
    name = _require_text(candidate["name"], "partner.name")
    ap = _require_text(candidate["ap_automation_evidence"], "ap_automation_evidence")
    ps = _require_text(candidate["peoplesoft_evidence"], "peoplesoft_evidence")
    route = _require_text(candidate["route"], "partner.route")
    researched = _parse_time(candidate["researched_at"], "partner.researched_at")
    del researched

    result = {
        "name": name,
        "partner_input_sha256": receipt(candidate),
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

    # Snapshot direct objects before evaluation so receipts bind the same values.
    source, cases, partners = load_strict_json(canonical_bytes([source, cases, partners]))
    if len(cases) > 1000 or len(partners) > 100:
        raise ContractError("bundle exceeds case/partner limits")
    case_ids = [_require_text(_require_exact_keys(case, _CASE_KEYS, "case")["invoice_id"], "invoice_id") for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ContractError("duplicate invoice_id in bundle")
    partner_ids = [_require_text(_require_exact_keys(partner, _PARTNER_KEYS, "partner")["name"], "partner.name") for partner in partners]
    if len(set(partner_ids)) != len(partner_ids):
        raise ContractError("duplicate partner name in bundle")
    cases.sort(key=lambda item: item["invoice_id"])
    partners.sort(key=lambda item: item["name"])
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
        "bundle_input_sha256": receipt({"source": source, "cases": cases, "partners": partners, "extraction_threshold_basis_points": extraction_threshold_basis_points}),
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
