"""Parse, accept, and identify Commons Protocol v0.1 events.

Malformed or partial events stay visible. They are never dropped, never
used to invent a session, and never become an access check.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from protocol.schema import (
    ACTOR_RE,
    CLASSIFICATIONS,
    EVENT_KINDS,
    GIT_SHA_RE,
    ID_RE,
    PROTOCOL_ID,
    PROTOCOL_VERSION,
    SHA256_RE,
    TS_RE,
    UNKNOWN,
)

_ID = re.compile(ID_RE)
_ACTOR = re.compile(ACTOR_RE)
_TS = re.compile(TS_RE)
_SHA = re.compile(SHA256_RE)
_GIT = re.compile(GIT_SHA_RE)


def _text(value: Any, *, maximum: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    text = str(value).strip()
    if len(text) > maximum:
        return text[:maximum]
    return text


def _opt(value: Any, *, maximum: int = 4000) -> str:
    text = _text(value, maximum=maximum)
    return text or UNKNOWN


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    seen = set()
    for item in value:
        text = _text(item, maximum=2000)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_id_for(fields: dict[str, Any]) -> str:
    """Stable event id: sha256 of the identity slice, 32 hex chars.

    Caller-supplied ids that already match Commons ID_RE are preserved.
    """
    supplied = _text(fields.get("event_id"), maximum=80)
    if _ID.fullmatch(supplied):
        return supplied
    identity = {
        "protocol": PROTOCOL_ID,
        "kind": _opt(fields.get("kind"), maximum=32),
        "task_id": _opt(fields.get("task_id"), maximum=80),
        "run_id": _opt(fields.get("run_id"), maximum=80),
        "session_id": _opt(fields.get("session_id"), maximum=80),
        "ts": _opt(fields.get("ts"), maximum=64),
        "dedupe_key": _opt(fields.get("dedupe_key") or fields.get("run_key"), maximum=200),
        "origin": {
            "thread_id": _opt(_obj(fields.get("origin")).get("thread_id"), maximum=80),
            "post_id": _opt(_obj(fields.get("origin")).get("post_id"), maximum=80),
            "message_id": _opt(_obj(fields.get("origin")).get("message_id"), maximum=80),
        },
    }
    digest = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:32]
    return digest


def classify_runtime(value: Any, harness: str = "", tools: list[str] | None = None) -> str:
    supplied = _text(value, maximum=32).upper()
    if supplied in CLASSIFICATIONS:
        return supplied
    blob = " ".join([supplied, harness, " ".join(tools or [])]).lower()
    if any(token in blob for token in ("browser", "cdp", "grok.com", "playwright", "chromium")):
        return "BROWSER"
    if any(token in blob for token in ("slack", "discord", "ntfy", "watchdog", "automation", "cron")):
        return "AUTOMATION"
    if any(token in blob for token in ("cloud", "chatgpt", "gpt cloud", "gemini")):
        return "CLOUD"
    if any(token in blob for token in ("local", "desktop", "filesystem", "codex desktop")):
        return "LOCAL"
    return UNKNOWN


def parse_event(raw: Any) -> dict[str, Any]:
    """Accept anything. Return a normalized event. Never raise on shape."""
    if not isinstance(raw, dict):
        return {
            "protocol": PROTOCOL_ID,
            "protocol_version": PROTOCOL_VERSION,
            "kind": UNKNOWN,
            "event_id": event_id_for({"kind": UNKNOWN, "ts": "", "session_id": ""}),
            "parse_state": "MALFORMED",
            "session_id": UNKNOWN,
            "task_id": UNKNOWN,
            "run_id": UNKNOWN,
            "model": UNKNOWN,
            "harness": UNKNOWN,
            "classification": UNKNOWN,
            "ts": UNKNOWN,
            "fields_observed": [],
            "fields_inferred": ["parse_state"],
            "evidence": [{"source": "raw", "grade": "UNKNOWN", "detail": "event was not an object"}],
            "raw_type": type(raw).__name__,
        }
    kind = _text(raw.get("kind"), maximum=32).upper()
    if kind not in EVENT_KINDS:
        kind = UNKNOWN
    origin = _obj(raw.get("origin"))
    tools = _list(raw.get("tools") or raw.get("capabilities"))
    harness = _opt(raw.get("harness"), maximum=200)
    classification = classify_runtime(raw.get("classification") or raw.get("runtime"), harness, tools)
    artifacts = []
    for item in raw.get("artifacts") or []:
        row = _obj(item)
        art = {
            "path": _opt(row.get("path"), maximum=2000),
            "sha256": _text(row.get("sha256"), maximum=64).lower(),
            "size_bytes": row.get("size_bytes") if isinstance(row.get("size_bytes"), int) and row.get("size_bytes") >= 0 else None,
            "url": _text(row.get("url"), maximum=2000),
            "provider_private": row.get("provider_private") is True,
            "grade": _opt(row.get("grade"), maximum=40),
        }
        if art["sha256"] and not _SHA.fullmatch(art["sha256"]):
            art["sha256"] = ""
            art["grade"] = "UNKNOWN"
        artifacts.append(art)
    ts = _opt(raw.get("ts") or raw.get("timestamp"), maximum=64)
    if ts != UNKNOWN and not _TS.fullmatch(ts):
        ts = UNKNOWN
    event = {
        "protocol": PROTOCOL_ID,
        "protocol_version": _opt(raw.get("protocol_version") or raw.get("protocol"), maximum=32),
        "kind": kind,
        "event_id": "",
        "task_id": _opt(raw.get("task_id"), maximum=80),
        "run_id": _opt(raw.get("run_id") or raw.get("run_key"), maximum=80),
        "parent_ids": _list(raw.get("parent_ids") or raw.get("lineage")),
        "origin": {
            "thread_id": _opt(origin.get("thread_id") or origin.get("thread_ts"), maximum=80),
            "message_id": _opt(origin.get("message_id") or origin.get("ts"), maximum=80),
            "post_id": _opt(origin.get("post_id") or origin.get("id"), maximum=80),
        },
        "session_id": _opt(raw.get("session_id"), maximum=80),
        "model": _opt(raw.get("model"), maximum=200),
        "harness": harness,
        "classification": classification,
        "tools": tools,
        "objective": _opt(raw.get("objective") or raw.get("current_objective"), maximum=2000),
        "lease": {
            "lease_id": _opt(_obj(raw.get("lease")).get("lease_id"), maximum=80),
            "holder": _opt(_obj(raw.get("lease")).get("holder"), maximum=80),
            "until": _opt(_obj(raw.get("lease")).get("until") or raw.get("lease_until"), maximum=64),
            "descriptive_only": True,
        },
        "claimed_paths": _list(raw.get("claimed_paths") or raw.get("paths")),
        "semantic_area": _opt(raw.get("semantic_area"), maximum=200),
        "dedupe_key": _opt(raw.get("dedupe_key") or raw.get("run_key"), maximum=200),
        "checkpoint": _opt(raw.get("checkpoint") if not isinstance(raw.get("checkpoint"), dict) else canonical_json(raw.get("checkpoint")), maximum=4000),
        "blocker": {
            "type": _opt(_obj(raw.get("blocker")).get("type") or raw.get("blocker_type"), maximum=80),
            "detail": _opt(_obj(raw.get("blocker")).get("detail") or raw.get("blocker"), maximum=2000),
        },
        "provider": _obj(raw.get("provider") or raw.get("execution")),
        "cost": {
            "tokens": raw.get("tokens") if isinstance(raw.get("tokens"), int) else None,
            "debit": _opt(_obj(raw.get("cost")).get("debit") or raw.get("debit_evidence"), maximum=200),
            "visible": bool(_obj(raw.get("cost")).get("visible") or raw.get("token_evidence") or raw.get("debit_evidence")),
            "grade": "PROVIDER_REPORTED" if (raw.get("token_evidence") or raw.get("debit_evidence")) else UNKNOWN,
        },
        "artifacts": artifacts,
        "ts": ts,
        "terminal_disposition": _opt(raw.get("terminal_disposition") or raw.get("disposition"), maximum=80),
        "supersedes": _opt(raw.get("supersedes") or raw.get("superseded_event_id"), maximum=80),
        "attention_reason": _opt(raw.get("attention_reason"), maximum=2000),
        "grok_url": _text(raw.get("grok_url") or raw.get("conversation_url"), maximum=2000),
        "head_sha": _text(raw.get("head_sha") or raw.get("base_sha"), maximum=40).lower(),
        "parse_state": "OK" if kind != UNKNOWN else "PARTIAL",
        "fields_observed": sorted(str(key) for key in raw.keys()),
        "fields_inferred": [],
        "evidence": [],
    }
    if event["protocol_version"] in {UNKNOWN, PROTOCOL_ID}:
        event["protocol_version"] = PROTOCOL_VERSION
    if event["head_sha"] and not _GIT.fullmatch(event["head_sha"]):
        event["head_sha"] = ""
    if event["session_id"] != UNKNOWN and not _ID.fullmatch(event["session_id"]) and not _ACTOR.fullmatch(event["session_id"]):
        # Keep the label; do not mint a replacement identity.
        event["fields_inferred"].append("session_id_noncanonical")
    event["event_id"] = event_id_for({**event, "event_id": raw.get("event_id")})
    if kind == UNKNOWN:
        event["evidence"].append({"source": "event", "grade": "UNKNOWN", "detail": "kind missing or not in v0.1 set"})
    else:
        event["evidence"].append({"source": "event", "grade": "OBSERVED", "event_id": event["event_id"]})
    if not isinstance(raw.get("kind"), str) or ("ts" in raw and event["ts"] == UNKNOWN):
        event["parse_state"] = "MALFORMED" if event["parse_state"] == "OK" else event["parse_state"]
    return event


def parse_events(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if isinstance(rows, dict):
        if isinstance(rows.get("events"), list):
            rows = rows["events"]
        else:
            rows = [rows]
    if not isinstance(rows, list):
        return [parse_event(rows)]
    return [parse_event(row) for row in rows]
