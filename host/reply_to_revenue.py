#!/usr/bin/env python3
"""Chronology-safe reply-to-revenue entrypoint.

The implementation inherited from the original chronology carrier lives in
``reply_to_revenue_core.py``.  This entrypoint applies two narrow policy fixes:
explicit opt-out evidence keeps the DNC boundary during equal-time conflicts,
and positive surfaces describe recorded machine observations truthfully.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


_CORE_PATH = Path(__file__).with_name("reply_to_revenue_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "_commons_reply_to_revenue_core",
    _CORE_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load reply-to-revenue core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

_ORIGINAL_REDUCE_CONTACT_STATE = _core._reduce_contact_state
_MACHINE_CLASSIFICATIONS = frozenset({"DELIVERY_FAILURE", "AUTO_RESPONSE"})


def _latest_human_bucket(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    semantic = [
        event
        for event in events
        if event.get("classification") in _core.HUMAN_STATE_CLASSIFICATIONS
    ]
    if not semantic:
        return []
    stamped = [
        (_core.parse_time(str(event["received_at"])), event)
        for event in semantic
    ]
    latest_time = max(stamp for stamp, _ in stamped)
    return [event for stamp, event in stamped if stamp == latest_time]


def _reduce_contact_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Preserve explicit DNC authority in an equal-time semantic conflict."""
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
    return _ORIGINAL_REDUCE_CONTACT_STATE(events)


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
            raise _core.ReplyRevenueError(
                f"positive contact {contact['prospect_key']} lacks an effective POSITIVE_SCOPE event"
            )
        if effective_event.get("classification") != "POSITIVE_SCOPE":
            raise _core.ReplyRevenueError(
                f"positive contact {contact['prospect_key']} resolved to non-positive evidence"
            )
        positives.append(
            {
                "prospect_key": contact["prospect_key"],
                "organization": contact["organization"],
                "event_ref": effective_event["event_ref"],
                "received_at": effective_event["received_at"],
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": _core.ACCEPTANCE_TOOL,
                "context": _positive_context(events),
                "buyer_interest": True,
            }
        )
    positives.sort(key=lambda item: item["prospect_key"])
    return positives


# Core functions resolve globals in the core module.  Install the corrected
# reducers there before re-exporting the public surface from this entrypoint.
_core._reduce_contact_state = _reduce_contact_state
_core.surface_positives = surface_positives

for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_core.main())
