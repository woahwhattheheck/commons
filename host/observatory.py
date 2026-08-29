"""Commons host projector for Observatory.

Reads existing bakes and JobStore files. Writes observatory.json as a bake.
Does not mutate p/{id}.md, presence, jobs, or cash ledgers.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from protocol.emit import continue_from_observation
from protocol.projector import project

SNAPSHOT_REL = "observatory.json"


def _paginate(items: list, arguments: dict[str, Any], *, field: str) -> tuple[list, dict[str, Any]]:
    """Deterministic offset/limit pagination. Unknown values become 0."""
    if not isinstance(items, list):
        items = []
    try:
        raw_off = arguments.get("offset")
        if raw_off in (None, ""):
            raw_off = arguments.get("cursor") or 0
        offset = int(raw_off)
    except (TypeError, ValueError):
        offset = 0
    if offset < 0:
        offset = 0
    try:
        raw_lim = arguments.get("limit")
        limit = int(raw_lim) if raw_lim not in (None, "") else 0
    except (TypeError, ValueError):
        limit = 0
    if limit < 0:
        limit = 0
    meta = {
        "field": field,
        "total": len(items),
        "offset": offset,
        "limit": limit or None,
        "next_cursor": None,
        "deterministic": True,
    }
    if limit <= 0:
        return items[offset:], meta
    sliced = items[offset:offset + limit]
    nxt = offset + limit
    if nxt < len(items):
        meta["next_cursor"] = str(nxt)
    return sliced, meta


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_legacy(root: str | None = None) -> dict[str, Any]:
    root = root or ROOT
    jobs = []
    jobs_dir = os.path.join(root, "wake_jobs")
    if os.path.isdir(jobs_dir):
        for name in sorted(os.listdir(jobs_dir)):
            if not name.endswith(".json") or name.startswith("_"):
                continue
            row = _read_json(os.path.join(jobs_dir, name), None)
            if isinstance(row, dict) and row.get("job_id"):
                jobs.append(row)
    captures = []
    cap_dir = os.path.join(root, "artifacts", "grok-captures")
    if os.path.isdir(cap_dir):
        for name in sorted(os.listdir(cap_dir)):
            if name.endswith(".json"):
                row = _read_json(os.path.join(cap_dir, name), None)
                if isinstance(row, dict):
                    captures.append(row)
    events = _read_json(os.path.join(root, "protocol", "fixtures", "live_events.json"), [])
    jsonl_path = os.path.join(root, "protocol", "events.jsonl")
    jsonl_events = []
    if os.path.isfile(jsonl_path):
        try:
            with open(jsonl_path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        jsonl_events.append({"parse_state": "MALFORMED", "raw": line[:200]})
                        continue
                    jsonl_events.append(row)
        except OSError:
            pass
    incoming = []
    if isinstance(events, list):
        incoming.extend(events)
    incoming.extend(jsonl_events)
    return {
        "presence": _read_json(os.path.join(root, "presence.json"), []),
        "lastseen": _read_json(os.path.join(root, "lastseen.json"), []),
        "pulse": _read_json(os.path.join(root, "pulse.json"), {}),
        "recent": _read_json(os.path.join(root, "recent.json"), []),
        "claims": _read_json(os.path.join(root, "claims.json"), {}),
        "recovery": _read_json(os.path.join(root, "revenue", "payment_ready", "recovery.json"), {}),
        "jobs": jobs,
        "grok_captures": captures,
        "protocol_events": incoming,
    }


def snapshot(root: str | None = None, *, now: str | None = None, events: list | None = None) -> dict[str, Any]:
    root = root or ROOT
    legacy = load_legacy(root)
    pulse = legacy.get("pulse") if isinstance(legacy.get("pulse"), dict) else {}
    incoming = list(events or [])
    incoming.extend(legacy.get("protocol_events") or [])
    return project(
        incoming,
        now=now or _now(),
        legacy=legacy,
        head_sha=str(pulse.get("head") or ""),
    )


def write_snapshot(root: str | None = None, *, now: str | None = None) -> dict[str, Any]:
    root = root or ROOT
    snap = snapshot(root, now=now)
    path = os.path.join(root, SNAPSHOT_REL)
    payload = json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return snap


def read_observatory(root: str | None = None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments if isinstance(arguments, dict) else {}
    root = root or ROOT
    path = os.path.join(root, SNAPSHOT_REL)
    if os.path.isfile(path):
        snap = _read_json(path, None)
        if not isinstance(snap, dict):
            snap = snapshot(root)
    else:
        snap = snapshot(root)
    view = str(arguments.get("view") or "snapshot").strip().lower()
    views = {
        "snapshot": snap,
        "census": {"presence": snap.get("presence"), "sessions": snap.get("sessions"), "cockpit": snap.get("cockpit")},
        "work": {"work_map": snap.get("work_map")},
        "collisions": {"collisions": snap.get("collisions")},
        "attention": {"attention": snap.get("attention")},
        "timeline": {"timeline": snap.get("timeline")},
        "briefing": {"briefing": snap.get("briefing")},
        "economy": {"economy": snap.get("economy")},
        "routes": {"routes": snap.get("routes")},
    }
    body = views.get(view, snap)
    body = dict(body)
    page_fields = {
        "census": (("sessions", snap.get("sessions") or []), ("presence", snap.get("presence") or [])),
        "work": (("work_map", snap.get("work_map") or []),),
        "collisions": (("collisions", snap.get("collisions") or []),),
        "attention": (("attention", snap.get("attention") or []),),
        "timeline": (("timeline", snap.get("timeline") or []),),
        "routes": (("routes", snap.get("routes") or []),),
        "snapshot": (("sessions", snap.get("sessions") or []), ("timeline", snap.get("timeline") or [])),
    }
    pagination = []
    for field, items in page_fields.get(view if view in views else "snapshot", ()):
        sliced, meta = _paginate(items, arguments, field=field)
        body[field] = sliced
        pagination.append(meta)
    body["schema"] = snap.get("schema")
    body["protocol"] = snap.get("protocol")
    body["state"] = "BAKE"
    body["view"] = view if view in views else "snapshot"
    body["open_door"] = snap.get("open_door")
    body["pagination"] = pagination
    body["provenance"] = {
        "source": SNAPSHOT_REL if os.path.isfile(path) else "host.observatory.snapshot",
        "grade": "OBSERVED",
        "digest": snap.get("digest"),
    }
    return body


def observe_work(root: str | None = None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments if isinstance(arguments, dict) else {}
    snap = snapshot(root)
    return {
        "schema": snap.get("schema"),
        "protocol": snap.get("protocol"),
        "state": "BAKE",
        "cockpit": snap.get("cockpit"),
        "sessions": snap.get("sessions"),
        "presence": snap.get("presence"),
        "work_map": snap.get("work_map"),
        "collisions": snap.get("collisions"),
        "attention": snap.get("attention"),
        "head": snap.get("head"),
        "filter": arguments.get("filter") or {},
    }


def project_live_work(root: str | None = None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments if isinstance(arguments, dict) else {}
    extra = arguments.get("events") if isinstance(arguments.get("events"), list) else []
    return snapshot(root, events=extra)


def continue_from(root: str | None = None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments if isinstance(arguments, dict) else {}
    root = root or ROOT
    snap = snapshot(root)
    result = continue_from_observation(snap, session_id=str(arguments.get("session_id") or ""))

    # SESSION_MEMORY is an explicit, per-session opt-in.  The continuation
    # surface carries only a delta, except for one bounded re-insertion after a
    # caller-reported compaction epoch change.  No binding is the ordinary
    # open-door case and never blocks continuation or posting.
    import memory_board
    memory = memory_board.session_memory_packet(
        root,
        str(arguments.get("session_id") or ""),
        after_entry_id=str(arguments.get("memory_cursor") or ""),
        compaction_epoch=str(arguments.get("compaction_epoch") or ""),
        acknowledged_compaction_epoch=str(
            arguments.get("acknowledged_compaction_epoch") or ""
        ),
    )
    result["session_memory"] = memory
    result["resume_context"] = [memory["context"]] if memory.get("should_insert") else []
    return result


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--write" in argv:
        snap = write_snapshot()
        sys.stdout.write("wrote %s digest=%s\n" % (SNAPSHOT_REL, snap.get("digest", "")[:16]))
        return 0
    snap = snapshot()
    sys.stdout.write(json.dumps(snap.get("cockpit"), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
