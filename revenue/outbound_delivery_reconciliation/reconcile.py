from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

REPORT_SCHEMA = "outbound-delivery-reconciliation-report/v1"
ORIGINAL_SCHEMA = "outbound-delivery-original/v1"
EVENT_SCHEMA = "outbound-delivery-provider-event/v1"
FAILURE_REASONS = {
    "NO_SUCH_USER",
    "MAILBOX_FULL",
    "POLICY_OR_GROUP_RESTRICTION",
    "REMOTE_REJECTION",
    "UNKNOWN_PERMANENT_FAILURE",
}
EVENT_KINDS = {"PERMANENT_FAILURE", "PROVIDER_ACCEPTED"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+={}\-]{0,191}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,252}[a-z0-9]$|^[a-z0-9]$")
_RECIPIENT_RE = re.compile(r"^[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+$")
MAX_EVENTS = 1000


class ReconciliationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReconciliationError(f"value is not canonical-JSON serializable: {exc}") from exc


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def _exact_keys(value: Any, expected: Iterable[str], where: str) -> Dict[str, Any]:
    if type(value) is not dict:
        raise ReconciliationError(f"{where} must be an object")
    expected_set = set(expected)
    got = set(value)
    if got != expected_set:
        raise ReconciliationError(
            f"{where} keys mismatch missing={sorted(expected_set-got)} extra={sorted(got-expected_set)}"
        )
    return value


