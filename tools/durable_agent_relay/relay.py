#!/usr/bin/env python3
"""Deterministic, send-nothing reducer for durable multi-model Slack relay events.

This module never calls Slack or another network provider. It reduces bounded JSON events
into content-addressed outbox receipts that a separately authorized transport may consume.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

VERSION = 1
MAX_LINE_BYTES = 16_384
MAX_EVENTS = 10_000
MAX_SUMMARY = 500
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
KINDS = {
    "STARTED",
    "PROGRESS",
    "APPROVAL_REQUESTED",
    "APPROVAL_RESOLVED",
    "COMPLETED",
    "FAILED",
}
TERMINAL = {"COMPLETED", "FAILED"}
PROVIDER_ALIASES = {
    "gpt": "openai",
    "chatgpt": "openai",
    "openai": "openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "google",
    "google": "google",
}
BASE_FIELDS = {"event_id", "run_id", "provider", "sequence", "kind", "occurred_at", "summary"}
APPROVAL_REQUEST_FIELDS = BASE_FIELDS | {"approval_id"}
APPROVAL_RESOLVE_FIELDS = BASE_FIELDS | {"approval_id", "decision", "actor"}


class RelayError(ValueError):
    """Bounded validation/reduction error."""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RelayError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_duplicates)
    except RelayError:
        raise
    except json.JSONDecodeError as exc:
        raise RelayError(f"invalid JSON: {exc.msg}") from exc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _normalize_id(name: str, value: Any) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise RelayError(f"{name} must match {ID_RE.pattern}")
    return value


def _normalize_provider(value: Any) -> str:
    if not isinstance(value, str):
        raise RelayError("provider must be a string")
    provider = value.strip().lower()
    provider = PROVIDER_ALIASES.get(provider, provider)
    if not PROVIDER_RE.fullmatch(provider):
        raise RelayError("provider must be a bounded lowercase slug")
    return provider


def _normalize_timestamp(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 64:
        raise RelayError("occurred_at must be a bounded ISO-8601 string")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise RelayError("occurred_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RelayError("occurred_at must include a timezone")
    parsed = parsed.astimezone(dt.timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_summary(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RelayError("summary must be a string")
    if len(value) > MAX_SUMMARY:
        raise RelayError(f"summary exceeds {MAX_SUMMARY} characters")
    return " ".join(value.split())


def normalize_event(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RelayError("event must be a JSON object")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise RelayError(f"kind must be one of {sorted(KINDS)}")
    allowed = BASE_FIELDS
    if kind == "APPROVAL_REQUESTED":
        allowed = APPROVAL_REQUEST_FIELDS
    elif kind == "APPROVAL_RESOLVED":
        allowed = APPROVAL_RESOLVE_FIELDS
    unknown = set(raw) - allowed
    if unknown:
        raise RelayError(f"unknown event fields: {sorted(unknown)}")
    required = {"event_id", "run_id", "provider", "sequence", "kind", "occurred_at"}
    missing = required - set(raw)
    if missing:
        raise RelayError(f"missing event fields: {sorted(missing)}")
    sequence = raw["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > 1_000_000_000:
        raise RelayError("sequence must be an integer from 1 to 1,000,000,000")
    normalized: dict[str, Any] = {
        "event_id": _normalize_id("event_id", raw["event_id"]),
        "run_id": _normalize_id("run_id", raw["run_id"]),
        "provider": _normalize_provider(raw["provider"]),
        "sequence": sequence,
        "kind": kind,
        "occurred_at": _normalize_timestamp(raw["occurred_at"]),
    }
    summary = _normalize_summary(raw.get("summary"))
    if summary is not None:
        normalized["summary"] = summary
    if kind == "APPROVAL_REQUESTED":
        if "approval_id" not in raw:
            raise RelayError("APPROVAL_REQUESTED requires approval_id")
        normalized["approval_id"] = _normalize_id("approval_id", raw["approval_id"])
    elif kind == "APPROVAL_RESOLVED":
        for field in ("approval_id", "decision", "actor"):
            if field not in raw:
                raise RelayError(f"APPROVAL_RESOLVED requires {field}")
        normalized["approval_id"] = _normalize_id("approval_id", raw["approval_id"])
        decision = raw["decision"]
        if decision not in {"APPROVE", "DENY"}:
            raise RelayError("decision must be APPROVE or DENY")
        normalized["decision"] = decision
        normalized["actor"] = _normalize_id("actor", raw["actor"])
    return normalized


def empty_state() -> dict[str, Any]:
    return {
        "version": VERSION,
        "runs": {},
        "event_index": {},
        "outbox": [],
        "dead_letters": [],
        "dead_letter_ids": {},
    }


def _validate_state_shape(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise RelayError("state must be an object")
    expected = {"version", "runs", "event_index", "outbox", "dead_letters", "dead_letter_ids"}
    if set(state) != expected:
        raise RelayError("state has unexpected shape")
    if state["version"] != VERSION:
        raise RelayError(f"unsupported state version: {state['version']!r}")
    if not all(isinstance(state[k], dict) for k in ("runs", "event_index", "dead_letter_ids")):
        raise RelayError("state map fields must be objects")
    if not all(isinstance(state[k], list) for k in ("outbox", "dead_letters")):
        raise RelayError("state receipt fields must be arrays")
    return state


def load_state(text: str) -> dict[str, Any]:
    parsed = strict_json_loads(text)
    state = _validate_state_shape(parsed)
    return copy.deepcopy(state)


def _dead_letter(state: dict[str, Any], event: dict[str, Any], digest: str, reason: str) -> dict[str, Any]:
    body = {
        "type": "DEAD_LETTER",
        "event_id": event["event_id"],
        "run_id": event["run_id"],
        "event_digest": digest,
        "reason": reason,
    }
    receipt_id = sha256_json(body)
    receipt = {**body, "receipt_id": receipt_id}
    if receipt_id not in state["dead_letter_ids"]:
        state["dead_letter_ids"][receipt_id] = True
        state["dead_letters"].append(receipt)
    return receipt


def _outbox_receipt(event: dict[str, Any], resulting_state: str) -> dict[str, Any]:
    summary = event.get("summary") or event["kind"].replace("_", " ").title()
    body = {
        "type": "SLACK_OUTBOX",
        "event_id": event["event_id"],
        "run_id": event["run_id"],
        "provider": event["provider"],
        "sequence": event["sequence"],
        "kind": event["kind"],
        "state": resulting_state,
        "thread_key": f"run:{event['run_id']}",
        "text": f"{event['run_id']} · {resulting_state} · {summary}",
    }
    return {**body, "receipt_id": sha256_json(body)}


def _reject_semantic(state: dict[str, Any], event: dict[str, Any], digest: str, reason: str) -> dict[str, Any]:
    state["event_index"][event["event_id"]] = {
        "digest": digest,
        "run_id": event["run_id"],
        "outcome": "REJECTED",
        "reason": reason,
    }
    receipt = _dead_letter(state, event, digest, reason)
    return {"outcome": "REJECTED", "reason": reason, "dead_letter": receipt}


def apply_event(state: dict[str, Any], raw_event: Any) -> dict[str, Any]:
    _validate_state_shape(state)
    event = normalize_event(raw_event)
    digest = sha256_json(event)
    event_id = event["event_id"]
    prior_event = state["event_index"].get(event_id)
    if prior_event is not None:
        if prior_event.get("digest") == digest and prior_event.get("run_id") == event["run_id"]:
            return {
                "outcome": "REPLAY_ACCEPTED" if prior_event.get("outcome") == "ACCEPTED" else "REPLAY_REJECTED",
                "event_id": event_id,
            }
        receipt = _dead_letter(state, event, digest, "EVENT_ID_CONFLICT")
        return {"outcome": "REJECTED", "reason": "EVENT_ID_CONFLICT", "dead_letter": receipt}

    run = state["runs"].get(event["run_id"])
    if run is None:
        if event["kind"] != "STARTED" or event["sequence"] != 1:
            return _reject_semantic(state, event, digest, "RUN_MUST_START_WITH_STARTED_SEQUENCE_1")
        run = {
            "provider": event["provider"],
            "last_sequence": 0,
            "last_occurred_at": None,
            "state": "NEW",
            "active_approval_id": None,
            "event_count": 0,
        }
        state["runs"][event["run_id"]] = run
    else:
        if event["provider"] != run["provider"]:
            return _reject_semantic(state, event, digest, "PROVIDER_CHANGED")
        if run["state"] in TERMINAL:
            return _reject_semantic(state, event, digest, "TERMINAL_RUN_MUTATION")
        if event["sequence"] != run["last_sequence"] + 1:
            return _reject_semantic(state, event, digest, "SEQUENCE_GAP_OR_REORDER")
        if run["last_occurred_at"] is not None and event["occurred_at"] < run["last_occurred_at"]:
            return _reject_semantic(state, event, digest, "TIME_REGRESSION")

    kind = event["kind"]
    current = run["state"]
    resulting = current
    if kind == "STARTED":
        if current != "NEW":
            return _reject_semantic(state, event, digest, "DUPLICATE_START")
        resulting = "RUNNING"
    elif kind == "PROGRESS":
        if current != "RUNNING":
            return _reject_semantic(state, event, digest, "PROGRESS_REQUIRES_RUNNING")
        resulting = "RUNNING"
    elif kind == "APPROVAL_REQUESTED":
        if current != "RUNNING":
            return _reject_semantic(state, event, digest, "APPROVAL_REQUEST_REQUIRES_RUNNING")
        run["active_approval_id"] = event["approval_id"]
        resulting = "AWAITING_APPROVAL"
    elif kind == "APPROVAL_RESOLVED":
        if current != "AWAITING_APPROVAL":
            return _reject_semantic(state, event, digest, "APPROVAL_RESOLUTION_REQUIRES_PENDING_REQUEST")
        if event["approval_id"] != run["active_approval_id"]:
            return _reject_semantic(state, event, digest, "APPROVAL_ID_MISMATCH")
        run["active_approval_id"] = None
        resulting = "RUNNING" if event["decision"] == "APPROVE" else "FAILED"
    elif kind == "COMPLETED":
        if current != "RUNNING":
            return _reject_semantic(state, event, digest, "COMPLETION_REQUIRES_RUNNING")
        resulting = "COMPLETED"
    elif kind == "FAILED":
        if current not in {"RUNNING", "AWAITING_APPROVAL"}:
            return _reject_semantic(state, event, digest, "FAILURE_REQUIRES_ACTIVE_RUN")
        run["active_approval_id"] = None
        resulting = "FAILED"
    else:
        raise RelayError("unreachable event kind")

    run["state"] = resulting
    run["last_sequence"] = event["sequence"]
    run["last_occurred_at"] = event["occurred_at"]
    run["event_count"] += 1
    receipt = _outbox_receipt(event, resulting)
    state["event_index"][event_id] = {
        "digest": digest,
        "run_id": event["run_id"],
        "outcome": "ACCEPTED",
        "receipt_id": receipt["receipt_id"],
    }
    state["outbox"].append(receipt)
    return {"outcome": "ACCEPTED", "receipt": receipt}


def project(state: dict[str, Any]) -> dict[str, Any]:
    _validate_state_shape(state)
    threads = []
    for run_id in sorted(state["runs"]):
        run = state["runs"][run_id]
        threads.append(
            {
                "run_id": run_id,
                "thread_key": f"run:{run_id}",
                "provider": run["provider"],
                "state": run["state"],
                "last_sequence": run["last_sequence"],
                "event_count": run["event_count"],
                "active_approval_id": run["active_approval_id"],
            }
        )
    counts: dict[str, int] = {}
    for thread in threads:
        counts[thread["state"]] = counts.get(thread["state"], 0) + 1
    body = {
        "version": VERSION,
        "threads": threads,
        "state_counts": dict(sorted(counts.items())),
        "outbox_count": len(state["outbox"]),
        "dead_letter_count": len(state["dead_letters"]),
        "outbox_receipt_ids": [r["receipt_id"] for r in state["outbox"]],
        "dead_letter_receipt_ids": [r["receipt_id"] for r in state["dead_letters"]],
    }
    return {**body, "projection_digest": sha256_json(body)}


def reduce_events(events: Iterable[Any], state: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current = empty_state() if state is None else copy.deepcopy(_validate_state_shape(state))
    results = []
    for count, event in enumerate(events, start=1):
        if count > MAX_EVENTS:
            raise RelayError(f"event count exceeds {MAX_EVENTS}")
        results.append(apply_event(current, event))
    return current, results


def parse_jsonl(text: str) -> list[Any]:
    events: list[Any] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            raise RelayError(f"line {number} exceeds {MAX_LINE_BYTES} bytes")
        if len(events) >= MAX_EVENTS:
            raise RelayError(f"event count exceeds {MAX_EVENTS}")
        try:
            events.append(strict_json_loads(line))
        except RelayError as exc:
            raise RelayError(f"line {number}: {exc}") from exc
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, help="bounded JSONL event file")
    parser.add_argument("--state-in", type=Path, help="optional prior reducer state JSON")
    parser.add_argument("--state-out", type=Path, help="optional path to write next reducer state JSON")
    args = parser.parse_args(argv)
    try:
        text = args.events.read_text(encoding="utf-8")
        events = parse_jsonl(text)
        state = empty_state()
        if args.state_in:
            state = load_state(args.state_in.read_text(encoding="utf-8"))
        next_state, results = reduce_events(events, state)
        projection = project(next_state)
        if args.state_out:
            args.state_out.write_text(json.dumps(next_state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        output = {"results": results, "projection": projection}
        print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except (OSError, RelayError) as exc:
        print(f"durable-agent-relay: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
