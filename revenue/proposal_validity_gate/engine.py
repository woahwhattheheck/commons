from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

OFFER_SCHEMA = "proposal-validity-offer/v1"
CURRENT_SCHEMA = "proposal-validity-current/v1"
RECEIPT_SCHEMA = "proposal-validity-receipt/v1"
VERIFICATION_SCHEMA = "proposal-validity-verification/v1"

CURRENT_FOR_OWNER_USE = "CURRENT_FOR_OWNER_USE"
EXPIRED_REQUOTE_REQUIRED = "EXPIRED_REQUOTE_REQUIRED"
SUPERSEDED = "SUPERSEDED"
HOLD_NO_VALIDITY_BASIS = "HOLD_NO_VALIDITY_BASIS"
HOLD_SOURCE_DRIFT = "HOLD_SOURCE_DRIFT"

STATES = {
    CURRENT_FOR_OWNER_USE,
    EXPIRED_REQUOTE_REQUIRED,
    SUPERSEDED,
    HOLD_NO_VALIDITY_BASIS,
    HOLD_SOURCE_DRIFT,
}

AUTHORITY = {
    "external_send_authorized": False,
    "muse_elected": False,
    "buyer_accepted": False,
    "contract_authorized": False,
    "signature_authorized": False,
    "invoice_authorized": False,
    "payment_authorized": False,
    "cash_received": False,
    "revenue_recognized": False,
}

