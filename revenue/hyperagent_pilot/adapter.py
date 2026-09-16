from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


class AdapterError(ValueError):
    pass


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_KINDS = {"MESSAGE", "STATUS", "ACTION_REQUEST", "RESULT", "ERROR"}
_APPROVAL_SIGNED_KEYS = {
    "schema",
    "run_id",
    "event_id",
    "action_generation",
    "approved_at",
    "expires_at",
}
_APPROVAL_KEYS = _APPROVAL_SIGNED_KEYS | {"auth_tag"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise AdapterError(f"{label} keys mismatch")


def _obj(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AdapterError(f"{label} must be an object")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise AdapterError(f"{label} must be a bounded opaque identifier")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2000:
        raise AdapterError(f"{label} must be nonempty text <= 2000 characters")
    if any((ord(ch) < 32 and ch not in "\n\t") or ord(ch) == 127 for ch in value):
        raise AdapterError(f"{label} contains control characters")
    return value


def _sequence(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 1_000_000:
        raise AdapterError(f"{label} must be an integer in [0, 1000000]")
    return value


def _kind(value: Any) -> str:
    if not isinstance(value, str) or value not in _KINDS:
        raise AdapterError("event kind is invalid")
    return value


def _stable_id(namespace: str, *parts: str) -> str:
    body = {"namespace": namespace, "parts": list(parts)}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _approval_key(value: Any) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise AdapterError("approval authority key must be bytes")
    key = bytes(value)
    if len(key) < 32 or len(key) > 128:
        raise AdapterError("approval authority key must be 32..128 bytes")
    return key


def _trusted_now(_now=datetime.now, _utc=timezone.utc) -> datetime:
    """Return process UTC without accepting caller time authority."""
    return _now(_utc).replace(microsecond=0)


def normalize_event(raw: Mapping[str, Any]) -> dict[str, Any]:
    raw = _obj(raw, "event")
    backend = raw.get("backend")

    if backend == "atlas":
        _exact_keys(raw, {"backend", "run", "event"}, "atlas event")
        run = _obj(raw["run"], "atlas.run")
        event = _obj(raw["event"], "atlas.event")
        _exact_keys(run, {"id", "thread"}, "atlas.run")
        _exact_keys(event, {"id", "sequence", "type", "text"}, "atlas.event")
        source_run = _identifier(run["id"], "atlas.run.id")
        thread_key = _identifier(run["thread"], "atlas.run.thread")
        source_event = _identifier(event["id"], "atlas.event.id")
        sequence = _sequence(event["sequence"], "atlas.event.sequence")
        kind = _kind(event["type"])
        text = _text(event["text"], "atlas.event.text")
    elif backend == "beacon":
        _exact_keys(raw, {"backend", "execution_id", "conversation_key", "record"}, "beacon event")
        record = _obj(raw["record"], "beacon.record")
        _exact_keys(record, {"id", "index", "kind", "body"}, "beacon.record")
        source_run = _identifier(raw["execution_id"], "beacon.execution_id")
        thread_key = _identifier(raw["conversation_key"], "beacon.conversation_key")
        source_event = _identifier(record["id"], "beacon.record.id")
        sequence = _sequence(record["index"], "beacon.record.index")
        kind = _kind(record["kind"])
        text = _text(record["body"], "beacon.record.body")
    elif backend == "cipher":
        _exact_keys(raw, {"backend", "trace", "item"}, "cipher event")
        trace = _obj(raw["trace"], "cipher.trace")
        item = _obj(raw["item"], "cipher.item")
        payload = _obj(item.get("payload"), "cipher.item.payload")
        _exact_keys(trace, {"run", "channel"}, "cipher.trace")
        _exact_keys(item, {"key", "ordinal", "type", "payload"}, "cipher.item")
        _exact_keys(payload, {"text"}, "cipher.item.payload")
        source_run = _identifier(trace["run"], "cipher.trace.run")
        thread_key = _identifier(trace["channel"], "cipher.trace.channel")
        source_event = _identifier(item["key"], "cipher.item.key")
        sequence = _sequence(item["ordinal"], "cipher.item.ordinal")
        kind = _kind(item["type"])
        text = _text(payload["text"], "cipher.item.payload.text")
    else:
        raise AdapterError("unsupported backend schema")

    run_id = _stable_id("hyperagent-pilot/run/v1", str(backend), source_run)
    thread_id = _stable_id("hyperagent-pilot/thread/v1", str(backend), thread_key)
    event_id = _stable_id("hyperagent-pilot/event/v1", str(backend), source_event)
    core = {
        "schema": "hyperagent-pilot/canonical-event/v1",
        "backend": backend,
        "source_run_id": source_run,
        "source_event_id": source_event,
        "sequence": sequence,
        "run_id": run_id,
        "thread_id": thread_id,
        "event_id": event_id,
        "kind": kind,
        "text": text,
    }
    if kind == "ACTION_REQUEST":
        core["action_generation"] = sha256_json(
            {
                "schema": "hyperagent-pilot/action-generation/v1",
                "run_id": run_id,
                "thread_id": thread_id,
                "event_id": event_id,
                "text": text,
            }
        )
    return core


def normalize_events(raw_events: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if isinstance(raw_events, (str, bytes, bytearray)) or not isinstance(raw_events, Sequence):
        raise AdapterError("events must be a sequence")
    if len(raw_events) > 10_000:
        raise AdapterError("too many events")

    by_source: dict[tuple[str, str], dict[str, Any]] = {}
    sequence_owner: dict[tuple[str, str, int], str] = {}
    duplicates = 0
    for raw in raw_events:
        event = normalize_event(raw)
        source_key = (event["backend"], event["source_event_id"])
        prior = by_source.get(source_key)
        if prior is not None:
            if canonical_bytes(prior) != canonical_bytes(event):
                raise AdapterError("same source event ID changed semantics")
            duplicates += 1
            continue
        sequence_key = (event["backend"], event["source_run_id"], event["sequence"])
        owner = sequence_owner.get(sequence_key)
        if owner is not None and owner != event["event_id"]:
            raise AdapterError("ambiguous sequence within source run")
        sequence_owner[sequence_key] = event["event_id"]
        by_source[source_key] = event

    events = sorted(
        by_source.values(),
        key=lambda row: (row["thread_id"], row["run_id"], row["sequence"], row["event_id"]),
    )
    return events, duplicates


def project_transcripts(raw_events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    events, duplicate_count = normalize_events(raw_events)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["thread_id"]].append(event)

    artifacts: list[dict[str, Any]] = []
    for thread_id in sorted(grouped):
        thread_events = grouped[thread_id]
        messages = [
            {
                "event_id": event["event_id"],
                "run_id": event["run_id"],
                "sequence": event["sequence"],
                "kind": event["kind"],
                "text": event["text"],
                **(
                    {"action_generation": event["action_generation"]}
                    if "action_generation" in event
                    else {}
                ),
            }
            for event in thread_events
        ]
        artifact_body = {
            "schema": "hyperagent-pilot/slack-transcript-artifact/v1",
            "thread_id": thread_id,
            "run_ids": sorted({event["run_id"] for event in thread_events}),
            "messages": messages,
            "outbound_authorized": False,
        }
        artifacts.append({**artifact_body, "artifact_sha256": sha256_json(artifact_body)})

    body = {
        "schema": "hyperagent-pilot/projection/v1",
        "artifact_count": len(artifacts),
        "logical_message_count": len(events),
        "duplicate_source_event_count": duplicate_count,
        "artifacts": artifacts,
        "authority": {
            "offline_projection_only": True,
            "network_access_performed": False,
            "slack_send_performed": False,
            "outbound_authorized": False,
            "buyer_acceptance_claimed": False,
            "payment_or_revenue_claimed": False,
        },
    }
    return {**body, "projection_sha256": sha256_json(body)}


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdapterError(f"{label} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AdapterError(f"{label} is invalid") from exc
    if parsed.tzinfo != timezone.utc or parsed.microsecond:
        raise AdapterError(f"{label} must be second-precision UTC")
    canonical = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    if canonical != value:
        raise AdapterError(f"{label} must be canonical UTC")
    return parsed


def _approval(value: Any, approval_auth_key: bytes) -> dict[str, Any]:
    obj = _obj(value, "approval")
    _exact_keys(obj, _APPROVAL_KEYS, "approval")
    if obj["schema"] != "hyperagent-pilot/approval/v1":
        raise AdapterError("approval schema mismatch")
    signed = {
        "schema": obj["schema"],
        "run_id": _identifier(obj["run_id"], "approval.run_id"),
        "event_id": _identifier(obj["event_id"], "approval.event_id"),
        "action_generation": _identifier(obj["action_generation"], "approval.action_generation"),
        "approved_at": obj["approved_at"],
        "expires_at": obj["expires_at"],
    }
    approved = _parse_utc(signed["approved_at"], "approval.approved_at")
    expires = _parse_utc(signed["expires_at"], "approval.expires_at")
    if expires <= approved:
        raise AdapterError("approval expiry must follow approval time")
    auth_tag = obj["auth_tag"]
    if not isinstance(auth_tag, str) or not _HEX64_RE.fullmatch(auth_tag):
        raise AdapterError("approval auth_tag must be lowercase HMAC-SHA256 hex")
    expected = hmac.new(approval_auth_key, canonical_bytes(signed), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(auth_tag, expected):
        raise AdapterError("approval authority authentication failed")
    return {**signed, "auth_tag": auth_tag}


def prepare_candidate_payloads(
    raw_events: Sequence[Mapping[str, Any]],
    approvals: Any,
    *,
    approval_auth_key: Any = None,
) -> list[dict[str, Any]]:
    """Build offline candidates only under an authenticated current approval.

    `approval_auth_key` is retained runtime authority supplied outside this repository.
    Current UTC comes from a captured process clock, never from caller input. This function
    never sends, performs network I/O, or grants provider authority. Malformed, foreign,
    unauthenticated, duplicate, or stale approval sets fail closed to [].
    """
    try:
        key = _approval_key(approval_auth_key)
        current = _trusted_now()
        events, _ = normalize_events(raw_events)
        if isinstance(approvals, (str, bytes, bytearray)) or not isinstance(approvals, Sequence):
            return []
        normalized_approvals = [_approval(value, key) for value in approvals]
        approval_by_event: dict[str, dict[str, Any]] = {}
        for approval in normalized_approvals:
            if approval["event_id"] in approval_by_event:
                return []
            approval_by_event[approval["event_id"]] = approval

        actions = {event["event_id"]: event for event in events if event["kind"] == "ACTION_REQUEST"}
        if set(approval_by_event) - set(actions):
            return []

        payloads: list[dict[str, Any]] = []
        for event_id in sorted(actions):
            approval = approval_by_event.get(event_id)
            if approval is None:
                continue
            event = actions[event_id]
            if approval["run_id"] != event["run_id"]:
                return []
            if approval["action_generation"] != event["action_generation"]:
                return []
            approved_at = _parse_utc(approval["approved_at"], "approval.approved_at")
            expires_at = _parse_utc(approval["expires_at"], "approval.expires_at")
            if not (approved_at <= current <= expires_at):
                return []
            body = {
                "schema": "hyperagent-pilot/offline-slack-candidate/v1",
                "thread_id": event["thread_id"],
                "run_id": event["run_id"],
                "event_id": event["event_id"],
                "action_generation": event["action_generation"],
                "text": event["text"],
                "approval_validated": True,
                "approval_receipt_sha256": sha256_json(approval),
                "outbound_authorized": False,
                "provider_action_performed": False,
            }
            payloads.append({**body, "candidate_sha256": sha256_json(body)})
        return payloads
    except (AdapterError, TypeError, ValueError, OverflowError):
        return []


def projection_bytes(raw_events: Sequence[Mapping[str, Any]]) -> bytes:
    return canonical_bytes(project_transcripts(raw_events)) + b"\n"
