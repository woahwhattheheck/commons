"""Reference emitter and continue-from-observation helper.

Emitting an event does not schedule work. continue_from_observation returns
an advisory envelope a caller may post through the existing open carrier.
"""
from __future__ import annotations

from typing import Any

from protocol.events import event_id_for, parse_event
from protocol.projector import project
from protocol.schema import EVENT_KINDS, PROTOCOL_ID, PROTOCOL_VERSION, UNKNOWN


def emit(
    kind: str,
    *,
    session_id: str = UNKNOWN,
    task_id: str = UNKNOWN,
    run_id: str = UNKNOWN,
    ts: str = UNKNOWN,
    **fields: Any,
) -> dict[str, Any]:
    kind = str(kind or UNKNOWN).upper()
    if kind not in EVENT_KINDS:
        kind = UNKNOWN
    payload = {
        "protocol": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "kind": kind,
        "session_id": session_id,
        "task_id": task_id,
        "run_id": run_id,
        "ts": ts,
        **fields,
    }
    payload["event_id"] = event_id_for(payload)
    return parse_event(payload)


def continue_from_observation(
    snapshot: dict[str, Any] | None = None,
    *,
    session_id: str = "",
    events: list | None = None,
    legacy: dict | None = None,
    now: str = "2026-08-28T09:30:00Z",
) -> dict[str, Any]:
    snap = snapshot or project(events or [], now=now, legacy=legacy or {})
    target = None
    if session_id:
        for row in snap.get("sessions") or []:
            if row.get("session_id") == session_id:
                target = row
                break
    if target is None:
        routes = snap.get("routes") or []
        if routes:
            sid = routes[0].get("session_id")
            for row in snap.get("sessions") or []:
                if row.get("session_id") == sid:
                    target = row
                    break
    handoff = (snap.get("briefing") or {}).get("handoff") or {}
    event = emit(
        "HANDOFF" if target and target.get("state") not in {"TERMINAL", "RELEASED", "SUPERSEDED"} else "START",
        session_id=(target or {}).get("session_id") or UNKNOWN,
        task_id=(target or {}).get("task_id") or UNKNOWN,
        run_id=(target or {}).get("run_id") or UNKNOWN,
        ts=now,
        objective=(target or {}).get("objective") or "observe live Commons work and continue a non-conflicting leftover",
        parent_ids=[(target or {}).get("last_event_id")] if target and target.get("last_event_id") not in {None, UNKNOWN} else [],
        attention_reason="lineage-linked continuation; do not replay a finished prompt",
    )
    envelope = {
        "from": "UNSEATED",
        "to": "TABLE",
        "id": ("obs-cont-" + event["event_id"])[:80],
        "body": "PROTOCOL HANDOFF %s\n%s" % (PROTOCOL_ID, "\n".join(handoff.get("read_this") or [])),
        "board": "TABLE",
        "subject": "observatory continuation",
        "kind": "POST",
    }
    return {
        "advisory": True,
        "authority": False,
        "replay_finished_prompt": False,
        "snapshot_digest": snap.get("digest"),
        "cockpit": (snap.get("cockpit") or {}).get("lines") or [],
        "target_session": (target or {}).get("session_id") or UNKNOWN,
        "recommended_event": event,
        "open_carrier_envelope": envelope,
        "collisions": snap.get("collisions") or [],
        "attention": snap.get("attention") or [],
        "economy": snap.get("economy") or {},
        "routes": (snap.get("routes") or [])[:5],
        "briefing": snap.get("briefing") or {},
    }


EXAMPLES = {
    "codex_local": emit(
        "START",
        session_id="codex-local-desk-01",
        task_id="task-protocol-observatory",
        run_id="run-codex-local-01",
        ts="2026-08-28T08:00:00Z",
        model="OpenAI Codex",
        harness="Codex desktop local",
        classification="LOCAL",
        tools=["filesystem", "github_write", "unittest"],
        objective="Land Protocol v0.1 and Observatory on current main",
        claimed_paths=["protocol/", "observatory.html", "host/observatory.py"],
        semantic_area="observatory-protocol",
        dedupe_key="protocol-v0.1-observatory",
    ),
    "codex_cloud": emit(
        "HEARTBEAT",
        session_id="codex-cloud-01",
        task_id="task-cloud-review",
        run_id="run-codex-cloud-01",
        ts="2026-08-28T08:05:00Z",
        model="OpenAI Codex",
        harness="ChatGPT cloud",
        classification="CLOUD",
        tools=["github_write"],
        objective="Review a candidate without replaying Grok prompts",
    ),
    "grok_browser": emit(
        "START",
        session_id="grok-browser-01",
        task_id="task-grok-capture",
        run_id="run-grok-browser-01",
        ts="2026-08-28T08:10:00Z",
        model="Grok",
        harness="grok.com browser",
        classification="BROWSER",
        tools=["browser", "grok.com"],
        grok_url="https://grok.com/c/example-rid",
        objective="Capture one intentional grok.com run",
        dedupe_key="https://grok.com/c/example-rid",
    ),
    "slack_automation": emit(
        "HEARTBEAT",
        session_id="slack-watchdog-01",
        task_id="rivet-watchdog-canary-20260825-01",
        run_id="run-slack-auto-01",
        ts="2026-08-28T08:15:00Z",
        harness="slack automation",
        classification="AUTOMATION",
        tools=["slack_read", "slack_send"],
        origin={"thread_id": "1787900000.000001", "message_id": "1787900000.000002"},
        objective="Mirror receipts; do not mint sessions from Slack authors",
    ),
    "unknown_future": emit(
        "START",
        ts="2026-08-28T08:20:00Z",
        objective="Join Commons from an unnamed future harness",
    ),
}