def _text(value: Any, where: str, *, maximum: int = 192) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ReconciliationError(f"{where} must be non-empty text <= {maximum} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ReconciliationError(f"{where} contains control characters")
    return value


def _opaque_id(value: Any, where: str) -> str:
    value = _text(value, where)
    if not _ID_RE.fullmatch(value):
        raise ReconciliationError(f"{where} is not a safe opaque id")
    return value


def _digest(value: Any, where: str) -> str:
    value = _text(value, where, maximum=64)
    if not _SHA_RE.fullmatch(value):
        raise ReconciliationError(f"{where} must be lowercase sha256")
    return value


def _recipient(value: Any, where: str) -> str:
    raw = _text(value, where, maximum=254)
    if raw != raw.strip():
        raise ReconciliationError(f"{where} must not have surrounding whitespace")
    normalized = raw.lower()
    if not _RECIPIENT_RE.fullmatch(normalized):
        raise ReconciliationError(f"{where} must be a single email-like route")
    return normalized


def _scope(value: Any, where: str) -> str:
    raw = _text(value, where, maximum=253)
    if raw != raw.strip() or raw != raw.lower() or not _SCOPE_RE.fullmatch(raw):
        raise ReconciliationError(f"{where} must be a canonical lowercase buyer scope")
    return raw


def _utc(value: Any, where: str) -> datetime:
    text = _text(value, where, maximum=20)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        raise ReconciliationError(f"{where} must be canonical UTC whole seconds")
    try:
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ReconciliationError(f"{where} is not a valid timestamp") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise ReconciliationError(f"{where} is not canonical UTC")
    return dt


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ReconciliationError("as_of must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_original(value: Mapping[str, Any]) -> Dict[str, Any]:
    value = _exact_keys(
        value,
        {"schema", "provider_message_id", "recipient", "buyer_scope", "opportunity_id", "sent_at", "evidence_sha256"},
        "original",
    )
    if value["schema"] != ORIGINAL_SCHEMA:
        raise ReconciliationError("unsupported original schema")
    return {
        "schema": ORIGINAL_SCHEMA,
        "provider_message_id": _opaque_id(value["provider_message_id"], "original.provider_message_id"),
        "recipient": _recipient(value["recipient"], "original.recipient"),
        "buyer_scope": _scope(value["buyer_scope"], "original.buyer_scope"),
        "opportunity_id": _opaque_id(value["opportunity_id"], "original.opportunity_id"),
        "sent_at": _utc_text(_utc(value["sent_at"], "original.sent_at")),
        "evidence_sha256": _digest(value["evidence_sha256"], "original.evidence_sha256"),
    }


def _normalize_event(value: Mapping[str, Any], index: int) -> Dict[str, Any]:
    where = f"events[{index}]"
    value = _exact_keys(
        value,
        {"schema", "event_id", "provider_message_id", "recipient", "buyer_scope", "opportunity_id", "observed_at", "event_kind", "reason_code", "evidence_sha256"},
        where,
    )
    if value["schema"] != EVENT_SCHEMA:
        raise ReconciliationError(f"{where}.schema unsupported")
    kind = _text(value["event_kind"], f"{where}.event_kind", maximum=32)
    if kind not in EVENT_KINDS:
        raise ReconciliationError(f"{where}.event_kind unsupported")
    reason = value["reason_code"]
    if kind == "PERMANENT_FAILURE":
        reason = _text(reason, f"{where}.reason_code", maximum=64)
        if reason not in FAILURE_REASONS:
            raise ReconciliationError(f"{where}.reason_code unsupported")
    elif reason is not None:
        raise ReconciliationError(f"{where}.reason_code must be null for PROVIDER_ACCEPTED")
    return {
        "schema": EVENT_SCHEMA,
        "event_id": _opaque_id(value["event_id"], f"{where}.event_id"),
        "provider_message_id": _opaque_id(value["provider_message_id"], f"{where}.provider_message_id"),
        "recipient": _recipient(value["recipient"], f"{where}.recipient"),
        "buyer_scope": _scope(value["buyer_scope"], f"{where}.buyer_scope"),
        "opportunity_id": _opaque_id(value["opportunity_id"], f"{where}.opportunity_id"),
        "observed_at": _utc_text(_utc(value["observed_at"], f"{where}.observed_at")),
        "event_kind": kind,
        "reason_code": reason,
        "evidence_sha256": _digest(value["evidence_sha256"], f"{where}.evidence_sha256"),
    }


def _normalize_events(events: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise ReconciliationError(f"events must be a list with at most {MAX_EVENTS} rows")
    by_id: Dict[str, Dict[str, Any]] = {}
    conflicts: List[str] = []
    for index, value in enumerate(events):
        row = _normalize_event(value, index)
        prior = by_id.get(row["event_id"])
        if prior is None:
            by_id[row["event_id"]] = row
        elif canonical_json(prior) != canonical_json(row):
            conflicts.append(f"EVENT_ID_FORK:{row['event_id']}")
    return sorted(by_id.values(), key=lambda row: (row["observed_at"], row["event_id"])), sorted(set(conflicts))


def _source_generation(original: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> str:
    return sha256_json({"original": original, "events": list(events)})


def _compile_at(original: Mapping[str, Any], events: Sequence[Mapping[str, Any]], *, at: datetime) -> Dict[str, Any]:
    as_of = _utc_text(at)
    current_dt = _utc(as_of, "internal.as_of")
    original_n = _normalize_original(original)
    events_n, conflicts = _normalize_events(events)
    sent_at = _utc(original_n["sent_at"], "original.sent_at")

    holds = list(conflicts)
    if sent_at > current_dt:
        holds.append("ORIGINAL_SENT_FROM_FUTURE")

    event_kinds = set()
    failure_reasons = set()
    evidence_digests = {original_n["evidence_sha256"]}
    for row in events_n:
        evidence_digests.add(row["evidence_sha256"])
        observed = _utc(row["observed_at"], "event.observed_at")
        if observed < sent_at:
            holds.append(f"EVENT_BEFORE_SEND:{row['event_id']}")
        if observed > current_dt:
            holds.append(f"EVENT_FROM_FUTURE:{row['event_id']}")
        if row["provider_message_id"] != original_n["provider_message_id"]:
            holds.append(f"CROSS_MESSAGE_EVENT:{row['event_id']}")
        if row["recipient"] != original_n["recipient"]:
            holds.append(f"CROSS_RECIPIENT_EVENT:{row['event_id']}")
        if row["buyer_scope"] != original_n["buyer_scope"]:
            holds.append(f"CROSS_BUYER_EVENT:{row['event_id']}")
        if row["opportunity_id"] != original_n["opportunity_id"]:
            holds.append(f"CROSS_OPPORTUNITY_EVENT:{row['event_id']}")
        event_kinds.add(row["event_kind"])
        if row["event_kind"] == "PERMANENT_FAILURE":
            failure_reasons.add(row["reason_code"])

    if "PERMANENT_FAILURE" in event_kinds and "PROVIDER_ACCEPTED" in event_kinds:
        holds.append("INCOMPATIBLE_TERMINAL_PROVIDER_EVIDENCE")

    holds = sorted(set(holds))
    if holds:
        classification = "HOLD_CONFLICTING_PROVIDER_EVIDENCE"
        failed_route_dnr = "PERMANENT_FAILURE" in event_kinds
    elif "PERMANENT_FAILURE" in event_kinds:
        classification = "DELIVERY_FAILED"
        failed_route_dnr = True
    else:
        classification = "SENT_PENDING_PROVIDER_TRUTH"
        failed_route_dnr = False

    core = {
        "schema": REPORT_SCHEMA,
        "generated_at": as_of,
        "classification": classification,
        "provider_message_id": original_n["provider_message_id"],
        "recipient": original_n["recipient"],
        "buyer_scope": original_n["buyer_scope"],
        "opportunity_id": original_n["opportunity_id"],
        "source_generation_sha256": _source_generation(original_n, events_n),
        "provider_event_ids": [row["event_id"] for row in events_n],
        "provider_evidence_sha256": sorted(evidence_digests),
        "failure_reason_codes": sorted(failure_reasons),
        "hold_reasons": holds,
        "failed_route_dnr": failed_route_dnr,
        "alternate_route_authorized": False,
        "retry_authorized": False,
        "buyer_rejection_asserted": False,
        "buyer_opt_out_asserted": False,
        "buyer_acceptance_asserted": False,
        "payment_asserted": False,
        "cash_asserted": False,
        "revenue_asserted": False,
    }
    report = dict(core)
    report["receipt_sha256"] = sha256_json(core)
    return report


def reconcile(original: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Compile current delivery truth with a host-owned UTC clock and no send authority."""
    return _compile_at(original, events, at=datetime.now(timezone.utc))


def verify(report: Mapping[str, Any], original: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> bool:
    """Verify receipt integrity at its receipt-bound historical instant only."""
    if type(report) is not dict or report.get("schema") != REPORT_SCHEMA:
        return False
    try:
        generated_at = _utc(report.get("generated_at"), "report.generated_at")
        expected = _compile_at(original, events, at=generated_at)
    except (ReconciliationError, TypeError, ValueError):
        return False
    return canonical_json(report) == canonical_json(expected)
