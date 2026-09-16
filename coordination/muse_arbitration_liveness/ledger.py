# SPDX-License-Identifier: MIT
"""Deterministic, offline evidence ledger for Muse arbitration request liveness.

This module has no publication, provider, or writer-selection authority.  It
classifies supplied evidence at a caller-supplied audit instant only.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

SCHEMA_VERSION = 1
MODE = "HISTORICAL_EVIDENCE_ONLY"
MAX_JSON_BYTES = 1_048_576
MAX_EVENTS = 10_000
MAX_TEXT = 512
MAX_AGE_SECONDS = 604_800
HEX = frozenset("0123456789abcdef")
EVENT_TYPES = frozenset({"REQUEST", "DECISION", "SEND_RECEIPT"})
DECISIONS = frozenset({"SELECTED", "HOLD", "COLLISION", "OTHER"})
STATUSES = frozenset({
    "PENDING_DECISION",
    "OWNER_REVIEW_RESUBMIT_DUE",
    "MALFORMED_OR_UNDERBOUND_DECISION",
    "HOLD_OR_COLLISION",
    "SELECTED_AWAITING_SEND_RECEIPT",
    "OWNER_REVIEW_STALE_SELECTION",
    "SENT_DNR",
    "CONFLICT",
})

AUTHORITY = {
    "can_select_writer": False,
    "can_resubmit": False,
    "can_reassign_lease": False,
    "can_send_external": False,
    "can_mutate_provider": False,
    "can_contact_counterparty": False,
    "can_assert_acceptance": False,
    "can_assert_payment": False,
    "can_recognize_revenue": False,
}

class LedgerError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise LedgerError(f"non-finite JSON value {value!r} is not allowed")


def _strict_int(text: str) -> int:
    if len(text.lstrip("-")) > 18:
        raise LedgerError("integer token is too large")
    return int(text)


def _pairs(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise LedgerError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def loads_strict(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise LedgerError("input must be strict UTF-8") from exc
    try:
        return json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
            parse_int=_strict_int,
        )
    except LedgerError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise LedgerError("invalid strict JSON") from exc


def _canonical(value: Any) -> bytes:
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return text.encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise LedgerError("value cannot be canonically encoded") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _obj(value: Any, label: str, keys: Iterable[str]) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise LedgerError(f"{label} must be an object")
    expected = set(keys)
    actual = set(value)
    if actual != expected:
        raise LedgerError(f"{label} keys mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > MAX_TEXT or "\x00" in value:
        raise LedgerError(f"{label} must be a non-empty bounded string")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _text(value, label)
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise LedgerError(f"{label} must be lowercase SHA-256 hex")
    return value


def _int(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or value < low or value > high:
        raise LedgerError(f"{label} must be an integer in [{low}, {high}]")
    return value


def _utc(value: Any, label: str) -> datetime:
    value = _text(value, label)
    if len(value) != 20 or not value.endswith("Z"):
        raise LedgerError(f"{label} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise LedgerError(f"{label} must be canonical UTC seconds") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise LedgerError(f"{label} must be canonical UTC seconds")
    return parsed


def _age_seconds(now: datetime, then: datetime) -> int:
    delta = int((now - then).total_seconds())
    return delta


def _tuple_from_event(event: Mapping[str, Any], prefix: str = "") -> Tuple[str, str, str, str, str, str]:
    return (
        _text(event[prefix + "request_key"], prefix + "request_key"),
        _text(event[prefix + "seat_id"], prefix + "seat_id"),
        _text(event[prefix + "counterparty_key"], prefix + "counterparty_key"),
        _sha256(event[prefix + "route_sha256"], prefix + "route_sha256"),
        _sha256(event[prefix + "purpose_sha256"], prefix + "purpose_sha256"),
        _text(event[prefix + "retry_policy_generation"], prefix + "retry_policy_generation"),
    )


def _binding_from_event(event: Mapping[str, Any]) -> Tuple[Any, Any, Any, Any, Any, Any]:
    keys = (
        "bound_request_key", "bound_seat_id", "bound_counterparty_key",
        "bound_route_sha256", "bound_purpose_sha256", "bound_retry_policy_generation",
    )
    values: List[Any] = []
    for key in keys:
        value = event[key]
        if value is None:
            values.append(None)
        elif key.endswith("_sha256"):
            values.append(_sha256(value, key))
        else:
            values.append(_text(value, key))
    return tuple(values)  # type: ignore[return-value]


def _validate_event(raw: Any, index: int) -> Dict[str, Any]:
    base_keys = {"type", "provider_event_id", "provider_event_sha256", "observed_at"}
    if type(raw) is not dict:
        raise LedgerError(f"events[{index}] must be an object")
    kind = raw.get("type")
    if kind not in EVENT_TYPES:
        raise LedgerError(f"events[{index}].type invalid")
    if kind == "REQUEST":
        keys = base_keys | {
            "request_key", "seat_id", "counterparty_key", "route_sha256",
            "purpose_sha256", "retry_policy_generation",
        }
    elif kind == "DECISION":
        keys = base_keys | {
            "decision", "bound_request_key", "bound_seat_id", "bound_counterparty_key",
            "bound_route_sha256", "bound_purpose_sha256", "bound_retry_policy_generation",
        }
    else:
        keys = base_keys | {
            "bound_request_key", "bound_seat_id", "bound_counterparty_key",
            "bound_route_sha256", "bound_purpose_sha256", "bound_retry_policy_generation",
        }
    event = dict(_obj(raw, f"events[{index}]", keys))
    _text(event["provider_event_id"], f"events[{index}].provider_event_id")
    _sha256(event["provider_event_sha256"], f"events[{index}].provider_event_sha256")
    _utc(event["observed_at"], f"events[{index}].observed_at")
    if kind == "REQUEST":
        _tuple_from_event(event)
    else:
        _binding_from_event(event)
        if kind == "DECISION" and event["decision"] not in DECISIONS:
            raise LedgerError(f"events[{index}].decision invalid")
    return event


def compile_ledger(payload: Mapping[str, Any]) -> Dict[str, Any]:
    root = _obj(payload, "root", {"schema_version", "as_of_utc", "policy", "events"})
    if root["schema_version"] != SCHEMA_VERSION:
        raise LedgerError("unsupported schema_version")
    as_of_s = _text(root["as_of_utc"], "as_of_utc")
    as_of = _utc(as_of_s, "as_of_utc")
    policy = _obj(root["policy"], "policy", {"resubmit_after_seconds", "selection_stale_after_seconds"})
    resubmit_after = _int(policy["resubmit_after_seconds"], "resubmit_after_seconds", 1, MAX_AGE_SECONDS)
    selection_stale_after = _int(policy["selection_stale_after_seconds"], "selection_stale_after_seconds", 1, MAX_AGE_SECONDS)
    events_raw = root["events"]
    if type(events_raw) is not list or len(events_raw) > MAX_EVENTS:
        raise LedgerError("events must be a bounded list")
    events = [_validate_event(raw, i) for i, raw in enumerate(events_raw)]

    # Provider event identity is immutable. Exact replays collapse; same-id/different-bytes is conflict evidence.
    provider_digest: Dict[str, str] = {}
    provider_semantics: Dict[str, bytes] = {}
    identity_conflicts: set[str] = set()
    unique_events: List[Dict[str, Any]] = []
    seen_exact: set[bytes] = set()
    for event in events:
        eid = event["provider_event_id"]
        digest = event["provider_event_sha256"]
        semantic = _canonical(event)
        prior_digest = provider_digest.get(eid)
        prior_semantic = provider_semantics.get(eid)
        if prior_digest is not None and (prior_digest != digest or prior_semantic != semantic):
            identity_conflicts.add(eid)
        provider_digest[eid] = digest
        provider_semantics[eid] = semantic
        if semantic not in seen_exact:
            seen_exact.add(semantic)
            unique_events.append(event)

    requests: Dict[str, List[Dict[str, Any]]] = {}
    for event in unique_events:
        if event["type"] == "REQUEST":
            requests.setdefault(event["request_key"], []).append(event)

    # Decisions/receipts whose binding identifies a request key are routed to that key even when under-bound.
    routed: Dict[str, List[Dict[str, Any]]] = {key: [] for key in requests}
    orphan_events: List[str] = []
    for event in unique_events:
        if event["type"] == "REQUEST":
            continue
        key = event.get("bound_request_key")
        if type(key) is str and key in routed:
            routed[key].append(event)
        else:
            orphan_events.append(event["provider_event_id"])

    items: List[Dict[str, Any]] = []
    for key in sorted(requests):
        reqs = requests[key]
        tuple_values = [_tuple_from_event(event) for event in reqs]
        tuple_set = set(tuple_values)
        reasons: List[str] = []
        status = "PENDING_DECISION"
        canonical_tuple = sorted(tuple_set)[0]
        request_key, seat_id, counterparty_key, route_sha, purpose_sha, retry_gen = canonical_tuple
        request_times = sorted((_utc(event["observed_at"], "request observed_at"), event["provider_event_id"]) for event in reqs)
        first_request_at = request_times[0][0]
        latest_request_at = request_times[-1][0]

        if len(tuple_set) != 1:
            status = "CONFLICT"
            reasons.append("REQUEST_TUPLE_DRIFT")

        relevant = routed.get(key, [])
        if any(event["provider_event_id"] in identity_conflicts for event in reqs + relevant):
            status = "CONFLICT"
            reasons.append("PROVIDER_EVENT_ID_REUSED_WITH_CHANGED_SEMANTICS")
        if any(_utc(event["observed_at"], "event observed_at") > as_of for event in reqs + relevant):
            status = "CONFLICT"
            reasons.append("FUTURE_EVENT")

        decisions = [event for event in relevant if event["type"] == "DECISION"]
        sends = [event for event in relevant if event["type"] == "SEND_RECEIPT"]
        exact_decisions: List[Dict[str, Any]] = []
        underbound_decisions: List[Dict[str, Any]] = []
        for decision in decisions:
            binding = _binding_from_event(decision)
            when = _utc(decision["observed_at"], "decision observed_at")
            if when < first_request_at:
                status = "CONFLICT"
                reasons.append("DECISION_BEFORE_REQUEST")
            if binding == canonical_tuple:
                exact_decisions.append(decision)
            else:
                underbound_decisions.append(decision)

        exact_sends: List[Dict[str, Any]] = []
        for send in sends:
            binding = _binding_from_event(send)
            when = _utc(send["observed_at"], "send observed_at")
            if binding == canonical_tuple:
                exact_sends.append(send)
            else:
                status = "CONFLICT"
                reasons.append("CROSS_REQUEST_OR_UNDERBOUND_SEND")
            if when < first_request_at:
                status = "CONFLICT"
                reasons.append("SEND_BEFORE_REQUEST")

        if len(exact_sends) > 1:
            status = "CONFLICT"
            reasons.append("MULTIPLE_DISTINCT_SEND_RECEIPTS")

        exact_dispositions = {event["decision"] for event in exact_decisions}
        if len(exact_dispositions) > 1:
            status = "CONFLICT"
            reasons.append("CONTRADICTORY_EXACT_DECISIONS")

        if status != "CONFLICT":
            if exact_sends:
                selected = [event for event in exact_decisions if event["decision"] == "SELECTED"]
                if not selected:
                    status = "CONFLICT"
                    reasons.append("SEND_WITHOUT_EXACT_SELECTION")
                else:
                    selection_time = min(_utc(event["observed_at"], "selection observed_at") for event in selected)
                    if any(_utc(send["observed_at"], "send observed_at") < selection_time for send in exact_sends):
                        status = "CONFLICT"
                        reasons.append("SEND_BEFORE_SELECTION")
                    else:
                        status = "SENT_DNR"
                        reasons.append("EXACT_SEND_RECEIPT_PRESENT")
            elif exact_decisions:
                disposition = next(iter(exact_dispositions))
                latest_decision_at = max(_utc(event["observed_at"], "decision observed_at") for event in exact_decisions)
                if disposition in {"HOLD", "COLLISION"}:
                    status = "HOLD_OR_COLLISION"
                    reasons.append(f"MUSE_{disposition}")
                elif disposition == "SELECTED":
                    age = _age_seconds(as_of, latest_decision_at)
                    if age < 0:
                        status = "CONFLICT"
                        reasons.append("FUTURE_DECISION")
                    elif age >= selection_stale_after:
                        status = "OWNER_REVIEW_STALE_SELECTION"
                        reasons.append("SELECTION_WITHOUT_SEND_RECEIPT_EXCEEDS_POLICY")
                    else:
                        status = "SELECTED_AWAITING_SEND_RECEIPT"
                        reasons.append("EXACT_SELECTION_NO_SEND_RECEIPT")
                else:
                    status = "MALFORMED_OR_UNDERBOUND_DECISION"
                    reasons.append("NON_BINDING_DECISION_DISPOSITION")
            elif underbound_decisions:
                status = "MALFORMED_OR_UNDERBOUND_DECISION"
                reasons.append("DECISION_DOES_NOT_BIND_EXACT_REQUEST_TUPLE")
            else:
                age = _age_seconds(as_of, latest_request_at)
                if age < 0:
                    status = "CONFLICT"
                    reasons.append("FUTURE_REQUEST")
                elif age >= resubmit_after:
                    status = "OWNER_REVIEW_RESUBMIT_DUE"
                    reasons.append("UNANSWERED_REQUEST_EXCEEDS_POLICY")
                else:
                    status = "PENDING_DECISION"
                    reasons.append("UNANSWERED_REQUEST_WITHIN_POLICY")

        item = {
            "request_key": request_key,
            "seat_id": seat_id,
            "counterparty_key": counterparty_key,
            "route_sha256": route_sha,
            "purpose_sha256": purpose_sha,
            "retry_policy_generation": retry_gen,
            "attempt_count": len(reqs),
            "exact_decision_count": len(exact_decisions),
            "underbound_decision_count": len(underbound_decisions),
            "send_receipt_count": len(exact_sends),
            "first_requested_at": first_request_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latest_requested_at": latest_request_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status,
            "reasons": sorted(set(reasons)),
        }
        if status not in STATUSES:
            raise LedgerError("internal invalid status")
        items.append(item)

    counts = {status: 0 for status in sorted(STATUSES)}
    for item in items:
        counts[item["status"]] += 1
    normalized_input = {
        "schema_version": SCHEMA_VERSION,
        "as_of_utc": as_of_s,
        "policy": {
            "resubmit_after_seconds": resubmit_after,
            "selection_stale_after_seconds": selection_stale_after,
        },
        "events": sorted(events, key=lambda event: _canonical(event)),
    }
    body: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "as_of_utc": as_of_s,
        "policy": {
            "resubmit_after_seconds": resubmit_after,
            "selection_stale_after_seconds": selection_stale_after,
        },
        "input_sha256": _sha(normalized_input),
        "items": items,
        "summary": {
            "request_count": len(items),
            "orphan_event_count": len(orphan_events),
            "orphan_provider_event_ids": sorted(orphan_events),
            "status_counts": counts,
        },
        "authority": dict(AUTHORITY),
    }
    body["packet_sha256"] = _sha(body)
    return body


def verify_ledger(payload: Mapping[str, Any], packet: Mapping[str, Any]) -> bool:
    if type(packet) is not dict:
        return False
    try:
        expected = compile_ledger(payload)
        return _canonical(expected) == _canonical(packet)
    except LedgerError:
        return False


def read_json_file(path: str) -> Any:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise LedgerError(f"cannot open input: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LedgerError("input must be a regular file")
        if info.st_size > MAX_JSON_BYTES:
            raise LedgerError("input is too large")
        chunks: List[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_JSON_BYTES:
            raise LedgerError("input is too large")
        return loads_strict(raw)
    finally:
        os.close(fd)


def write_json_exclusive(path: str, value: Any) -> None:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8", "strict") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise LedgerError(f"refusing unsafe or existing output: {exc}") from exc
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise LedgerError("output write made no progress")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
