#!/usr/bin/env python3
"""Deterministic offline outbound delivery-truth compiler.

Provider submission is transport evidence, not delivery evidence. This module
consumes only retained evidence and never sends, retries, mutates providers,
authorizes an alternate route, or asserts payment/revenue.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

INPUT_SCHEMA = "commons.outbound-delivery-evidence/v1"
OUTPUT_SCHEMA = "commons.outbound-delivery-diagnostic/v1"
VERIFY_SCHEMA = "commons.outbound-delivery-verification/v1"
PROJECTION_SCHEMA = "commons.outbound-delivery-collision-projection/v1"
MAX_TEXT = 512
MAX_EVENTS = 128
MAX_INT = 2**53 - 1
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_STATUS_RE = re.compile(r"^([245])\.([0-9]{1,3})\.([0-9]{1,3})$")

AUTHORITY = {
    "send_authorized": False,
    "retry_authorized": False,
    "alternate_route_authorized": False,
    "provider_action_authorized": False,
    "buyer_acceptance": False,
    "payment_authorized": False,
    "cash_proven": False,
    "revenue_recognized": False,
}


class DeliveryTruthError(ValueError):
    """Stable domain error for malformed or contradictory retained evidence."""


def _text(value: Any, name: str, *, maximum: int = MAX_TEXT) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise DeliveryTruthError(f"{name} must be non-empty text <= {maximum} chars")
    if value != value.strip():
        raise DeliveryTruthError(f"{name} must not have leading/trailing whitespace")
    if unicodedata.normalize("NFC", value) != value:
        raise DeliveryTruthError(f"{name} must use NFC Unicode")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise DeliveryTruthError(f"{name} contains invalid Unicode") from exc
    visible = False
    for ch in value:
        cat = unicodedata.category(ch)
        if cat.startswith("C"):
            raise DeliveryTruthError(f"{name} contains control/format/surrogate codepoint")
        if not ch.isspace() and not cat.startswith("M"):
            visible = True
    if not visible:
        raise DeliveryTruthError(f"{name} must contain a visible base character")
    return value


def _sha(value: Any, name: str) -> str:
    value = _text(value, name, maximum=64)
    if not _SHA_RE.fullmatch(value):
        raise DeliveryTruthError(f"{name} must be lowercase SHA-256 hex")
    return value


def _utc(value: Any, name: str) -> tuple[str, int]:
    value = _text(value, name, maximum=32)
    if not value.endswith("Z"):
        raise DeliveryTruthError(f"{name} must be canonical whole-second UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DeliveryTruthError(f"{name} must be canonical whole-second UTC") from exc
    if parsed.tzinfo != timezone.utc or parsed.microsecond != 0:
        raise DeliveryTruthError(f"{name} must be canonical whole-second UTC")
    canonical = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    if canonical != value:
        raise DeliveryTruthError(f"{name} must be canonical whole-second UTC")
    return canonical, int(parsed.timestamp())


def _canonical(value: Any) -> bytes:
    if value is None or type(value) in (bool, int, str):
        if type(value) is int and not (-MAX_INT <= value <= MAX_INT):
            raise DeliveryTruthError("integer exceeds safe range")
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise DeliveryTruthError("invalid Unicode in canonical value") from exc
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    if type(value) is list:
        if len(value) > MAX_EVENTS * 4:
            raise DeliveryTruthError("array exceeds limit")
        return b"[" + b",".join(_canonical(x) for x in value) + b"]"
    if type(value) is dict:
        if len(value) > 128:
            raise DeliveryTruthError("object exceeds key limit")
        for key in value:
            if type(key) is not str:
                raise DeliveryTruthError("object keys must be text")
        return b"{" + b",".join(
            json.dumps(k, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            + b":"
            + _canonical(value[k])
            for k in sorted(value)
        ) + b"}"
    raise DeliveryTruthError("unsupported JSON type")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact_keys(value: Any, name: str, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeliveryTruthError(f"{name} must be object")
    actual = set(value)
    if actual != keys:
        raise DeliveryTruthError(
            f"{name} schema mismatch missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def _normalize_submission(raw: Any) -> dict[str, Any]:
    keys = {
        "operation_key",
        "counterparty",
        "purpose",
        "provider",
        "provider_message_id",
        "provider_thread_id",
        "sender",
        "recipient",
        "submitted_at",
        "source_ref",
        "source_sha256",
    }
    raw = _exact_keys(raw, "submission", keys)
    submitted_at, _ = _utc(raw["submitted_at"], "submission.submitted_at")
    return {
        "operation_key": _text(raw["operation_key"], "submission.operation_key", maximum=240),
        "counterparty": _text(raw["counterparty"], "submission.counterparty"),
        "purpose": _text(raw["purpose"], "submission.purpose"),
        "provider": _text(raw["provider"], "submission.provider", maximum=80),
        "provider_message_id": _text(
            raw["provider_message_id"], "submission.provider_message_id", maximum=240
        ),
        "provider_thread_id": _text(
            raw["provider_thread_id"], "submission.provider_thread_id", maximum=240
        ),
        "sender": _text(raw["sender"], "submission.sender", maximum=320).casefold(),
        "recipient": _text(raw["recipient"], "submission.recipient", maximum=320).casefold(),
        "submitted_at": submitted_at,
        "source_ref": _text(raw["source_ref"], "submission.source_ref"),
        "source_sha256": _sha(raw["source_sha256"], "submission.source_sha256"),
    }


def _normalize_event(raw: Any, idx: int) -> dict[str, Any]:
    keys = {
        "id",
        "kind",
        "observed_at",
        "provider",
        "original_message_id",
        "original_thread_id",
        "sender",
        "recipient",
        "action",
        "status",
        "diagnostic_code",
        "source_ref",
        "source_sha256",
    }
    raw = _exact_keys(raw, f"events[{idx}]", keys)
    kind = _text(raw["kind"], f"events[{idx}].kind", maximum=40)
    if kind not in {"DSN", "PROVIDER_DELIVERY_CONFIRMATION"}:
        raise DeliveryTruthError(f"events[{idx}].kind unsupported")
    action = _text(raw["action"], f"events[{idx}].action", maximum=40).casefold()
    status = _text(raw["status"], f"events[{idx}].status", maximum=32)
    if not _STATUS_RE.fullmatch(status):
        raise DeliveryTruthError(f"events[{idx}].status must be enhanced SMTP status")
    observed_at, _ = _utc(raw["observed_at"], f"events[{idx}].observed_at")
    return {
        "id": _text(raw["id"], f"events[{idx}].id", maximum=160),
        "kind": kind,
        "observed_at": observed_at,
        "provider": _text(raw["provider"], f"events[{idx}].provider", maximum=80),
        "original_message_id": _text(
            raw["original_message_id"], f"events[{idx}].original_message_id", maximum=240
        ),
        "original_thread_id": _text(
            raw["original_thread_id"], f"events[{idx}].original_thread_id", maximum=240
        ),
        "sender": _text(raw["sender"], f"events[{idx}].sender", maximum=320).casefold(),
        "recipient": _text(raw["recipient"], f"events[{idx}].recipient", maximum=320).casefold(),
        "action": action,
        "status": status,
        "diagnostic_code": _text(
            raw["diagnostic_code"], f"events[{idx}].diagnostic_code", maximum=512
        ),
        "source_ref": _text(raw["source_ref"], f"events[{idx}].source_ref"),
        "source_sha256": _sha(raw["source_sha256"], f"events[{idx}].source_sha256"),
    }


def _event_semantic(event: dict[str, Any]) -> str:
    """Semantic evidence identity independent of wrapper id/ref/blob reminting."""
    return _digest(
        {
            "kind": event["kind"],
            "provider": event["provider"],
            "original_message_id": event["original_message_id"],
            "original_thread_id": event["original_thread_id"],
            "sender": event["sender"],
            "recipient": event["recipient"],
            "action": event["action"],
            "status": event["status"],
            "diagnostic_code": event["diagnostic_code"],
        }
    )


def _classify(event: dict[str, Any]) -> str:
    match = _STATUS_RE.fullmatch(event["status"])
    if match is None:
        raise DeliveryTruthError("status lost validation")
    klass = match.group(1)
    if event["kind"] == "PROVIDER_DELIVERY_CONFIRMATION":
        if event["action"] == "delivered" and klass == "2":
            return "DELIVERED"
        return "AMBIGUOUS"
    if event["action"] == "failed" and klass == "5":
        return "HARD_FAILURE"
    if event["action"] in {"delayed", "failed"} and klass == "4":
        return "SOFT_FAILURE"
    if event["action"] == "delivered" and klass == "2":
        return "DELIVERED"
    return "AMBIGUOUS"


def normalize_packet(packet: Any) -> dict[str, Any]:
    if type(packet) is not dict:
        raise DeliveryTruthError("packet must be object")
    actual = set(packet)
    old_keys = {"schema", "submission", "events"}
    extended_keys = {"schema", "submission", "legacy_local_sent", "events"}
    if actual not in (old_keys, extended_keys):
        allowed = old_keys if "legacy_local_sent" not in actual else extended_keys
        raise DeliveryTruthError(
            f"packet schema mismatch missing={sorted(allowed-actual)} extra={sorted(actual-allowed)}"
        )
    if packet["schema"] != INPUT_SCHEMA:
        raise DeliveryTruthError("unsupported input schema")
    raw_submission = packet["submission"]
    raw_legacy = packet.get("legacy_local_sent")
    if raw_submission is not None and raw_legacy is not None:
        raise DeliveryTruthError("submission and legacy_local_sent are mutually exclusive")
    submission = _normalize_submission(raw_submission) if raw_submission is not None else None
    legacy = _normalize_submission(raw_legacy) if raw_legacy is not None else None
    active = submission if submission is not None else legacy
    raw_events = packet["events"]
    if type(raw_events) is not list or len(raw_events) > MAX_EVENTS:
        raise DeliveryTruthError(f"events must be list <= {MAX_EVENTS}")
    if active is None and raw_events:
        raise DeliveryTruthError("delivery evidence requires submission or legacy_local_sent evidence")
    submitted_s = None
    if active is not None:
        _, submitted_s = _utc(active["submitted_at"], "submission.submitted_at")
    ordered = []
    ids: set[str] = set()
    source_shas: set[str] = set()
    semantic_keys: set[str] = set()
    for idx, raw in enumerate(raw_events):
        event = _normalize_event(raw, idx)
        if event["id"] in ids:
            raise DeliveryTruthError("duplicate evidence id")
        ids.add(event["id"])
        if event["source_sha256"] in source_shas:
            raise DeliveryTruthError("duplicate retained evidence source")
        source_shas.add(event["source_sha256"])
        semantic = _event_semantic(event)
        if semantic in semantic_keys:
            raise DeliveryTruthError("reminted duplicate delivery evidence")
        semantic_keys.add(semantic)
        _, observed_s = _utc(event["observed_at"], f"event {event['id']} observed_at")
        if submitted_s is not None and observed_s < submitted_s:
            raise DeliveryTruthError("delivery evidence predates provider submission")
        ordered.append((observed_s, event["id"], event))
    ordered.sort(key=lambda row: (row[0], row[1]))
    return {
        "schema": INPUT_SCHEMA,
        "submission": submission,
        "legacy_local_sent": legacy,
        "events": [row[2] for row in ordered],
    }


def _binding(event: dict[str, Any], submission: dict[str, Any]) -> tuple[bool, list[str]]:
    mismatches = []
    pairs = (
        ("provider", event["provider"], submission["provider"]),
        ("message", event["original_message_id"], submission["provider_message_id"]),
        ("thread", event["original_thread_id"], submission["provider_thread_id"]),
        ("sender", event["sender"], submission["sender"]),
        ("recipient", event["recipient"], submission["recipient"]),
    )
    for name, actual, expected in pairs:
        if actual != expected:
            mismatches.append(name)
    return not mismatches, mismatches


def compile_delivery_truth(packet: Any) -> dict[str, Any]:
    normalized = normalize_packet(packet)
    submission = normalized["submission"]
    legacy = normalized["legacy_local_sent"]
    active = submission if submission is not None else legacy
    evaluated = []
    hard_failures = []
    delivered = []
    if active is not None:
        for event in normalized["events"]:
            bound, mismatches = _binding(event, active)
            classification = _classify(event) if bound else "UNBOUND"
            row = {
                "id": event["id"],
                "source_sha256": event["source_sha256"],
                "bound_to_submission": bound,
                "binding_mismatches": mismatches,
                "classification": classification,
                "status": event["status"],
                "action": event["action"],
            }
            evaluated.append(row)
            if bound and classification == "HARD_FAILURE":
                hard_failures.append(row)
            elif bound and classification == "DELIVERED":
                delivered.append(row)
    if active is None:
        state, reason = "UNSENT", "no_submission_evidence"
    elif hard_failures and delivered:
        state, reason = "DELIVERY_UNKNOWN", "conflicting_terminal_evidence"
    elif hard_failures:
        state, reason = "DELIVERY_FAILED", "bound_hard_dsn"
    elif delivered:
        state, reason = "DELIVERED_EVIDENCE", "bound_delivery_evidence"
    elif submission is not None and not normalized["events"]:
        state, reason = "PROVIDER_SUBMITTED_PENDING_DELIVERY", "provider_submitted_no_delivery_evidence"
    else:
        state, reason = "DELIVERY_UNKNOWN", "no_terminal_delivery_evidence"
    if state == "DELIVERY_FAILED":
        route_viability = "DEAD_ROUTE_EVIDENCE"
    elif state == "DELIVERED_EVIDENCE":
        route_viability = "VIABLE_ROUTE_EVIDENCE"
    elif state == "UNSENT":
        route_viability = "UNTRIED_ROUTE"
    else:
        route_viability = "UNKNOWN_ROUTE_VIABILITY"
    contact_confirmed = state == "DELIVERED_EVIDENCE"
    projection = {
        "schema": PROJECTION_SCHEMA,
        "provider_submission_observed": active is not None,
        "delivery_state": state,
        "organization_contact_confirmed": contact_confirmed,
        "route_viability": route_viability,
        "same_route_resend_authorized": False,
        "alternate_route_send_authorized": False,
        "same_route_dedupe_hold": active is not None,
        "counts_as_contacted": contact_confirmed,
        "counts_as_revenue": False,
    }
    if state == "UNSENT":
        transition = ["UNSENT"]
    elif submission is not None:
        transition = ["UNSENT", "PROVIDER_SUBMITTED_PENDING_DELIVERY"]
        if state != "PROVIDER_SUBMITTED_PENDING_DELIVERY":
            transition.append(state)
    else:
        transition = ["UNSENT", "DELIVERY_UNKNOWN"]
        if state != "DELIVERY_UNKNOWN":
            transition.append(state)
    artifact = {
        "schema": OUTPUT_SCHEMA,
        "input_schema": INPUT_SCHEMA,
        "input_sha256": _digest(normalized),
        "submission": deepcopy(submission),
        "legacy_local_sent": deepcopy(legacy),
        "state_transition": transition,
        "delivery_state": state,
        "reason": reason,
        "evaluated_evidence": evaluated,
        "collision_projection": projection,
        "evidence_claims": {
            "provider_submission_retained": submission is not None,
            "legacy_local_sent_retained": legacy is not None,
            "delivery_confirmed": contact_confirmed,
            "hard_failure_confirmed": state == "DELIVERY_FAILED",
            "absence_of_dsn_is_delivery": False,
        },
        "authority": dict(AUTHORITY),
    }
    artifact["receipt_sha256"] = _digest(artifact)
    return artifact


def verify_delivery_truth(packet: Any, artifact: Any) -> dict[str, Any]:
    try:
        if type(artifact) is not dict:
            raise DeliveryTruthError("artifact must be object")
        receipt = _sha(artifact.get("receipt_sha256"), "artifact.receipt_sha256")
        unsigned = deepcopy(artifact)
        unsigned.pop("receipt_sha256", None)
        if _digest(unsigned) != receipt:
            return {"schema": VERIFY_SCHEMA, "valid": False, "reason": "receipt_mismatch"}
        expected = compile_delivery_truth(packet)
        if _canonical(expected) != _canonical(artifact):
            return {
                "schema": VERIFY_SCHEMA,
                "valid": False,
                "reason": "semantic_recompile_mismatch",
            }
        return {
            "schema": VERIFY_SCHEMA,
            "valid": True,
            "reason": "artifact_authenticated",
            "delivery_state": artifact["delivery_state"],
            "same_route_resend_authorized": False,
            "alternate_route_send_authorized": False,
            "revenue_recognized": False,
        }
    except (DeliveryTruthError, UnicodeError, ValueError, TypeError) as exc:
        return {"schema": VERIFY_SCHEMA, "valid": False, "reason": f"artifact_invalid:{exc}"}


def collision_projection(artifact: Any) -> dict[str, Any]:
    if type(artifact) is not dict or artifact.get("schema") != OUTPUT_SCHEMA:
        raise DeliveryTruthError("diagnostic artifact required")
    projection = artifact.get("collision_projection")
    if type(projection) is not dict or projection.get("schema") != PROJECTION_SCHEMA:
        raise DeliveryTruthError("collision projection missing")
    return deepcopy(projection)
