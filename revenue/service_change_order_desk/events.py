from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Mapping, Sequence

from .common import (
    GENESIS,
    MAX_EVENTS,
    DeskError,
    _digest,
    _identifier,
    _integer,
    _list,
    _object,
    _text,
    _timestamp,
    sha256_json,
)


def _event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key != "event_digest"}


def _transition(state: str, kind: str) -> str:
    transitions = {
        ("DRAFT", "SUBMIT_FOR_REVIEW"): "READY_FOR_HUMAN_REVIEW",
        ("DRAFT", "CANCEL"): "CANCELLED",
        ("READY_FOR_HUMAN_REVIEW", "APPROVE"): "APPROVED",
        ("READY_FOR_HUMAN_REVIEW", "REJECT"): "REJECTED",
        ("READY_FOR_HUMAN_REVIEW", "REQUEST_REVISION"): "REVISION_REQUESTED",
        ("READY_FOR_HUMAN_REVIEW", "CANCEL"): "CANCELLED",
    }
    try:
        return transitions[(state, kind)]
    except KeyError as exc:
        raise DeskError("INVALID_STATE_TRANSITION", f"{state}->{kind}") from exc


def _parse_event(raw: Any, *, index: int) -> dict[str, Any]:
    path = f"$.events[{index}]"
    row = _object(
        raw,
        path=path,
        required=(
            "event_id", "seq", "kind", "occurred_at", "actor_ref", "expected_state",
            "expected_change_version", "prev_event_digest", "decision_ref_sha256", "event_digest",
        ),
    )
    decision = row["decision_ref_sha256"]
    if decision is not None:
        decision = _digest(decision, path=f"{path}.decision_ref_sha256")
    return {
        "event_id": _identifier(row["event_id"], path=f"{path}.event_id"),
        "seq": _integer(row["seq"], path=f"{path}.seq", minimum=1, maximum=MAX_EVENTS),
        "kind": _text(row["kind"], path=f"{path}.kind", maximum=32),
        "occurred_at": _timestamp(row["occurred_at"], path=f"{path}.occurred_at").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor_ref": _identifier(row["actor_ref"], path=f"{path}.actor_ref"),
        "expected_state": _text(row["expected_state"], path=f"{path}.expected_state", maximum=32),
        "expected_change_version": _integer(row["expected_change_version"], path=f"{path}.expected_change_version", minimum=1, maximum=1_000_000),
        "prev_event_digest": GENESIS if row["prev_event_digest"] == GENESIS else _digest(row["prev_event_digest"], path=f"{path}.prev_event_digest"),
        "decision_ref_sha256": decision,
        "event_digest": _digest(row["event_digest"], path=f"{path}.event_digest"),
    }


def validate_events(events: Any, change: Mapping[str, Any], evaluation: datetime) -> tuple[list[dict[str, Any]], str, str]:
    rows = _list(events, path="$.events", maximum=MAX_EVENTS, allow_empty=True)
    parsed: list[dict[str, Any]] = []
    state = "DRAFT"
    previous = GENESIS
    last_time = _timestamp(change["created_at"], path="$.change.created_at")
    expires = _timestamp(change["expires_at"], path="$.change.expires_at")
    seen: set[str] = set()
    decision_evidence = {
        item["sha256"] for item in change.get("evidence_refs", [])
        if isinstance(item, dict) and item.get("kind") == "buyer_decision"
    }
    for index, raw in enumerate(rows):
        event = _parse_event(raw, index=index)
        if event["event_id"] in seen:
            raise DeskError("DUPLICATE_EVENT_ID")
        seen.add(event["event_id"])
        if event["seq"] != index + 1:
            raise DeskError("NONCONTIGUOUS_EVENT_SEQUENCE")
        if event["prev_event_digest"] != previous:
            raise DeskError("EVENT_PREV_DIGEST_MISMATCH")
        occurred = _timestamp(event["occurred_at"], path=f"$.events[{index}].occurred_at")
        if occurred < last_time or occurred > evaluation or occurred > expires:
            raise DeskError("INVALID_EVENT_TIME")
        if event["expected_state"] != state:
            raise DeskError("EVENT_EXPECTED_STATE_MISMATCH")
        if event["expected_change_version"] != change["change_version"]:
            raise DeskError("EVENT_CHANGE_VERSION_MISMATCH")
        if event["kind"] == "SUBMIT_FOR_REVIEW":
            if event["decision_ref_sha256"] is not None:
                raise DeskError("UNEXPECTED_DECISION_REFERENCE")
        elif event["kind"] in {"APPROVE", "REJECT", "REQUEST_REVISION", "CANCEL"}:
            if event["decision_ref_sha256"] is None:
                raise DeskError("DECISION_REFERENCE_REQUIRED")
            if event["decision_ref_sha256"] not in decision_evidence:
                raise DeskError("DECISION_REFERENCE_NOT_IN_EVIDENCE")
        else:
            raise DeskError("UNKNOWN_EVENT_KIND")
        expected_digest = sha256_json(_event_payload(event))
        if event["event_digest"] != expected_digest:
            raise DeskError("EVENT_DIGEST_MISMATCH")
        state = _transition(state, event["kind"])
        previous = event["event_digest"]
        last_time = occurred
        parsed.append(event)
    return parsed, state, previous


def append_event(
    existing_events: Sequence[Mapping[str, Any]],
    *,
    change: Mapping[str, Any],
    evaluation_time: str,
    event_id: str,
    kind: str,
    occurred_at: str,
    actor_ref: str,
    expected_state: str,
    expected_change_version: int,
    decision_ref_sha256: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    evaluation = _timestamp(evaluation_time, path="$.evaluation_time")
    parsed, state, previous = validate_events(list(existing_events), change, evaluation)
    event_id = _identifier(event_id, path="$.new_event.event_id")
    for existing in parsed:
        if existing["event_id"] == event_id:
            replay_fields = {
                "kind": kind,
                "occurred_at": occurred_at,
                "actor_ref": actor_ref,
                "expected_state": expected_state,
                "expected_change_version": expected_change_version,
                "decision_ref_sha256": decision_ref_sha256,
            }
            if all(existing[key] == value for key, value in replay_fields.items()):
                return copy.deepcopy(parsed), True
            raise DeskError("EVENT_ID_CONFLICT")
    if expected_state != state:
        raise DeskError("EVENT_EXPECTED_STATE_MISMATCH")
    event: dict[str, Any] = {
        "event_id": event_id,
        "seq": len(parsed) + 1,
        "kind": _text(kind, path="$.new_event.kind", maximum=32),
        "occurred_at": _timestamp(occurred_at, path="$.new_event.occurred_at").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor_ref": _identifier(actor_ref, path="$.new_event.actor_ref"),
        "expected_state": expected_state,
        "expected_change_version": _integer(expected_change_version, path="$.new_event.expected_change_version", minimum=1, maximum=1_000_000),
        "prev_event_digest": previous,
        "decision_ref_sha256": None if decision_ref_sha256 is None else _digest(decision_ref_sha256, path="$.new_event.decision_ref_sha256"),
    }
    event["event_digest"] = sha256_json(event)
    candidate = [*parsed, event]
    validate_events(candidate, change, evaluation)
    return candidate, False
