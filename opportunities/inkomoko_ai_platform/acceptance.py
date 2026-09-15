"""Deterministic synthetic acceptance checks for the Inkomoko pursuit carrier.

This module deliberately models only synthetic/non-production evidence.  It does
not connect to WhatsApp, CBS, Inkobook, Power BI, or any buyer system.
"""
from __future__ import annotations

from typing import Any


class AcceptanceError(ValueError):
    pass


REQUIRED_SCENARIOS = {
    "progressive_learning",
    "content_revision",
    "rbac",
    "multilingual_routing",
    "channel_continuity",
    "human_escalation",
    "adapter_boundaries",
    "replay_idempotency",
    "stale_content_policy",
    "analytics_events",
}

ALLOWED_CHANNELS = {"WEB", "WHATSAPP_SYNTHETIC"}
ALLOWED_LANGUAGES = {"en", "fr", "rw", "sw"}
ALLOWED_ROLES = {"LEARNER", "COACH", "ADMIN"}


def _is_int(value: Any) -> bool:
    return type(value) is int


def _text(value: Any, field: str, *, maximum: int = 160) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise AcceptanceError(f"{field} must be non-empty bounded text")
    return value


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise AcceptanceError(f"{field} must be boolean")
    return value


def _event_list(case: dict[str, Any]) -> list[dict[str, Any]]:
    events = case.get("events")
    if type(events) is not list or not events or len(events) > 40:
        raise AcceptanceError("events must be a non-empty bounded list")
    for event in events:
        if type(event) is not dict:
            raise AcceptanceError("event must be an object")
        if set(event) != {"id", "kind", "channel", "language", "role", "sequence", "payload_ref"}:
            raise AcceptanceError("event keys are exact")
        _text(event["id"], "event.id", maximum=80)
        _text(event["kind"], "event.kind", maximum=80)
        if event["channel"] not in ALLOWED_CHANNELS:
            raise AcceptanceError("unsupported channel")
        if event["language"] not in ALLOWED_LANGUAGES:
            raise AcceptanceError("unsupported language")
        if event["role"] not in ALLOWED_ROLES:
            raise AcceptanceError("unsupported role")
        if not _is_int(event["sequence"]) or event["sequence"] < 0:
            raise AcceptanceError("sequence must be a non-negative integer")
        _text(event["payload_ref"], "event.payload_ref", maximum=120)
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)):
        raise AcceptanceError("duplicate event id")
    return events


def _ordered(events: list[dict[str, Any]]) -> bool:
    seq = [e["sequence"] for e in events]
    return seq == sorted(seq) and len(seq) == len(set(seq))


def _has(events: list[dict[str, Any]], kind: str) -> bool:
    return any(e["kind"] == kind for e in events)


def _scenario_pass(case: dict[str, Any], events: list[dict[str, Any]]) -> tuple[bool, str]:
    sid = case["scenario_id"]
    if sid == "progressive_learning":
        return (_ordered(events) and all(_has(events, f"STAGE_{i}_COMPLETE") for i in range(1, 5)), "four ordered learning stages")
    if sid == "content_revision":
        return (_ordered(events) and _has(events, "CONTENT_VERSION_OLD") and _has(events, "CONTENT_VERSION_NEW") and _has(events, "STALE_VERSION_REJECTED"), "revision invalidates stale content")
    if sid == "rbac":
        roles = {e["role"] for e in events if e["kind"] == "AUTHORIZED_ACTION"}
        return (_has(events, "UNAUTHORIZED_ACTION_REJECTED") and bool(roles), "role boundary enforced")
    if sid == "multilingual_routing":
        langs = {e["language"] for e in events if e["kind"] == "ROUTED_RESPONSE"}
        return (langs == ALLOWED_LANGUAGES, "all four required languages routed")
    if sid == "channel_continuity":
        channels = {e["channel"] for e in events if e["kind"] in {"SESSION_OPEN", "SESSION_RESUME"}}
        refs = {e["payload_ref"] for e in events if e["kind"] in {"SESSION_OPEN", "SESSION_RESUME"}}
        return (channels == ALLOWED_CHANNELS and len(refs) == 1, "cross-channel synthetic session continuity")
    if sid == "human_escalation":
        kinds = [e["kind"] for e in events]
        ok = "ESCALATION_REQUESTED" in kinds and "CONTEXT_PRESERVED" in kinds and kinds.index("ESCALATION_REQUESTED") < kinds.index("CONTEXT_PRESERVED")
        return (ok, "human escalation preserves context")
    if sid == "adapter_boundaries":
        required = {"CBS_ADAPTER_STUB", "INKOBOOK_ADAPTER_STUB", "POWERBI_ADAPTER_STUB", "LIVE_CREDENTIAL_REFUSED"}
        return (required.issubset({e["kind"] for e in events}), "provider-neutral stubs and live-credential refusal")
    if sid == "replay_idempotency":
        return (_has(events, "DUPLICATE_EFFECT_COLLAPSED") and _has(events, "CONFLICTING_REPLAY_REJECTED"), "duplicate collapse and conflict rejection")
    if sid == "stale_content_policy":
        return (_has(events, "STALE_POLICY_REJECTED") and _has(events, "CURRENT_POLICY_ACCEPTED"), "stale/current policy separation")
    if sid == "analytics_events":
        return (_has(events, "ANALYTICS_EVENT_EMITTED") and _has(events, "ANALYTICS_DUPLICATE_COLLAPSED"), "analytics event idempotency")
    raise AcceptanceError("unknown scenario")


def evaluate_acceptance(cases: Any) -> dict[str, Any]:
    if type(cases) is not list or len(cases) != len(REQUIRED_SCENARIOS):
        raise AcceptanceError("acceptance suite must contain exactly the required scenario count")
    by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        if type(case) is not dict or set(case) != {"scenario_id", "synthetic", "events"}:
            raise AcceptanceError("scenario keys are exact")
        sid = _text(case["scenario_id"], "scenario_id", maximum=80)
        if sid not in REQUIRED_SCENARIOS or sid in by_id:
            raise AcceptanceError("unknown or duplicate scenario_id")
        if _bool(case["synthetic"], "synthetic") is not True:
            raise AcceptanceError("checked-in acceptance evidence must be explicitly synthetic")
        by_id[sid] = case
    if set(by_id) != REQUIRED_SCENARIOS:
        raise AcceptanceError("acceptance scenario universe mismatch")

    rows = []
    for sid in sorted(REQUIRED_SCENARIOS):
        events = _event_list(by_id[sid])
        passed, reason = _scenario_pass(by_id[sid], events)
        rows.append({"scenario_id": sid, "passed": bool(passed), "reason": reason})
    return {
        "synthetic_only": True,
        "passed": all(row["passed"] for row in rows),
        "scenario_count": len(rows),
        "rows": rows,
    }
