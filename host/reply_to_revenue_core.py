#!/usr/bin/env python3
"""Single-generation reply-to-revenue core.

The retained implementation is stored as non-importable source beside this
module. This executable/import surface loads that implementation, replaces its
observation loader with one authoritative full-envelope reducer, installs the
chronology-safe contact policy into the retained implementation globals, and
then re-exports the public API. Every supported wrapper, direct import, and CLI
path therefore validates and reduces through the same authoritative graph.
"""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any


_IMPL_PATH = Path(__file__).with_name("reply_to_revenue_core_impl.source")
_impl = types.ModuleType("_commons_reply_to_revenue_core_impl")
_impl.__file__ = str(_IMPL_PATH)
_impl.__package__ = None
exec(
    compile(_IMPL_PATH.read_text(encoding="utf-8"), str(_IMPL_PATH), "exec"),
    _impl.__dict__,
)

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

PUBLIC_LIMITS = [
    (
        "ingest each inbound event_ref once; collision on same ref with a "
        "different full observation envelope"
        if item.startswith("ingest each inbound event_ref once;")
        else item
    )
    for item in _impl.PUBLIC_LIMITS
]
_impl.PUBLIC_LIMITS = PUBLIC_LIMITS


def load_observations(path: Path = OBSERVATIONS_PATH) -> dict[str, Any]:
    """Read, validate, deduplicate, and reduce one immutable generation."""
    value = read_object(path)
    _exact_keys(
        value,
        {"schema_version", "kind", "measured_at", "monitor", "events"},
        "observations",
    )
    if value["schema_version"] != "commons-reply-to-revenue-observations/v1":
        raise ReplyRevenueError("unsupported observations version")
    if value["kind"] != "REPLY_TO_REVENUE_OBSERVATIONS":
        raise ReplyRevenueError("unsupported observations kind")
    parse_time(value["measured_at"])
    monitor = value["monitor"]
    if not isinstance(monitor, dict):
        raise ReplyRevenueError("monitor must be an object")
    _exact_keys(
        monitor,
        {"connector", "status", "mailbox_claim", "sends", "queries", "attributed_inbound"},
        "monitor",
    )
    if type(monitor["sends"]) is not int or monitor["sends"] != 0:
        raise ReplyRevenueError("monitor.sends must be 0")
    if type(monitor["queries"]) is not int or monitor["queries"] < 0:
        raise ReplyRevenueError("monitor.queries must be a non-negative integer")
    if type(monitor["attributed_inbound"]) is not int or monitor["attributed_inbound"] < 0:
        raise ReplyRevenueError("monitor.attributed_inbound must be a non-negative integer")
    events = value["events"]
    if not isinstance(events, list):
        raise ReplyRevenueError("events must be an array")

    seen_refs: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    cleaned: list[dict[str, Any]] = []
    fields = {
        "event_ref",
        "received_at",
        "prospect_key",
        "payload_sha256",
        "markers",
        "provider",
        "matched_receipt_id",
        "requested_classification",
    }
    for index, event in enumerate(events):
        where = f"events[{index}]"
        if not isinstance(event, dict):
            raise ReplyRevenueError(f"{where} must be an object")
        _exact_keys(event, fields, where)
        if not OPAQUE_RE.fullmatch(event["event_ref"]):
            raise ReplyRevenueError(f"{where}.event_ref is invalid")
        parse_time(event["received_at"])
        if not PROSPECT_RE.fullmatch(event["prospect_key"]):
            raise ReplyRevenueError(f"{where}.prospect_key is invalid")
        if not SHA256_RE.fullmatch(event["payload_sha256"]):
            raise ReplyRevenueError(f"{where}.payload_sha256 is invalid")
        if not isinstance(event["markers"], list):
            raise ReplyRevenueError(f"{where}.markers must be an array")
        requested = event["requested_classification"]
        if requested is not None and requested not in CLASSIFICATIONS:
            raise ReplyRevenueError(f"{where}.requested_classification is invalid")

        identity = sha256_text(canonical_text(event))
        previous = seen_refs.get(event["event_ref"])
        if previous is not None and previous != identity:
            raise CollisionError(
                f"duplicate event_ref with different observation envelope: {event['event_ref']}"
            )
        hashed = seen_hashes.get(event["payload_sha256"])
        if hashed and hashed != event["event_ref"]:
            raise CollisionError("duplicate payload_sha256 under a second event_ref")
        if previous is not None:
            continue
        seen_refs[event["event_ref"]] = identity
        seen_hashes[event["payload_sha256"]] = event["event_ref"]
        verdict = classify_signals(event["markers"], requested)
        cleaned.append(
            {
                "event_ref": event["event_ref"],
                "received_at": event["received_at"],
                "prospect_key": event["prospect_key"],
                "payload_sha256": event["payload_sha256"],
                "provider": event["provider"],
                "matched_receipt_id": event["matched_receipt_id"],
                **verdict,
            }
        )

    if monitor["attributed_inbound"] != len(cleaned):
        raise ReplyRevenueError(
            "monitor.attributed_inbound does not match ingested unique events"
        )
    value = dict(value)
    value["events"] = cleaned
    _assert_observation_window(value["measured_at"], cleaned)
    return value


