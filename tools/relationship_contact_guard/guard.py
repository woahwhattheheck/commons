#!/usr/bin/env python3
"""Deterministic relationship-level outbound collision guard.

This module is diagnostic only. It never authorizes external contact. A
NO_CONFLICT_FOUND result means only that the retained packet supplied to this
compiler did not expose a relationship collision at a process-owned evaluation
time. Fresh provider census and an independent session-bound Muse consume/GO
gate remain required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "relationship-contact-guard/v3"
ARTIFACT_SCHEMA = "relationship-contact-guard-artifact/v3"
VERIFICATION_SCHEMA = "relationship-contact-guard-verification/v1"
MAX_JSON_BYTES = 1_048_576
MAX_EVENTS = 10_000
MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MIN_RELATIONSHIP_COOLDOWN_SECONDS = 6 * 60 * 60
MIN_PURSUIT_COOLDOWN_SECONDS = 72 * 60 * 60
IDENT_RE = re.compile(r"^[a-z0-9][a-z0-9._@:+/\-]{0,254}$")
OPAQUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+=\-]{0,511}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
KINDS = {"PROVIDER_SENT", "PROVIDER_BOUNCE", "HUMAN_REPLY", "HUMAN_NEGATIVE", "HUMAN_REOPEN"}
SCOPES = {"ROUTE_PURPOSE", "COUNTERPARTY"}

# Compatibility/export surface only. Compile/verify semantics deliberately do
# not read this mutable module object; source-literal authority is emitted
# inside _compile_at().
AUTHORITY = {
    "send_authorized": False,
    "muse_authorized": False,
    "provider_send_proven": False,
    "buyer_acceptance_proven": False,
    "contract_proven": False,
    "payment_proven": False,
    "cash_proven": False,
    "revenue_recognized": False,
}


class GuardError(ValueError):
    pass


def _pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GuardError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_constant(value: str) -> None:
    raise GuardError(f"non-finite JSON constant forbidden: {value}")


def _json_string_size(value: str, path: str, remaining: int) -> int:
    """Return exact ensure_ascii canonical JSON string bytes without allocating it."""
    total = 2  # surrounding quotes
    if total > remaining:
        raise GuardError(f"{path}: canonical bytes limit exceeded")
    for char in value:
        code = ord(char)
        if char in ('"', "\\") or char in ("\b", "\f", "\n", "\r", "\t"):
            step = 2
        elif code < 0x20:
            step = 6
        elif code <= 0x7F:
            step = 1
        elif code <= 0xFFFF:
            step = 6
        else:
            step = 12
        total += step
        if total > remaining:
            raise GuardError(f"{path}: canonical bytes limit exceeded")
    return total


def _freeze_plain_json(value: Any, path: str) -> Any:
    """Detach one bounded exact-JSON generation before canonical serialization.

    Container cardinality is checked against the remaining node budget before
    child iteration/copy. String/key canonical bytes are charged incrementally,
    so over-budget direct objects fail before the full value reaches json.dumps.
    """
    state = {"nodes": 0, "bytes": 0}

    def charge_bytes(amount: int, item_path: str) -> None:
        if amount < 0 or state["bytes"] + amount > MAX_JSON_BYTES:
            raise GuardError(f"{item_path}: canonical bytes limit exceeded")
        state["bytes"] += amount

    def take_node(item_path: str) -> None:
        if state["nodes"] >= MAX_JSON_NODES:
            raise GuardError(f"{item_path}: JSON node limit exceeded")
        state["nodes"] += 1

    def visit(item: Any, item_path: str, depth: int) -> Any:
        if depth > MAX_JSON_DEPTH:
            raise GuardError(f"{item_path}: JSON depth limit exceeded")
        take_node(item_path)

        if item is None:
            charge_bytes(4, item_path)
            return None
        if type(item) is bool:
            charge_bytes(4 if item else 5, item_path)
            return item
        if type(item) is int:
            if item < -MAX_SAFE_INTEGER or item > MAX_SAFE_INTEGER:
                raise GuardError(f"{item_path}: integer outside supported exact JSON range")
            charge_bytes(len(str(item)), item_path)
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise GuardError(f"{item_path}: non-finite number")
            # A finite float's scalar representation is intrinsically tiny;
            # using the serializer here cannot bypass aggregate work bounds.
            try:
                scalar = json.dumps(item, ensure_ascii=True, allow_nan=False)
            except (ValueError, TypeError, OverflowError) as exc:
                raise GuardError(f"{item_path}: canonical float serialization failed") from exc
            charge_bytes(len(scalar.encode("ascii")), item_path)
            return item
        if type(item) is str:
            remaining = MAX_JSON_BYTES - state["bytes"]
            charge_bytes(_json_string_size(item, item_path, remaining), item_path)
            return item

        if type(item) is list:
            count = len(item)
            if state["nodes"] + count > MAX_JSON_NODES:
                raise GuardError(f"{item_path}: JSON node limit exceeded before child traversal")
            charge_bytes(2 + max(0, count - 1), item_path)  # [] plus commas
            out: list[Any] = []
            try:
                for index in range(count):
                    out.append(visit(item[index], f"{item_path}[{index}]", depth + 1))
            except IndexError as exc:
                raise GuardError(f"{item_path}: list changed during bounded snapshot") from exc
            if len(item) != count:
                raise GuardError(f"{item_path}: list changed during bounded snapshot")
            return out

        if type(item) is dict:
            count = len(item)
            # Each pair costs one string-key work node and one value work node.
            if state["nodes"] + (2 * count) > MAX_JSON_NODES:
                raise GuardError(f"{item_path}: JSON node limit exceeded before child traversal")
            charge_bytes(2 + max(0, count - 1) + count, item_path)  # {}, commas, colons
            out: dict[str, Any] = {}
            seen = 0
            try:
                for key, child in item.items():
                    seen += 1
                    if seen > count:
                        raise GuardError(f"{item_path}: object changed during bounded snapshot")
                    if type(key) is not str:
                        raise GuardError(f"{item_path}: non-string JSON key")
                    take_node(f"{item_path}.<key>")
                    remaining = MAX_JSON_BYTES - state["bytes"]
                    charge_bytes(_json_string_size(key, f"{item_path}.<key>", remaining), f"{item_path}.<key>")
                    out[key] = visit(child, f"{item_path}.{key}", depth + 1)
            except RuntimeError as exc:
                raise GuardError(f"{item_path}: object changed during bounded snapshot") from exc
            if seen != count or len(item) != count:
                raise GuardError(f"{item_path}: object changed during bounded snapshot")
            return out

        raise GuardError(f"{item_path}: exact plain JSON types required")

    return visit(value, path, 0)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise GuardError("canonical JSON serialization failed") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _decode_json_bytes(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except GuardError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise GuardError(f"{label}: invalid strict JSON") from exc


def _freeze(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise GuardError(f"{label}: top level must be a plain object")
    frozen_plain = _freeze_plain_json(value, label)
    if type(frozen_plain) is not dict:
        raise GuardError(f"{label}: top level must be a plain object")
    raw = canonical_bytes(frozen_plain)
    if len(raw) > MAX_JSON_BYTES:
        # Defensive consistency check: bounded preflight should have rejected
        # before serializer entry if its byte accounting ever drifts.
        raise GuardError(f"{label}: exceeds {MAX_JSON_BYTES} canonical bytes")
    frozen = _decode_json_bytes(raw, label)
    if type(frozen) is not dict:
        raise GuardError(f"{label}: top level must be a plain object")
    return frozen


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise GuardError(f"{path}: exceeds {MAX_JSON_BYTES} bytes")
    value = _decode_json_bytes(raw, str(path))
    return _freeze(value, str(path))


def _keys(obj: Mapping[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    keys = set(obj)
    missing = sorted(required - keys)
    unknown = sorted(keys - allowed)
    if missing:
        raise GuardError(f"{label}: missing keys: {', '.join(missing)}")
    if unknown:
        raise GuardError(f"{label}: unknown keys: {', '.join(unknown)}")


def _ident(value: Any, label: str) -> str:
    if type(value) is not str or not IDENT_RE.fullmatch(value):
        raise GuardError(f"{label}: canonical lowercase ASCII identifier required")
    return value


def _opaque(value: Any, label: str) -> str:
    if type(value) is not str or not OPAQUE_RE.fullmatch(value):
        raise GuardError(f"{label}: bounded ASCII identifier required")
    return value


def _time(value: Any, label: str):
    # Local import intentionally avoids trusting a mutable module-level
    # datetime/timezone binding for current evaluation semantics.
    from datetime import datetime as _datetime, timezone as _timezone

    if type(value) is not str or not value.endswith("Z"):
        raise GuardError(f"{label}: canonical UTC Z timestamp required")
    try:
        dt = _datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GuardError(f"{label}: invalid timestamp") from exc
    if dt.tzinfo != _timezone.utc or value != dt.isoformat(timespec="seconds").replace("+00:00", "Z"):
        raise GuardError(f"{label}: whole-second canonical UTC timestamp required")
    return dt


def _format_time(dt) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _cooldown(value: Any, minimum: int, label: str) -> int:
    if type(value) is not int or value < minimum:
        raise GuardError(f"{label}: integer must be >= {minimum}")
    return value


def _candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    required = {"counterparty_id", "opportunity_id", "route", "purpose"}
    allowed = required | {"relationship_cooldown_seconds", "pursuit_cooldown_seconds"}
    _keys(raw, required, allowed, "candidate")
    return {
        "counterparty_id": _ident(raw["counterparty_id"], "candidate.counterparty_id"),
        "opportunity_id": _ident(raw["opportunity_id"], "candidate.opportunity_id"),
        "route": _ident(raw["route"], "candidate.route"),
        "purpose": _ident(raw["purpose"], "candidate.purpose"),
        "relationship_cooldown_seconds": _cooldown(
            raw.get("relationship_cooldown_seconds", MIN_RELATIONSHIP_COOLDOWN_SECONDS),
            MIN_RELATIONSHIP_COOLDOWN_SECONDS,
            "candidate.relationship_cooldown_seconds",
        ),
        "pursuit_cooldown_seconds": _cooldown(
            raw.get("pursuit_cooldown_seconds", MIN_PURSUIT_COOLDOWN_SECONDS),
            MIN_PURSUIT_COOLDOWN_SECONDS,
            "candidate.pursuit_cooldown_seconds",
        ),
    }


def _event(raw: Mapping[str, Any], index: int, counterparty: str) -> dict[str, Any]:
    label = f"events[{index}]"
    required = {"event_id", "kind", "occurred_at", "counterparty_id", "opportunity_id", "route", "purpose"}
    allowed = required | {
        "provider_message_id",
        "provider_thread_id",
        "scope",
        "in_reply_to_message_id",
        "reopens_event_id",
    }
    _keys(raw, required, allowed, label)
    kind = raw["kind"]
    if type(kind) is not str or kind not in KINDS:
        raise GuardError(f"{label}.kind: unsupported event kind")
    out = {
        "event_id": _opaque(raw["event_id"], f"{label}.event_id"),
        "kind": kind,
        "occurred_at": raw["occurred_at"],
        "counterparty_id": _ident(raw["counterparty_id"], f"{label}.counterparty_id"),
        "opportunity_id": _ident(raw["opportunity_id"], f"{label}.opportunity_id"),
        "route": _ident(raw["route"], f"{label}.route"),
        "purpose": _ident(raw["purpose"], f"{label}.purpose"),
    }
    _time(out["occurred_at"], f"{label}.occurred_at")
    if out["counterparty_id"] != counterparty:
        raise GuardError(f"{label}: cross-counterparty event transplant")
    for field in ("provider_message_id", "provider_thread_id", "in_reply_to_message_id", "reopens_event_id"):
        if field in raw:
            out[field] = _opaque(raw[field], f"{label}.{field}")

    if kind == "PROVIDER_SENT":
        if "provider_message_id" not in out:
            raise GuardError(f"{label}: PROVIDER_SENT requires provider_message_id")
        if "in_reply_to_message_id" in out or "reopens_event_id" in out or "scope" in raw:
            raise GuardError(f"{label}: PROVIDER_SENT has incompatible response fields")
    elif kind == "PROVIDER_BOUNCE":
        if "in_reply_to_message_id" not in out:
            raise GuardError(f"{label}: PROVIDER_BOUNCE requires in_reply_to_message_id")
        if "scope" in raw or "reopens_event_id" in out:
            raise GuardError(f"{label}: PROVIDER_BOUNCE has incompatible fields")
    elif kind == "HUMAN_REPLY":
        if "in_reply_to_message_id" not in out:
            raise GuardError(f"{label}: HUMAN_REPLY requires in_reply_to_message_id")
        if "scope" in raw or "reopens_event_id" in out:
            raise GuardError(f"{label}: HUMAN_REPLY has incompatible fields")
    elif kind == "HUMAN_NEGATIVE":
        if "in_reply_to_message_id" not in out:
            raise GuardError(f"{label}: HUMAN_NEGATIVE requires in_reply_to_message_id")
        scope = raw.get("scope")
        if type(scope) is not str or scope not in SCOPES:
            raise GuardError(f"{label}: HUMAN_NEGATIVE requires valid scope")
        out["scope"] = scope
        if "reopens_event_id" in out:
            raise GuardError(f"{label}: HUMAN_NEGATIVE cannot reopen another event")
    elif kind == "HUMAN_REOPEN":
        if "in_reply_to_message_id" not in out or "reopens_event_id" not in out:
            raise GuardError(f"{label}: HUMAN_REOPEN requires in_reply_to_message_id and reopens_event_id")
        scope = raw.get("scope")
        if type(scope) is not str or scope not in SCOPES:
            raise GuardError(f"{label}: HUMAN_REOPEN requires valid scope")
        out["scope"] = scope

    return out


def _bind_response(event: Mapping[str, Any], send: Mapping[str, Any], label: str) -> None:
    for field in ("counterparty_id", "opportunity_id", "route", "purpose"):
        if event[field] != send[field]:
            raise GuardError(f"{label}: response/bounce transplant changes referenced send {field}")
    # Thread identity is optional, but when present it is exact-generation
    # evidence: a response cannot add, omit, or swap the referenced send thread.
    if event.get("provider_thread_id") != send.get("provider_thread_id"):
        raise GuardError(f"{label}: response/bounce thread does not match referenced send")


def _semantic_event_key(event: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    # event_id and provider_message_id are source identities, not semantic
    # evidence identity. Reminting either must not turn one retained fact into
    # two facts. provider_thread_id and all lineage/scope fields remain bound.
    excluded = {"event_id", "provider_message_id"}
    return tuple((key, event[key]) for key in sorted(event) if key not in excluded)


def _validate(packet: Mapping[str, Any], now) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _keys(packet, {"candidate", "events"}, {"candidate", "events"}, "packet")
    if type(packet["candidate"]) is not dict or type(packet["events"]) is not list:
        raise GuardError("packet candidate/events types invalid")
    candidate = _candidate(packet["candidate"])
    if len(packet["events"]) > MAX_EVENTS:
        raise GuardError("too many events")
    events = [_event(raw, i, candidate["counterparty_id"]) for i, raw in enumerate(packet["events"])]

    seen_event: set[str] = set()
    seen_provider: set[str] = set()
    seen_semantic: set[tuple[tuple[str, Any], ...]] = set()
    send_by_message: dict[str, dict[str, Any]] = {}
    event_by_id: dict[str, dict[str, Any]] = {}
    last = None

    for i, event in enumerate(events):
        label = f"events[{i}]"
        dt = _time(event["occurred_at"], f"{label}.occurred_at")
        if dt > now:
            raise GuardError(f"{label}: future-dated event")
        if last is not None and dt < last:
            raise GuardError("events: chronology must be nondecreasing")
        last = dt

        if event["event_id"] in seen_event:
            raise GuardError("duplicate event_id")
        seen_event.add(event["event_id"])

        semantic_key = _semantic_event_key(event)
        if semantic_key in seen_semantic:
            raise GuardError("duplicate semantic event")
        seen_semantic.add(semantic_key)

        mid = event.get("provider_message_id")
        if mid is not None:
            if mid in seen_provider:
                raise GuardError("duplicate provider_message_id")
            seen_provider.add(mid)

        if event["kind"] == "PROVIDER_SENT":
            send_by_message[event["provider_message_id"]] = event
        ref = event.get("in_reply_to_message_id")
        if ref is not None:
            send = send_by_message.get(ref)
            if send is None:
                raise GuardError(f"{label}: orphan response/bounce reference")
            _bind_response(event, send, label)

        if event["kind"] == "HUMAN_REOPEN":
            blocker = event_by_id.get(event["reopens_event_id"])
            if blocker is None or blocker["kind"] != "HUMAN_NEGATIVE":
                raise GuardError(f"{label}: reopen must reference an earlier HUMAN_NEGATIVE")
            if event["scope"] != blocker["scope"]:
                raise GuardError(f"{label}: reopen scope does not match referenced negative")
            for field in ("counterparty_id", "opportunity_id", "route", "purpose", "in_reply_to_message_id"):
                if event[field] != blocker[field]:
                    raise GuardError(f"{label}: reopen does not exactly bind referenced negative {field}")

        event_by_id[event["event_id"]] = event

    return candidate, events


def _send_state(send: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> str:
    mid = send["provider_message_id"]
    later = [e for e in events if e.get("in_reply_to_message_id") == mid]
    # A retained hard bounce is transport evidence and remains route-dead even
    # if later contradictory human-shaped evidence is present.
    if any(event["kind"] == "PROVIDER_BOUNCE" for event in later):
        return "BOUNCED"
    if any(event["kind"] in {"HUMAN_REPLY", "HUMAN_NEGATIVE", "HUMAN_REOPEN"} for event in later):
        return "HUMAN_EVENT"
    return "DELIVERED_UNANSWERED"


def _reopened_after(events: Sequence[Mapping[str, Any]], blocker: Mapping[str, Any]) -> bool:
    blocker_time = _time(blocker["occurred_at"], "blocker.occurred_at")
    for event in events:
        if event["kind"] != "HUMAN_REOPEN":
            continue
        if event.get("reopens_event_id") != blocker["event_id"]:
            continue
        if _time(event["occurred_at"], "reopen.occurred_at") > blocker_time:
            return True
    return False


def _active_scoped_negative(
    events: Sequence[Mapping[str, Any]],
    scope: str,
    candidate: Mapping[str, Any],
):
    active = []
    for event in events:
        if event["kind"] != "HUMAN_NEGATIVE" or event.get("scope") != scope:
            continue
        if scope == "ROUTE_PURPOSE" and (
            event["route"] != candidate["route"] or event["purpose"] != candidate["purpose"]
        ):
            continue
        if not _reopened_after(events, event):
            active.append(event)
    return active[-1] if active else None


def _compile_at(frozen: Mapping[str, Any], now, evaluation_mode: str) -> dict[str, Any]:
    candidate, events = _validate(frozen, now)
    status = "NO_CONFLICT_FOUND"
    reasons: list[str] = []
    blockers: list[str] = []

    org_negative = _active_scoped_negative(events, "COUNTERPARTY", candidate)
    route_negative = _active_scoped_negative(events, "ROUTE_PURPOSE", candidate)
    if org_negative is not None:
        status = "HOLD_COUNTERPARTY_OPT_OUT"
        reasons.append("retained human negative event applies to the whole counterparty")
        blockers.append(org_negative["event_id"])
    elif route_negative is not None:
        status = "HOLD_ROUTE_PURPOSE_OPT_OUT"
        reasons.append("retained human negative event applies to this route/purpose")
        blockers.append(route_negative["event_id"])

    sends = [(e, _send_state(e, events)) for e in events if e["kind"] == "PROVIDER_SENT"]
    if status == "NO_CONFLICT_FOUND":
        bounced = [e for e, state in sends if state == "BOUNCED" and e["route"] == candidate["route"]]
        if bounced:
            status = "HOLD_DEAD_ROUTE"
            reasons.append("current route has a retained hard-bounce event; bounce is route-scoped, not counterparty rejection")
            blockers.append(bounced[-1]["event_id"])
    if status == "NO_CONFLICT_FOUND":
        exact = [
            e
            for e, state in sends
            if state == "DELIVERED_UNANSWERED"
            and e["route"] == candidate["route"]
            and e["purpose"] == candidate["purpose"]
        ]
        if exact:
            status = "HOLD_EXACT_DNR"
            reasons.append("same route/purpose has provider-SENT with no later human/provider resolution")
            blockers.append(exact[-1]["event_id"])
    if status == "NO_CONFLICT_FOUND":
        recent = []
        for send, state in sends:
            if state == "BOUNCED":
                continue
            age = int((now - _time(send["occurred_at"], "send.occurred_at")).total_seconds())
            if age < candidate["relationship_cooldown_seconds"]:
                recent.append((send, age))
        if recent:
            send, age = recent[-1]
            status = "HOLD_RECENT_COUNTERPARTY_CONTACT"
            reasons.append(
                f"same counterparty has recent non-bounced provider send "
                f"({age}s < {candidate['relationship_cooldown_seconds']}s)"
            )
            blockers.append(send["event_id"])
    if status == "NO_CONFLICT_FOUND":
        recent = []
        for send, state in sends:
            if (
                state == "BOUNCED"
                or send["opportunity_id"] != candidate["opportunity_id"]
                or send["purpose"] != candidate["purpose"]
            ):
                continue
            age = int((now - _time(send["occurred_at"], "send.occurred_at")).total_seconds())
            if age < candidate["pursuit_cooldown_seconds"]:
                recent.append((send, age))
        if recent:
            send, age = recent[-1]
            status = "HOLD_RECENT_PURSUIT_CONTACT"
            reasons.append(
                f"same opportunity/purpose has recent non-bounced provider send "
                f"({age}s < {candidate['pursuit_cooldown_seconds']}s)"
            )
            blockers.append(send["event_id"])

    replies = [
        e
        for e in events
        if e["kind"] == "HUMAN_REPLY" and e["opportunity_id"] == candidate["opportunity_id"]
    ]
    if status == "NO_CONFLICT_FOUND" and replies:
        status = "HOLD_INBOUND_REVIEW"
        reasons.append("retained human reply exists; relationship should be handled as inbound context")
        blockers.append(replies[-1]["event_id"])
    if not reasons:
        reasons.append(
            "no relationship conflict found in supplied retained packet; "
            "packet completeness and provider authentication are not established"
        )

    # Source-literal authority ceiling. Do not replace this with AUTHORITY.copy():
    # that exported compatibility object is intentionally non-semantic.
    authority = {
        "send_authorized": False,
        "muse_authorized": False,
        "provider_send_proven": False,
        "buyer_acceptance_proven": False,
        "contract_proven": False,
        "payment_proven": False,
        "cash_proven": False,
        "revenue_recognized": False,
    }
    decision = {
        "schema": SCHEMA,
        "evaluation_mode": evaluation_mode,
        "evaluated_at": _format_time(now),
        "status": status,
        "candidate": candidate,
        "blocker_event_ids": blockers,
        "reasons": reasons,
        "retained_event_count": len(events),
        "input_sha256": digest(frozen),
        "authority": authority,
        "next_gate": (
            "HOLD_AND_RECONCILE"
            if status != "NO_CONFLICT_FOUND"
            else "FRESH_SLACK_GMAIL_RECENSUS_THEN_SESSION_BOUND_MUSE_CONSUME_GO"
        ),
        "truth": {
            "retained_packet_complete": False,
            "provider_authentication_established_here": False,
            "no_conflict_is_send_permission": False,
            "evaluation_time_claim": evaluation_mode,
            "evaluation_time_process_origin_authenticated": False,
            "retained_replay_establishes_currentness": False,
        },
    }
    core = {"artifact_schema": ARTIFACT_SCHEMA, "decision": decision}
    return {**core, "receipt_sha256": digest(core)}


def compile_guard(packet: Mapping[str, Any]) -> dict[str, Any]:
    # Sample process wall time directly in the public current compiler rather
    # than through a mutable module-level clock callback.
    from datetime import datetime as _datetime, timezone as _timezone

    frozen = _freeze(packet, "packet")
    now = _datetime.now(_timezone.utc).replace(microsecond=0)
    return _compile_at(frozen, now, "PROCESS_UTC_SNAPSHOT")


def verify_guard(packet: Mapping[str, Any], artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Verify retained artifact integrity, then freshly re-evaluate current semantics.

    A semantic receipt is not a signature. The retained artifact cannot prove
    that its own evaluated_at was originally sampled from process UTC, so this
    verifier never upgrades that retained clock claim. Current diagnostic
    status comes only from a fresh process-time evaluation performed here.
    """
    frozen_artifact = _freeze(artifact, "artifact")
    decision = frozen_artifact.get("decision")
    if type(decision) is not dict:
        raise GuardError("artifact decision missing")
    if decision.get("evaluation_mode") != "PROCESS_UTC_SNAPSHOT":
        raise GuardError("artifact evaluation_mode must be PROCESS_UTC_SNAPSHOT")
    evaluated_at = _time(decision.get("evaluated_at"), "artifact.decision.evaluated_at")

    from datetime import datetime as _datetime, timezone as _timezone

    verify_now = _datetime.now(_timezone.utc).replace(microsecond=0)
    if evaluated_at > verify_now:
        raise GuardError("artifact evaluated_at is in the future")

    frozen_packet = _freeze(packet, "packet")
    expected = _compile_at(frozen_packet, evaluated_at, "PROCESS_UTC_SNAPSHOT")
    if canonical_bytes(frozen_artifact) != canonical_bytes(expected):
        raise GuardError("artifact does not exactly match deterministic retained-time recompile")
    receipt = frozen_artifact.get("receipt_sha256")
    if type(receipt) is not str or not HEX64_RE.fullmatch(receipt):
        raise GuardError("artifact receipt_sha256 malformed")
    core = {"artifact_schema": frozen_artifact["artifact_schema"], "decision": frozen_artifact["decision"]}
    if digest(core) != receipt:
        raise GuardError("artifact receipt mismatch")
    if any(frozen_artifact["decision"]["authority"].values()):
        raise GuardError("artifact authority ceiling widened")

    fresh = _compile_at(frozen_packet, verify_now, "PROCESS_UTC_VERIFY_FRESH")
    if any(fresh["decision"]["authority"].values()):
        raise GuardError("fresh verification authority ceiling widened")

    return {
        "verification_schema": VERIFICATION_SCHEMA,
        "retained_integrity_verified": True,
        "retained_time_process_origin_verified": False,
        "retained_status_is_current": False,
        "artifact_evaluated_at": frozen_artifact["decision"]["evaluated_at"],
        "artifact_status": frozen_artifact["decision"]["status"],
        "verification_evaluated_at": fresh["decision"]["evaluated_at"],
        "fresh_status": fresh["decision"]["status"],
        "fresh_decision": fresh["decision"],
        "fresh_receipt_sha256": fresh["receipt_sha256"],
        "authority": {
            "send_authorized": False,
            "muse_authorized": False,
            "provider_send_proven": False,
            "buyer_acceptance_proven": False,
            "contract_proven": False,
            "payment_proven": False,
            "cash_proven": False,
            "revenue_recognized": False,
        },
    }


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cp = sub.add_parser("compile")
    cp.add_argument("packet", type=Path)
    cp.add_argument("output", type=Path)
    vp = sub.add_parser("verify")
    vp.add_argument("packet", type=Path)
    vp.add_argument("artifact", type=Path)
    args = parser.parse_args(argv)
    if args.command == "compile":
        artifact = compile_guard(load_json(args.packet))
        _write(args.output, artifact)
        print(artifact["receipt_sha256"])
        return 0
    verify_guard(load_json(args.packet), load_json(args.artifact))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
