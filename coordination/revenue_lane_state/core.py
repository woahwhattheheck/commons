"""Deterministic current-state reducer for revenue coordination lanes.

Pure/offline: this module never dereferences source refs or mutates providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = 1
SAFE_INT_MAX = (1 << 53) - 1
MAX_INPUT_BYTES = 1_000_000
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MAX_STRING_UTF8_BYTES = 262_144
MAX_EVENTS = 4_096
MAX_CANONICAL_BYTES = 2_000_000
MAX_CURRENTNESS_SECONDS = 7 * 24 * 60 * 60
MAX_SAFE_INT_DIGITS = len(str(SAFE_INT_MAX))
STATE_BEGIN = "<!-- REVENUE_LANE_CURRENT_STATE:BEGIN -->"
STATE_END = "<!-- REVENUE_LANE_CURRENT_STATE:END -->"

KINDS = {
    "RESEARCHED", "TAKE", "MUSE_PENDING", "MUSE_SELECTED", "LEASE_CONSUMED",
    "PROVIDER_SEND_ATTEMPTED", "PROVIDER_SENT", "BOUNCED", "HUMAN_REPLY",
    "HUMAN_DECLINE", "PARTNER_ACCEPTED", "DNR", "DEAD_ROUTE",
    "PACKET_REQUESTED", "PACKET_RECEIVED", "QUESTION_SENT", "BUYER_ACK",
    "SUBMITTED", "AWARDED", "LOST", "EXPIRED", "EVIDENCE_HOLD",
}
SOURCE_CLASSES = {"coordination", "provider", "human", "procurement", "auto"}
SOURCE_REQUIREMENTS = {
    "RESEARCHED": {"coordination"},
    "TAKE": {"coordination"},
    "MUSE_PENDING": {"coordination"},
    "MUSE_SELECTED": {"coordination"},
    "LEASE_CONSUMED": {"coordination"},
    "PROVIDER_SEND_ATTEMPTED": {"provider"},
    "PROVIDER_SENT": {"provider"},
    "BOUNCED": {"provider"},
    "HUMAN_REPLY": {"human"},
    "HUMAN_DECLINE": {"human"},
    "PARTNER_ACCEPTED": {"human"},
    "DNR": {"coordination", "human", "provider"},
    "DEAD_ROUTE": {"provider", "coordination"},
    "PACKET_REQUESTED": {"procurement", "provider"},
    "PACKET_RECEIVED": {"procurement", "provider"},
    "QUESTION_SENT": {"procurement", "provider"},
    "BUYER_ACK": {"procurement", "human"},
    "SUBMITTED": {"procurement", "provider"},
    "AWARDED": {"procurement", "human"},
    "LOST": {"procurement", "human"},
    "EXPIRED": {"procurement", "coordination"},
    "EVIDENCE_HOLD": {"coordination"},
}
ROOT_KEYS = {
    "schema_version", "lane_id", "opportunity_id", "counterparty_id", "purpose_id",
    "currentness_seconds", "events",
}
EVENT_KEYS = {
    "event_id", "lane_id", "opportunity_id", "counterparty_id", "purpose_id",
    "generation", "kind", "source_class", "source_ref", "occurred_at",
    "route_id", "supersedes",
}
ACTIONABLE_CURRENT_STATES = {
    "CLAIMED_NO_OUTBOUND",
    "MUSE_PENDING_NO_AUTHORITY",
    "SELECTED_UNCONSUMED_NO_SEND_AUTHORITY",
    "SEND_ATTEMPTED_PROVIDER_UNKNOWN",
    "HUMAN_REPLY_ACTIONABLE",
    "PARTNER_CONFIRMED",
    "BUYER_QUESTION_PENDING",
    "PACKET_PENDING",
    "PACKET_RECEIVED",
}
CURRENTNESS_BASIS_KINDS = {
    "CLAIMED_NO_OUTBOUND": {"TAKE"},
    "MUSE_PENDING_NO_AUTHORITY": {"MUSE_PENDING"},
    "SELECTED_UNCONSUMED_NO_SEND_AUTHORITY": {"MUSE_SELECTED"},
    "SEND_ATTEMPTED_PROVIDER_UNKNOWN": {"PROVIDER_SEND_ATTEMPTED"},
    "HUMAN_REPLY_ACTIONABLE": {"HUMAN_REPLY"},
    "PARTNER_CONFIRMED": {"PARTNER_ACCEPTED"},
    "BUYER_QUESTION_PENDING": {"QUESTION_SENT"},
    "PACKET_PENDING": {"PACKET_REQUESTED"},
    "PACKET_RECEIVED": {"PACKET_RECEIVED"},
}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")


def _make_policy_generation_sha256() -> str:
    """Bind the first-load semantic policy used by compile and verify."""
    descriptor = {
        "policy_schema": "commons.revenue-lane-policy.v1",
        "schema_version": SCHEMA_VERSION,
        "kinds": sorted(KINDS),
        "source_classes": sorted(SOURCE_CLASSES),
        "source_requirements": {
            kind: sorted(classes)
            for kind, classes in sorted(SOURCE_REQUIREMENTS.items())
        },
        "root_keys": sorted(ROOT_KEYS),
        "event_keys": sorted(EVENT_KEYS),
        "actionable_current_states": sorted(ACTIONABLE_CURRENT_STATES),
        "currentness_basis_kinds": {
            state: sorted(kinds)
            for state, kinds in sorted(CURRENTNESS_BASIS_KINDS.items())
        },
        "limits": {
            "safe_int_max": SAFE_INT_MAX,
            "max_input_bytes": MAX_INPUT_BYTES,
            "max_json_depth": MAX_JSON_DEPTH,
            "max_json_nodes": MAX_JSON_NODES,
            "max_string_utf8_bytes": MAX_STRING_UTF8_BYTES,
            "max_events": MAX_EVENTS,
            "max_canonical_bytes": MAX_CANONICAL_BYTES,
            "max_currentness_seconds": MAX_CURRENTNESS_SECONDS,
        },
        "id_pattern": _ID_RE.pattern,
        "authority": {
            "send": False,
            "muse": False,
            "provider_mutation": False,
            "payment": False,
            "revenue": False,
        },
    }
    payload = json.dumps(
        descriptor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_POLICY_GENERATION_SHA256 = _make_policy_generation_sha256()
del _make_policy_generation_sha256


class ContractError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON number forbidden: {value}")


def _reject_float(value: str) -> None:
    raise ContractError(f"floating-point JSON number forbidden: {value}")


def _parse_int(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if not digits or len(digits) > MAX_SAFE_INT_DIGITS:
        raise ContractError("unsafe integer")
    try:
        number = int(value)
    except ValueError as exc:
        raise ContractError("unsafe integer") from exc
    if abs(number) > SAFE_INT_MAX:
        raise ContractError("unsafe integer")
    return number


def _object_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _validate_json_value(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    seen_containers: set[int] = set()
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ContractError("JSON node limit exceeded")
        if depth > MAX_JSON_DEPTH:
            raise ContractError("JSON depth limit exceeded")
        item_type = type(item)
        if item_type is str:
            try:
                encoded = item.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise ContractError("lone surrogate forbidden") from exc
            if len(encoded) > MAX_STRING_UTF8_BYTES:
                raise ContractError("JSON string byte limit exceeded")
        elif item_type is int:
            if abs(item) > SAFE_INT_MAX:
                raise ContractError("unsafe integer")
        elif item_type is bool or item is None:
            continue
        elif item_type is list:
            marker = id(item)
            if marker in seen_containers:
                raise ContractError("container alias or cycle forbidden")
            seen_containers.add(marker)
            for child in reversed(item):
                stack.append((child, depth + 1))
        elif item_type is dict:
            marker = id(item)
            if marker in seen_containers:
                raise ContractError("container alias or cycle forbidden")
            seen_containers.add(marker)
            for key, child in reversed(list(item.items())):
                if type(key) is not str:
                    raise ContractError("JSON object keys must be exact strings")
                stack.append((child, depth + 1))
                stack.append((key, depth + 1))
        else:
            raise ContractError("non-JSON value type")


def strict_json_loads(data: bytes | str) -> Any:
    if isinstance(data, bytes):
        if len(data) > MAX_INPUT_BYTES:
            raise ContractError("JSON input byte limit exceeded")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ContractError("invalid UTF-8") from exc
    elif isinstance(data, str):
        try:
            encoded = data.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise ContractError("invalid UTF-8") from exc
        if len(encoded) > MAX_INPUT_BYTES:
            raise ContractError("JSON input byte limit exceeded")
        text = data
    else:
        raise TypeError("strict_json_loads accepts bytes or str")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_no_dupes,
            parse_float=_reject_float,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, UnicodeError, RecursionError, ValueError) as exc:
        raise ContractError("invalid JSON") from exc
    _validate_json_value(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _validate_json_value(value)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        payload = text.encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("value is not canonicalizable") from exc
    if len(payload) > MAX_CANONICAL_BYTES:
        raise ContractError("canonical JSON byte limit exceeded")
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_keys(obj: dict[str, Any], expected: set[str], *, optional: set[str] = frozenset()) -> None:
    keys = set(obj)
    unknown = keys - expected
    missing = (expected - optional) - keys
    if unknown:
        raise ContractError(f"unknown keys: {sorted(unknown)}")
    if missing:
        raise ContractError(f"missing keys: {sorted(missing)}")


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ContractError(f"invalid {name}")
    return value


def _safe_positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0 or value > SAFE_INT_MAX:
        raise ContractError(f"invalid {name}")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError(f"invalid {name}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"invalid {name}") from exc
    if dt.tzinfo is None:
        raise ContractError(f"{name} must include timezone")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class ParsedEvent:
    raw: dict[str, Any]
    event_id: str
    generation: int
    kind: str
    source_class: str
    occurred_at: datetime
    route_id: str | None
    supersedes: str | None


def _bind_validate_packet():
    """Capture trust-bearing policy so later module rebinding cannot widen v1."""
    schema_version = SCHEMA_VERSION
    safe_int_max = SAFE_INT_MAX
    max_currentness_seconds = MAX_CURRENTNESS_SECONDS
    max_events = MAX_EVENTS
    max_json_depth = MAX_JSON_DEPTH
    max_json_nodes = MAX_JSON_NODES
    max_string_utf8_bytes = MAX_STRING_UTF8_BYTES
    root_keys = frozenset(ROOT_KEYS)
    event_keys = frozenset(EVENT_KEYS)
    kinds = frozenset(KINDS)
    source_classes = frozenset(SOURCE_CLASSES)
    source_requirements = {
        kind: frozenset(classes)
        for kind, classes in SOURCE_REQUIREMENTS.items()
    }
    id_re = re.compile(_ID_RE.pattern)
    contract_error = ContractError
    parsed_event_type = ParsedEvent
    datetime_fromisoformat = datetime.fromisoformat
    utc = timezone.utc

    def validate_json_value_local(value: Any) -> None:
        stack: list[tuple[Any, int]] = [(value, 0)]
        seen_containers: set[int] = set()
        nodes = 0
        while stack:
            item, depth = stack.pop()
            nodes += 1
            if nodes > max_json_nodes:
                raise contract_error("JSON node limit exceeded")
            if depth > max_json_depth:
                raise contract_error("JSON depth limit exceeded")
            item_type = type(item)
            if item_type is str:
                try:
                    encoded = item.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise contract_error("lone surrogate forbidden") from exc
                if len(encoded) > max_string_utf8_bytes:
                    raise contract_error("JSON string byte limit exceeded")
            elif item_type is int:
                if abs(item) > safe_int_max:
                    raise contract_error("unsafe integer")
            elif item_type is bool or item is None:
                continue
            elif item_type is list:
                marker = id(item)
                if marker in seen_containers:
                    raise contract_error("container alias or cycle forbidden")
                seen_containers.add(marker)
                for child in reversed(item):
                    stack.append((child, depth + 1))
            elif item_type is dict:
                marker = id(item)
                if marker in seen_containers:
                    raise contract_error("container alias or cycle forbidden")
                seen_containers.add(marker)
                for key, child in reversed(list(item.items())):
                    if type(key) is not str:
                        raise contract_error("JSON object keys must be exact strings")
                    stack.append((child, depth + 1))
                    stack.append((key, depth + 1))
            else:
                raise contract_error("non-JSON value type")

    def require_exact_keys_local(
        obj: dict[str, Any],
        expected: frozenset[str],
        *,
        optional: frozenset[str] = frozenset(),
    ) -> None:
        keys = set(obj)
        unknown = keys - expected
        missing = (expected - optional) - keys
        if unknown:
            raise contract_error(f"unknown keys: {sorted(unknown)}")
        if missing:
            raise contract_error(f"missing keys: {sorted(missing)}")

    def id_local(value: Any, name: str) -> str:
        if not isinstance(value, str) or not id_re.fullmatch(value):
            raise contract_error(f"invalid {name}")
        return value

    def safe_positive_int_local(value: Any, name: str) -> int:
        if type(value) is not int or value <= 0 or value > safe_int_max:
            raise contract_error(f"invalid {name}")
        return value

    def timestamp_local(value: Any, name: str) -> datetime:
        if not isinstance(value, str) or not value:
            raise contract_error(f"invalid {name}")
        try:
            dt = datetime_fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise contract_error(f"invalid {name}") from exc
        if dt.tzinfo is None:
            raise contract_error(f"{name} must include timezone")
        return dt.astimezone(utc)

    def validate_packet(
        packet: Any,
        evaluation_time: str,
    ) -> tuple[dict[str, Any], list[ParsedEvent], datetime]:
        validate_json_value_local(packet)
        if not isinstance(packet, dict):
            raise contract_error("root must be object")
        require_exact_keys_local(packet, root_keys)
        if type(packet["schema_version"]) is not int or packet["schema_version"] != schema_version:
            raise contract_error("unsupported schema_version")
        identity = {
            "lane_id": id_local(packet["lane_id"], "lane_id"),
            "opportunity_id": id_local(packet["opportunity_id"], "opportunity_id"),
            "counterparty_id": id_local(packet["counterparty_id"], "counterparty_id"),
            "purpose_id": id_local(packet["purpose_id"], "purpose_id"),
        }
        currentness = safe_positive_int_local(packet["currentness_seconds"], "currentness_seconds")
        if currentness > max_currentness_seconds:
            raise contract_error(
                f"currentness_seconds exceeds compiler maximum {max_currentness_seconds}"
            )
        eval_dt = timestamp_local(evaluation_time, "evaluation_time")
        events_raw = packet["events"]
        if not isinstance(events_raw, list) or not events_raw:
            raise contract_error("events must be non-empty list")
        if len(events_raw) > max_events:
            raise contract_error("event count limit exceeded")
        parsed: list[ParsedEvent] = []
        seen: set[str] = set()
        for raw in events_raw:
            if not isinstance(raw, dict):
                raise contract_error("event must be object")
            require_exact_keys_local(
                raw,
                event_keys,
                optional=frozenset({"route_id", "supersedes"}),
            )
            for field, expected in identity.items():
                if id_local(raw[field], field) != expected:
                    raise contract_error("cross-lane/counterparty/opportunity/purpose transplant")
            event_id = id_local(raw["event_id"], "event_id")
            if event_id in seen:
                raise contract_error(f"duplicate event_id: {event_id}")
            seen.add(event_id)
            generation = safe_positive_int_local(raw["generation"], "generation")
            kind = raw["kind"]
            if kind not in kinds:
                raise contract_error(f"invalid event kind: {kind}")
            source_class = raw["source_class"]
            if source_class not in source_classes:
                raise contract_error(f"invalid source_class: {source_class}")
            if source_class not in source_requirements[kind]:
                raise contract_error(f"{kind} cannot be proven by source_class={source_class}")
            id_local(raw["source_ref"], "source_ref")
            occurred_at = timestamp_local(raw["occurred_at"], "occurred_at")
            if occurred_at > eval_dt:
                raise contract_error("future event relative to trusted evaluation time")
            route_id = None
            if "route_id" in raw:
                route_id = id_local(raw["route_id"], "route_id")
            supersedes = None
            if "supersedes" in raw:
                supersedes = id_local(raw["supersedes"], "supersedes")
                if supersedes == event_id:
                    raise contract_error("event cannot supersede itself")
            parsed.append(
                parsed_event_type(
                    raw,
                    event_id,
                    generation,
                    kind,
                    source_class,
                    occurred_at,
                    route_id,
                    supersedes,
                )
            )
        chronological = sorted(parsed, key=lambda e: (e.occurred_at, e.generation, e.event_id))
        max_generation = 0
        for event in chronological:
            if event.generation < max_generation:
                raise contract_error("generation chronology regressed")
            max_generation = max(max_generation, event.generation)

        by_id = {event.event_id: event for event in parsed}
        superseded: set[str] = set()
        for event in parsed:
            if event.supersedes:
                target = by_id.get(event.supersedes)
                if target is None:
                    raise contract_error("supersedes target missing")
                if target.occurred_at >= event.occurred_at:
                    raise contract_error("supersession chronology invalid")
                if event.generation < target.generation:
                    raise contract_error("supersession generation regressed")
                if event.source_class != target.source_class:
                    raise contract_error("supersession source authority mismatch")
                if target.kind == "PROVIDER_SENT":
                    raise contract_error("provider send evidence cannot be superseded")
                if target.event_id in superseded:
                    raise contract_error("multiple supersessions of one event")
                superseded.add(target.event_id)
        active = [event for event in parsed if event.event_id not in superseded]
        if not active:
            raise contract_error("all events superseded")
        active.sort(key=lambda e: (e.occurred_at, e.generation, e.event_id))
        normalized = {
            "schema_version": schema_version,
            **identity,
            "currentness_seconds": currentness,
            "events": [
                event.raw
                for event in sorted(
                    parsed,
                    key=lambda e: (e.generation, e.occurred_at, e.event_id),
                )
            ],
        }
        return normalized, active, eval_dt

    return validate_packet


validate_packet = _bind_validate_packet()
del _bind_validate_packet


def _latest_generation(events: list[ParsedEvent]) -> int:
    return max(event.generation for event in events)


def _bind_reduce_state():
    contract_error = ContractError
    actionable_current_states = frozenset(ACTIONABLE_CURRENT_STATES)
    currentness_basis_kinds = {
        state: frozenset(kinds)
        for state, kinds in CURRENTNESS_BASIS_KINDS.items()
    }

    def reduce_state(
        events: list[ParsedEvent],
        eval_dt: datetime,
        currentness_seconds: int,
    ) -> str:
        kinds = {event.kind for event in events}
        terminal_procurement = kinds & {"AWARDED", "LOST", "EXPIRED"}
        if len(terminal_procurement) > 1:
            raise contract_error("conflicting terminal procurement outcomes")
        if "EXPIRED" in kinds and "SUBMITTED" in kinds:
            raise contract_error("expired and submitted outcomes conflict")
        if "HUMAN_DECLINE" in kinds and "PARTNER_ACCEPTED" in kinds:
            raise contract_error("human decline and partner acceptance conflict")

        if "LOST" in kinds:
            state = "LOST_CLOSED"
        elif "EXPIRED" in kinds:
            state = "EXPIRED_CLOSED"
        elif "AWARDED" in kinds:
            state = "AWARDED_PENDING_CONTRACT"
        elif "SUBMITTED" in kinds:
            state = "SUBMITTED_PENDING_RESULT"
        elif "HUMAN_DECLINE" in kinds:
            state = "HUMAN_DECLINE_DNR"
        elif "PARTNER_ACCEPTED" in kinds:
            state = "PARTNER_CONFIRMED"
        elif "HUMAN_REPLY" in kinds:
            state = "HUMAN_REPLY_ACTIONABLE"
        else:
            sent = [event for event in events if event.kind == "PROVIDER_SENT"]
            bounced = [event for event in events if event.kind == "BOUNCED"]
            dead_routes = [event for event in events if event.kind == "DEAD_ROUTE"]
            if len(sent) >= 2:
                state = "COLLISION_DUPLICATE_SEND_DNR"
            elif "DNR" in kinds:
                state = "SENT_DNR_PENDING_EVENT" if sent else "HOLD_EVIDENCE"
            elif sent:
                # Retained successful send truth dominates a later transport-only
                # failure on another route/generation. The failure remains bound
                # in history but cannot turn an already-contacted lane unopened.
                state = "SENT_DNR_PENDING_EVENT"
            elif bounced or dead_routes:
                state = "BOUNCED_DEAD_ROUTE"
            elif "PROVIDER_SEND_ATTEMPTED" in kinds:
                state = "SEND_ATTEMPTED_PROVIDER_UNKNOWN"
            elif "LEASE_CONSUMED" in kinds:
                state = "HOLD_EVIDENCE"
            else:
                latest_gen = max(event.generation for event in events)
                generation_events = [
                    event for event in events
                    if event.generation == latest_gen
                ]
                generation_kinds = {event.kind for event in generation_events}
                if "MUSE_SELECTED" in generation_kinds:
                    state = "SELECTED_UNCONSUMED_NO_SEND_AUTHORITY"
                elif "MUSE_PENDING" in generation_kinds:
                    state = "MUSE_PENDING_NO_AUTHORITY"
                elif "PACKET_RECEIVED" in kinds:
                    state = "PACKET_RECEIVED"
                elif "PACKET_REQUESTED" in kinds:
                    state = "PACKET_PENDING"
                elif "QUESTION_SENT" in kinds and "BUYER_ACK" not in kinds:
                    state = "BUYER_QUESTION_PENDING"
                elif "BUYER_ACK" in kinds:
                    state = "HOLD_EVIDENCE"
                elif "EVIDENCE_HOLD" in kinds:
                    state = "HOLD_EVIDENCE"
                elif "TAKE" in kinds:
                    state = "CLAIMED_NO_OUTBOUND"
                elif "RESEARCHED" in kinds:
                    state = "RESEARCHED_NOT_CONTACTED"
                else:
                    state = "HOLD_EVIDENCE"
        if state in actionable_current_states:
            basis_kinds = currentness_basis_kinds[state]
            basis_events = [event for event in events if event.kind in basis_kinds]
            if not basis_events:
                raise contract_error("currentness basis missing")
            latest_basis = max(
                basis_events,
                key=lambda event: (event.occurred_at, event.generation, event.event_id),
            )
            age = (eval_dt - latest_basis.occurred_at).total_seconds()
            if age > currentness_seconds:
                return "HOLD_EVIDENCE"
        return state

    return reduce_state


reduce_state = _bind_reduce_state()
del _bind_reduce_state


_STALE_RULES: tuple[tuple[set[str], re.Pattern[str], str], ...] = (
    (
        {
            "SENT_DNR_PENDING_EVENT", "BOUNCED_DEAD_ROUTE", "HUMAN_REPLY_ACTIONABLE",
            "HUMAN_DECLINE_DNR", "PARTNER_CONFIRMED", "SUBMITTED_PENDING_RESULT",
            "LOST_CLOSED", "AWARDED_PENDING_CONTRACT", "COLLISION_DUPLICATE_SEND_DNR",
        },
        re.compile(r"\b(?:outbound\s+)?not\s+(?:yet\s+)?sent\b", re.I),
        "NOT_SENT",
    ),
    (
        {
            "SENT_DNR_PENDING_EVENT", "BOUNCED_DEAD_ROUTE", "HUMAN_REPLY_ACTIONABLE",
            "HUMAN_DECLINE_DNR", "PARTNER_CONFIRMED", "COLLISION_DUPLICATE_SEND_DNR",
        },
        re.compile(r"\bno\s+(?:buyer\s+or\s+)?partner\s+contact\b", re.I),
        "NO_PARTNER_CONTACT",
    ),
    (
        {
            "SELECTED_UNCONSUMED_NO_SEND_AUTHORITY", "SEND_ATTEMPTED_PROVIDER_UNKNOWN",
            "SENT_DNR_PENDING_EVENT", "BOUNCED_DEAD_ROUTE", "HUMAN_REPLY_ACTIONABLE",
            "HUMAN_DECLINE_DNR", "PARTNER_CONFIRMED", "COLLISION_DUPLICATE_SEND_DNR",
        },
        re.compile(r"\bmuse[\s_-]*pending\b", re.I),
        "MUSE_PENDING",
    ),
    (
        {
            "PACKET_RECEIVED", "SENT_DNR_PENDING_EVENT", "HUMAN_REPLY_ACTIONABLE",
            "HUMAN_DECLINE_DNR", "PARTNER_CONFIRMED", "SUBMITTED_PENDING_RESULT",
        },
        re.compile(r"\bpacket(?:\s+recovery)?[\s_-]*pending\b", re.I),
        "PACKET_PENDING",
    ),
    (
        {"HUMAN_DECLINE_DNR", "PARTNER_CONFIRMED", "HUMAN_REPLY_ACTIONABLE"},
        re.compile(r"\bawait(?:ing)?\s+(?:a\s+)?reply\b", re.I),
        "AWAIT_REPLY",
    ),
)


def stale_body_findings(body_text: str, state: str) -> list[dict[str, Any]]:
    if not isinstance(body_text, str):
        raise ContractError("body_text must be string")
    try:
        body_text.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ContractError("body_text contains lone surrogate") from exc
    findings: list[dict[str, Any]] = []
    for states, pattern, code in _STALE_RULES:
        if state not in states:
            continue
        for match in pattern.finditer(body_text):
            findings.append({
                "code": code,
                "start": match.start(),
                "end": match.end(),
                "matched_text": match.group(0),
            })
    findings.sort(key=lambda row: (row["start"], row["end"], row["code"]))
    return findings


def render_header(state: str, evaluation_time: str, event_digest: str, receipt: str) -> str:
    return "\n".join([
        STATE_BEGIN,
        "## CURRENT STATE — machine-reduced, coordination only",
        f"- State: `{state}`",
        f"- Evaluated at: `{evaluation_time}`",
        f"- Active-event digest: `{event_digest}`",
        f"- Semantic receipt: `{receipt}`",
        "- Authority: `send=false · muse=false · provider_mutation=false · payment=false · revenue=false`",
        STATE_END,
    ])


def make_patch_plan(body_text: str, header: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    encoded = body_text.encode("utf-8", "strict")
    begin_count = body_text.count(STATE_BEGIN)
    end_count = body_text.count(STATE_END)
    if begin_count != end_count or begin_count > 1:
        raise ContractError("malformed or duplicate CURRENT STATE block")
    if begin_count == 1:
        start = body_text.index(STATE_BEGIN)
        end = body_text.index(STATE_END, start) + len(STATE_END)
        action = "replace_current_state_block"
        proposed = body_text[:start] + header + body_text[end:]
    else:
        action = "prepend_current_state_block"
        proposed = header + "\n\n" + body_text
    return {
        "apply": False,
        "action": action,
        "expected_body_sha256": sha256_bytes(encoded),
        "proposed_body_sha256": sha256_bytes(proposed.encode("utf-8")),
        "stale_findings": [dict(item) for item in findings],
        "replacement_header": header,
    }


def _bind_compile_state():
    validate = validate_packet
    reduce = reduce_state
    canonical = canonical_bytes
    digest = sha256_bytes
    stale_findings = stale_body_findings
    render = render_header
    patch = make_patch_plan
    schema_version = SCHEMA_VERSION
    policy_generation_sha256 = _POLICY_GENERATION_SHA256

    def compile_state(packet: dict[str, Any], *, body_text: str, evaluation_time: str) -> dict[str, Any]:
        normalized, events, eval_dt = validate(packet, evaluation_time)
        state = reduce(events, eval_dt, normalized["currentness_seconds"])
        event_digest = digest(canonical(normalized))
        semantic_basis = {
            "schema_version": schema_version,
            "policy_generation_sha256": policy_generation_sha256,
            "lane_id": normalized["lane_id"],
            "opportunity_id": normalized["opportunity_id"],
            "counterparty_id": normalized["counterparty_id"],
            "purpose_id": normalized["purpose_id"],
            "evaluation_time": evaluation_time,
            "state": state,
            "event_digest_sha256": event_digest,
            "input_authentication": {
                "verified_by_compiler": False,
                "requirement": "UPSTREAM_AUTHENTICATED_RETAINED_EVENTS",
            },
            "authority": {
                "send": False,
                "muse": False,
                "provider_mutation": False,
                "payment": False,
                "revenue": False,
            },
        }
        receipt = digest(canonical(semantic_basis))
        findings = stale_findings(body_text, state)
        header = render(state, evaluation_time, event_digest, receipt)
        return {
            **semantic_basis,
            "semantic_receipt_sha256": receipt,
            "current_state_markdown": header,
            "stale_body_findings": findings,
            "patch_plan": patch(body_text, header, findings),
        }

    return compile_state


compile_state = _bind_compile_state()
del _bind_compile_state


def _bind_compile_from_json():
    strict_loads = strict_json_loads
    compile_bound = compile_state

    def compile_from_json(data: bytes | str, *, body_text: str, evaluation_time: str) -> dict[str, Any]:
        packet = strict_loads(data)
        return compile_bound(packet, body_text=body_text, evaluation_time=evaluation_time)

    return compile_from_json


compile_from_json = _bind_compile_from_json()
del _bind_compile_from_json


def _bind_verify_artifact():
    compile_bound = compile_from_json
    strict_loads = strict_json_loads
    canonical = canonical_bytes
    contract_error = ContractError

    def verify_artifact(
        packet_data: bytes | str,
        artifact_data: bytes | str,
        *,
        body_text: str,
        evaluation_time: str,
    ) -> bool:
        expected = compile_bound(packet_data, body_text=body_text, evaluation_time=evaluation_time)
        actual = strict_loads(artifact_data)
        if not isinstance(actual, dict):
            raise contract_error("artifact must be object")
        if canonical(actual) != canonical(expected):
            raise contract_error("artifact does not exactly replay")
        return True

    return verify_artifact


verify_artifact = _bind_verify_artifact()
del _bind_verify_artifact