_ORIGINAL_REDUCE_CONTACT_STATE = _impl._reduce_contact_state
_MACHINE_CLASSIFICATIONS = frozenset({"DELIVERY_FAILURE", "AUTO_RESPONSE"})


def _latest_human_bucket(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    semantic = [
        event
        for event in events
        if event.get("classification") in HUMAN_STATE_CLASSIFICATIONS
    ]
    if not semantic:
        return []
    stamped = [
        (parse_time(str(event["received_at"])), event)
        for event in semantic
    ]
    latest_time = max(stamp for stamp, _ in stamped)
    return [event for stamp, event in stamped if stamp == latest_time]


def _reduce_contact_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Preserve explicit DNC authority in an equal-time semantic conflict."""
    # Preserve every validation/error contract owned by the retained reducer.
    inherited_state = _ORIGINAL_REDUCE_CONTACT_STATE(events)
    latest_semantic = _latest_human_bucket(events)
    opt_outs = [
        event
        for event in latest_semantic
        if event.get("classification") == "OPT_OUT"
    ]
    if opt_outs:
        effective_event = min(
            opt_outs,
            key=lambda item: str(item.get("event_ref") or ""),
        )
        return {
            "classification": "OPT_OUT",
            "lane": "CLOSED",
            "next_action": "DNC/CLOSE",
            "handoff": None,
            "effective_event": effective_event,
        }
    return inherited_state


def _positive_context(events: list[dict[str, Any]]) -> str:
    machine_classes = sorted(
        {
            str(event.get("classification"))
            for event in events
            if event.get("classification") in _MACHINE_CLASSIFICATIONS
        }
    )
    if not machine_classes:
        return (
            "effective human inbound classified POSITIVE_SCOPE; "
            "no machine delivery-failure or auto-response observations were recorded"
        )
    recorded = ", ".join(machine_classes)
    return (
        "effective human inbound classified POSITIVE_SCOPE; "
        f"recorded machine observations ({recorded}) do not override human semantics"
    )


def surface_positives(
    contacts: list[dict[str, Any]],
    inbound: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    positives: list[dict[str, Any]] = []
    inbound_by_key: dict[str, list[dict[str, Any]]] = {}
    for event in inbound:
        inbound_by_key.setdefault(event["prospect_key"], []).append(event)
    for contact in contacts:
        if contact["lane"] != "HUMAN_POSITIVE":
            continue
        events = inbound_by_key.get(contact["prospect_key"], [])
        state = _reduce_contact_state(events)
        effective_event = state["effective_event"]
        if state["lane"] != "HUMAN_POSITIVE" or effective_event is None:
            raise ReplyRevenueError(
                f"positive contact {contact['prospect_key']} lacks an effective POSITIVE_SCOPE event"
            )
        if effective_event.get("classification") != "POSITIVE_SCOPE":
            raise ReplyRevenueError(
                f"positive contact {contact['prospect_key']} resolved to non-positive evidence"
            )
        positives.append(
            {
                "prospect_key": contact["prospect_key"],
                "organization": contact["organization"],
                "event_ref": effective_event["event_ref"],
                "received_at": effective_event["received_at"],
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": ACCEPTANCE_TOOL,
                "context": _positive_context(events),
                "buyer_interest": True,
            }
        )
    positives.sort(key=lambda item: item["prospect_key"])
    return positives


# Functions copied from the retained implementation keep that module's globals.
# Install every repaired authority into the retained graph before any production
# build/main path can run, then keep this direct-import surface identical.
_impl.load_observations = load_observations
_impl._reduce_contact_state = _reduce_contact_state
_impl.surface_positives = surface_positives

if _impl.load_observations is not load_observations:
    raise ImportError("reply-to-revenue observation authority was not installed")
if _impl._reduce_contact_state is not _reduce_contact_state:
    raise ImportError("reply-to-revenue reducer authority was not installed")
if _impl.surface_positives is not surface_positives:
    raise ImportError("reply-to-revenue positive-surface authority was not installed")


if __name__ == "__main__":
    raise SystemExit(_impl.main())