MAX_JSON_BYTES = 1_000_000
MAX_ID_LEN = 200
MAX_EVENTS = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ContractError(ValueError):
    """Stable fail-closed contract error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_constant(value: str) -> None:
    raise ContractError(f"nonfinite_number:{value}")


def _reject_float(value: str) -> None:
    raise ContractError(f"float_not_allowed:{value}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate_json_key:{key}")
        out[key] = value
    return out


def strict_json_loads(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise ContractError("json_bytes_required")
    if len(raw) > MAX_JSON_BYTES:
        raise ContractError("input_too_large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("utf8_required") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("invalid_json") from exc


def _exact_keys(obj: Any, expected: set[str], where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise ContractError(f"{where}_object_required")
    actual = set(obj)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractError(f"{where}_keys:missing={missing}:extra={extra}")
    return obj


def _text(value: Any, where: str, *, max_len: int = MAX_ID_LEN) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise ContractError(f"{where}_text")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ContractError(f"{where}_control_character")
    return value


def _sha256(value: Any, where: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{where}_sha256")
    return value


def _currency(value: Any, where: str) -> str:
    if type(value) is not str or _CURRENCY_RE.fullmatch(value) is None:
        raise ContractError(f"{where}_currency")
    return value


def _timestamp(value: Any, where: str) -> datetime:
    if type(value) is not str or _TIMESTAMP_RE.fullmatch(value) is None:
        raise ContractError(f"{where}_timestamp_utc")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ContractError(f"{where}_timestamp_utc") from exc
    return parsed


def _timestamp_or_none(value: Any, where: str) -> datetime | None:
    if value is None:
        return None
    return _timestamp(value, where)


def _canonical_timestamp(value: datetime) -> str:
    value = _utc_datetime(value, "timestamp")
    if value.microsecond:
        raise ContractError("timestamp_microseconds_not_allowed")
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_datetime(value: Any, where: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ContractError(f"{where}_aware_datetime_required")
    normalized = value.astimezone(UTC)
    if normalized.utcoffset() != timedelta(0):
        raise ContractError(f"{where}_utc_required")
    if normalized.microsecond:
        raise ContractError(f"{where}_whole_second_required")
    return normalized


def _validate_validity(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("validity_object_required")
    kind = value.get("kind")
    if kind == "NONE":
        _exact_keys(value, {"kind"}, "validity")
        return {"kind": "NONE"}
    if kind == "UNTIL":
        _exact_keys(value, {"kind", "valid_until_utc"}, "validity")
        _timestamp(value["valid_until_utc"], "validity.valid_until_utc")
        return dict(value)
    if kind == "DAYS":
        _exact_keys(value, {"kind", "days"}, "validity")
        days = value["days"]
        if type(days) is not int or not (1 <= days <= 3650):
            raise ContractError("validity.days_integer_range")
        return dict(value)
    raise ContractError("validity.kind")


def _validate_payment_rail(value: Any, where: str) -> dict[str, Any] | None:
    if value is None:
        return None
    obj = _exact_keys(
        value,
        {"rail_id", "rail_revision", "checkout_ref_sha256", "state"},
        where,
    )
    _text(obj["rail_id"], f"{where}.rail_id")
    _text(obj["rail_revision"], f"{where}.rail_revision")
    _sha256(obj["checkout_ref_sha256"], f"{where}.checkout_ref_sha256")
    if obj["state"] not in {"ACTIVE", "INACTIVE", "REPLACED", "WITHDRAWN"}:
        raise ContractError(f"{where}.state")
    return dict(obj)


def validate_offer(obj: Any) -> dict[str, Any]:
    obj = _exact_keys(
        obj,
        {
            "schema",
            "opportunity_id",
            "offer_id",
            "source_generation",
            "source_digest_sha256",
            "pricing_revision",
            "currency",
            "scope_sha256",
            "economics_sha256",
            "issued_at_utc",
            "validity",
            "buyer_deadline_utc",
            "payment_rail",
        },
        "offer",
    )
    if obj["schema"] != OFFER_SCHEMA:
        raise ContractError("offer.schema")
    _text(obj["opportunity_id"], "offer.opportunity_id")
    _text(obj["offer_id"], "offer.offer_id")
    _text(obj["source_generation"], "offer.source_generation")
    _sha256(obj["source_digest_sha256"], "offer.source_digest_sha256")
    _text(obj["pricing_revision"], "offer.pricing_revision")
    _currency(obj["currency"], "offer.currency")
    _sha256(obj["scope_sha256"], "offer.scope_sha256")
    _sha256(obj["economics_sha256"], "offer.economics_sha256")
    issued = _timestamp(obj["issued_at_utc"], "offer.issued_at_utc")
    validity = _validate_validity(obj["validity"])
    deadline = _timestamp_or_none(obj["buyer_deadline_utc"], "offer.buyer_deadline_utc")
    if deadline is not None and deadline <= issued:
        raise ContractError("offer.buyer_deadline_not_after_issued")
    if validity["kind"] == "UNTIL":
        valid_until = _timestamp(validity["valid_until_utc"], "validity.valid_until_utc")
        if valid_until <= issued:
            raise ContractError("offer.valid_until_not_after_issued")
    _validate_payment_rail(obj["payment_rail"], "offer.payment_rail")
    return dict(obj)


def _validate_event(value: Any, opportunity_id: str) -> dict[str, Any]:
    obj = _exact_keys(
        value,
        {
            "event_id",
            "kind",
            "opportunity_id",
            "supersedes_offer_id",
            "observed_at_utc",
            "source_digest_sha256",
        },
        "supersession_event",
    )
    _text(obj["event_id"], "supersession_event.event_id")
    if obj["kind"] not in {"AMENDMENT", "REDLINE", "CHANGE_ORDER", "REPRICE", "WITHDRAWAL"}:
        raise ContractError("supersession_event.kind")
    _text(obj["opportunity_id"], "supersession_event.opportunity_id")
    if obj["opportunity_id"] != opportunity_id:
        raise ContractError("supersession_event.opportunity_mismatch")
    _text(obj["supersedes_offer_id"], "supersession_event.supersedes_offer_id")
    _timestamp(obj["observed_at_utc"], "supersession_event.observed_at_utc")
    _sha256(obj["source_digest_sha256"], "supersession_event.source_digest_sha256")
    return dict(obj)


def validate_current(obj: Any) -> dict[str, Any]:
    obj = _exact_keys(
        obj,
        {
            "schema",
            "opportunity_id",
            "source_generation",
            "source_digest_sha256",
            "source_status",
            "source_observed_at_utc",
            "pricing_revision",
            "currency",
            "scope_sha256",
            "economics_sha256",
            "buyer_deadline_utc",
            "supersession_events",
            "payment_rail",
        },
        "current",
    )
    if obj["schema"] != CURRENT_SCHEMA:
        raise ContractError("current.schema")
    opportunity_id = _text(obj["opportunity_id"], "current.opportunity_id")
    _text(obj["source_generation"], "current.source_generation")
    _sha256(obj["source_digest_sha256"], "current.source_digest_sha256")
    if obj["source_status"] not in {"CURRENT", "STALE", "WITHDRAWN"}:
        raise ContractError("current.source_status")
    _timestamp(obj["source_observed_at_utc"], "current.source_observed_at_utc")
    _text(obj["pricing_revision"], "current.pricing_revision")
    _currency(obj["currency"], "current.currency")
    _sha256(obj["scope_sha256"], "current.scope_sha256")
    _sha256(obj["economics_sha256"], "current.economics_sha256")
    _timestamp_or_none(obj["buyer_deadline_utc"], "current.buyer_deadline_utc")
    events = obj["supersession_events"]
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise ContractError("current.supersession_events")
    validated = [_validate_event(event, opportunity_id) for event in events]
    event_ids = [event["event_id"] for event in validated]
    if len(event_ids) != len(set(event_ids)):
        raise ContractError("current.duplicate_event_id")
    source_observed = _timestamp(obj["source_observed_at_utc"], "current.source_observed_at_utc")
    for event in validated:
        if event["source_digest_sha256"] != obj["source_digest_sha256"]:
            raise ContractError("supersession_event_source_digest_mismatch")
        if _timestamp(event["observed_at_utc"], "supersession_event.observed_at_utc") > source_observed:
            raise ContractError("supersession_event_after_source_observation")
    _validate_payment_rail(obj["payment_rail"], "current.payment_rail")
    return dict(obj)


def _effective_valid_until(offer: dict[str, Any]) -> datetime | None:
    validity = offer["validity"]
    kind = validity["kind"]
    if kind == "NONE":
        return None
    if kind == "UNTIL":
        return _timestamp(validity["valid_until_utc"], "validity.valid_until_utc")
    issued = _timestamp(offer["issued_at_utc"], "offer.issued_at_utc")
    return issued + timedelta(days=validity["days"])


def _binding_payment_rail(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "rail_id": value["rail_id"],
        "rail_revision": value["rail_revision"],
        "checkout_ref_sha256": value["checkout_ref_sha256"],
        "state": value["state"],
    }


def _source_drift(offer: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[str]]:
    changed: list[str] = []
    reasons: list[str] = []
    for field in (
        "source_generation",
        "source_digest_sha256",
        "pricing_revision",
        "currency",
        "scope_sha256",
        "economics_sha256",
        "buyer_deadline_utc",
    ):
        if offer[field] != current[field]:
            changed.append(field)
            reasons.append(f"{field}_drift")
    if current["source_status"] != "CURRENT":
        changed.append("source_status")
        reasons.append(f"source_status_{str(current['source_status']).lower()}")
    offer_rail = _binding_payment_rail(offer["payment_rail"])
    current_rail = _binding_payment_rail(current["payment_rail"])
    if offer_rail != current_rail:
        changed.append("payment_rail")
        reasons.append("payment_rail_drift")
    elif offer_rail is not None and offer_rail["state"] != "ACTIVE":
        changed.append("payment_rail")
        reasons.append("payment_rail_not_active")
    return sorted(set(changed)), sorted(set(reasons))


def _owner_reapproval_fields(state: str, changed_fields: list[str]) -> list[str]:
    if state == CURRENT_FOR_OWNER_USE:
        return []
    if state == HOLD_NO_VALIDITY_BASIS:
        return ["validity"]
    if state == EXPIRED_REQUOTE_REQUIRED:
        return sorted(
            {
                "validity",
                "pricing_revision",
                "currency",
                "scope_sha256",
                "economics_sha256",
                "payment_rail",
            }
        )
    if state == SUPERSEDED:
        return sorted(
            {
                "source_generation",
                "source_digest_sha256",
                "pricing_revision",
                "currency",
                "scope_sha256",
                "economics_sha256",
                "buyer_deadline_utc",
                "payment_rail",
            }
        )
    return sorted(set(changed_fields))


def _semantic_hash(receipt_without_hash: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(receipt_without_hash))


def _offer_input_hash(offer: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(offer))


def _current_input_hash(current: dict[str, Any]) -> str:
    normalized = dict(current)
    normalized["supersession_events"] = sorted(
        current["supersession_events"], key=lambda e: (e["observed_at_utc"], e["event_id"])
    )
    return sha256_bytes(canonical_bytes(normalized))


def compile_at(offer_raw: bytes, current_raw: bytes, now_utc: datetime) -> dict[str, Any]:
    now = _utc_datetime(now_utc, "now_utc")
    offer = validate_offer(strict_json_loads(offer_raw))
    current = validate_current(strict_json_loads(current_raw))

    if offer["opportunity_id"] != current["opportunity_id"]:
        raise ContractError("opportunity_mismatch")

    issued = _timestamp(offer["issued_at_utc"], "offer.issued_at_utc")
    observed = _timestamp(current["source_observed_at_utc"], "current.source_observed_at_utc")
    if issued > now:
        raise ContractError("offer_issued_in_future")
    if observed > now:
        raise ContractError("current_source_observed_in_future")

    all_events = sorted(current["supersession_events"], key=lambda e: (e["observed_at_utc"], e["event_id"]))
    for event in all_events:
        if _timestamp(event["observed_at_utc"], "supersession_event.observed_at_utc") > now:
            raise ContractError("supersession_event_observed_in_future")
    relevant_events = [event for event in all_events if event["supersedes_offer_id"] == offer["offer_id"]]

    changed_fields, drift_reasons = _source_drift(offer, current)
    reasons: list[str] = []

    if relevant_events:
        state = SUPERSEDED
        changed_fields = sorted(set(changed_fields + ["supersession_events"]))
        reasons.extend(f"superseded_by_{event['kind'].lower()}" for event in relevant_events)
    elif changed_fields:
        state = HOLD_SOURCE_DRIFT
        reasons.extend(drift_reasons)
    elif offer["validity"]["kind"] == "NONE":
        state = HOLD_NO_VALIDITY_BASIS
        changed_fields = ["validity"]
        reasons.append("no_validity_basis")
    else:
        valid_until = _effective_valid_until(offer)
        buyer_deadline = _timestamp_or_none(offer["buyer_deadline_utc"], "offer.buyer_deadline_utc")
        if valid_until is not None and now >= valid_until:
            reasons.append("validity_expired")
        if buyer_deadline is not None and now >= buyer_deadline:
            reasons.append("buyer_deadline_passed")
        state = EXPIRED_REQUOTE_REQUIRED if reasons else CURRENT_FOR_OWNER_USE
        if state == EXPIRED_REQUOTE_REQUIRED:
            changed_fields = ["time"]

    reasons = sorted(set(reasons))
    requote_delta = {
        "required": state != CURRENT_FOR_OWNER_USE,
        "changed_fields": sorted(set(changed_fields)),
        "superseding_event_ids": sorted(event["event_id"] for event in relevant_events),
        "reasons": reasons,
        "owner_reapproval_fields": _owner_reapproval_fields(state, changed_fields),
    }

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "opportunity_id": offer["opportunity_id"],
        "offer_id": offer["offer_id"],
        "evaluated_at_utc": _canonical_timestamp(now),
        "currentness_state": state,
        "offer_sha256": _offer_input_hash(offer),
        "current_sha256": _current_input_hash(current),
        "source_binding": {
            "offer_generation": offer["source_generation"],
            "offer_digest_sha256": offer["source_digest_sha256"],
            "current_generation": current["source_generation"],
            "current_digest_sha256": current["source_digest_sha256"],
            "current_status": current["source_status"],
            "current_observed_at_utc": current["source_observed_at_utc"],
        },
        "offer_binding": {
            "pricing_revision": offer["pricing_revision"],
            "currency": offer["currency"],
            "scope_sha256": offer["scope_sha256"],
            "economics_sha256": offer["economics_sha256"],
            "issued_at_utc": offer["issued_at_utc"],
            "validity": offer["validity"],
            "buyer_deadline_utc": offer["buyer_deadline_utc"],
            "payment_rail": offer["payment_rail"],
        },
        "current_binding": {
            "pricing_revision": current["pricing_revision"],
            "currency": current["currency"],
            "scope_sha256": current["scope_sha256"],
            "economics_sha256": current["economics_sha256"],
            "buyer_deadline_utc": current["buyer_deadline_utc"],
            "payment_rail": current["payment_rail"],
        },
        "supersession_events": relevant_events,
        "requote_delta": requote_delta,
        "authority": dict(AUTHORITY),
    }
    receipt["semantic_sha256"] = _semantic_hash(receipt)
    return receipt


def compile_current(offer_raw: bytes, current_raw: bytes) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0)
    return compile_at(offer_raw, current_raw, now)


def _validate_receipt_shape(receipt: Any) -> dict[str, Any]:
    obj = _exact_keys(
        receipt,
        {
            "schema",
            "opportunity_id",
            "offer_id",
            "evaluated_at_utc",
            "currentness_state",
            "offer_sha256",
            "current_sha256",
            "source_binding",
            "offer_binding",
            "current_binding",
            "supersession_events",
            "requote_delta",
            "authority",
            "semantic_sha256",
        },
        "receipt",
    )
    if obj["schema"] != RECEIPT_SCHEMA:
        raise ContractError("receipt.schema")
    _text(obj["opportunity_id"], "receipt.opportunity_id")
    _text(obj["offer_id"], "receipt.offer_id")
    _timestamp(obj["evaluated_at_utc"], "receipt.evaluated_at_utc")
    if obj["currentness_state"] not in STATES:
        raise ContractError("receipt.currentness_state")
    _sha256(obj["offer_sha256"], "receipt.offer_sha256")
    _sha256(obj["current_sha256"], "receipt.current_sha256")
    _sha256(obj["semantic_sha256"], "receipt.semantic_sha256")
    if obj["authority"] != AUTHORITY:
        raise ContractError("receipt.authority")
    return dict(obj)


def verify_at(
    offer_raw: bytes,
    current_raw: bytes,
    receipt_raw: bytes,
    now_utc: datetime,
) -> dict[str, Any]:
    now = _utc_datetime(now_utc, "now_utc")
    receipt = _validate_receipt_shape(strict_json_loads(receipt_raw))

    current_offer = validate_offer(strict_json_loads(offer_raw))
    current_record = validate_current(strict_json_loads(current_raw))
    if receipt["offer_sha256"] != _offer_input_hash(current_offer):
        raise ContractError("receipt_offer_semantics_mismatch")
    if receipt["current_sha256"] != _current_input_hash(current_record):
        raise ContractError("receipt_current_semantics_mismatch")

    supplied_semantic = receipt["semantic_sha256"]
    unhashed = dict(receipt)
    del unhashed["semantic_sha256"]
    if supplied_semantic != _semantic_hash(unhashed):
        raise ContractError("receipt_semantic_hash_mismatch")

    evaluated = _timestamp(receipt["evaluated_at_utc"], "receipt.evaluated_at_utc")
    if evaluated > now:
        raise ContractError("receipt_evaluated_in_future")

    exact = compile_at(offer_raw, current_raw, evaluated)
    if exact != receipt:
        raise ContractError("receipt_exact_recompile_mismatch")

    fresh = compile_at(offer_raw, current_raw, now)
    if fresh["currentness_state"] != receipt["currentness_state"]:
        raise ContractError(
            f"current_state_drift:{receipt['currentness_state']}->{fresh['currentness_state']}"
        )

    return {
        "schema": VERIFICATION_SCHEMA,
        "verified": True,
        "currentness_state": fresh["currentness_state"],
        "evaluated_at_utc": receipt["evaluated_at_utc"],
        "verified_at_utc": _canonical_timestamp(now),
        "semantic_sha256": receipt["semantic_sha256"],
        "authority": dict(AUTHORITY),
    }


def verify_current(offer_raw: bytes, current_raw: bytes, receipt_raw: bytes) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0)
    return verify_at(offer_raw, current_raw, receipt_raw, now)
