#!/usr/bin/env python3
"""Deterministic TITAN V4 claim-liveness and orphan-recovery auditor.

Consumes normalized JSONL exported from coordination surfaces. This module has
no Slack/GitHub credentials and performs no writes. Its output is routing
evidence only: STALE_CLAIM is never permission to overwrite peer work.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

SCHEMA = "titan-v4-claim-liveness/v1"
DEFAULT_CANONICAL_ROOT = (
    "main:revenue/kaggriculture/cloud-execution-lab/candidates/v4"
)
CLAIM = "CLAIM"
HEARTBEAT = "HEARTBEAT"
TERMINAL = {"COMPLETE", "RELEASED", "BLOCKED", "REJECTED", "SUPERSEDED"}
VALID_EVENTS = {CLAIM, HEARTBEAT, *TERMINAL}


class AuditError(ValueError):
    pass


def _timestamp(value: Any) -> float:
    if isinstance(value, bool):
        raise AuditError("timestamp must not be boolean")
    if isinstance(value, (int, float)):
        out = float(value)
        if not math.isfinite(out) or out < 0:
            raise AuditError("timestamp must be a finite nonnegative number")
        return out
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise AuditError("timestamp string is empty")
        try:
            numeric = float(text)
        except ValueError:
            numeric = None
        if numeric is not None:
            if not math.isfinite(numeric) or numeric < 0:
                raise AuditError("timestamp must be a finite nonnegative number")
            return numeric
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError as exc:
            raise AuditError(f"invalid timestamp {value!r}") from exc
        if parsed.tzinfo is None:
            raise AuditError("ISO timestamp must include timezone")
        return parsed.timestamp()
    raise AuditError("timestamp must be numeric or timezone-aware ISO-8601")


def _strict_bool(value: Any, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if type(value) is not bool:
        raise AuditError(f"{field} must be boolean")
    return value


@dataclass(frozen=True)
class Event:
    index: int
    ts: float
    lane: str
    session: str
    event: str
    event_id: str | None
    canonical_root: str | None
    writes_repo: bool
    requires_artifact: bool
    artifact: str | None
    channel: str | None
    thread_ts: str | None

    @classmethod
    def parse(cls, raw: Any, index: int) -> "Event":
        if not isinstance(raw, dict):
            raise AuditError(f"event[{index}] must be an object")
        lane = raw.get("lane")
        session = raw.get("session")
        event = raw.get("event")
        if not isinstance(lane, str) or not lane.strip():
            raise AuditError(f"event[{index}].lane must be a nonempty string")
        if not isinstance(session, str) or not session.strip():
            raise AuditError(f"event[{index}].session must be a nonempty string")
        if not isinstance(event, str):
            raise AuditError(f"event[{index}].event must be a string")
        event = event.strip().upper()
        if event not in VALID_EVENTS:
            raise AuditError(f"event[{index}].event unsupported: {event!r}")

        def opt_str(name: str) -> str | None:
            value = raw.get(name)
            if value is None:
                return None
            if not isinstance(value, str) or not value.strip():
                raise AuditError(f"event[{index}].{name} must be a nonempty string")
            return value.strip()

        return cls(
            index=index,
            ts=_timestamp(raw.get("ts")),
            lane=lane.strip(),
            session=session.strip(),
            event=event,
            event_id=opt_str("event_id"),
            canonical_root=opt_str("canonical_root"),
            writes_repo=_strict_bool(raw.get("writes_repo"), "writes_repo"),
            requires_artifact=_strict_bool(
                raw.get("requires_artifact"), "requires_artifact"
            ),
            artifact=opt_str("artifact"),
            channel=opt_str("channel"),
            thread_ts=opt_str("thread_ts"),
        )


def load_jsonl(lines: Iterable[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line_no, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AuditError(f"line {line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise AuditError(f"line {line_no}: JSON value must be an object")
        out.append(value)
    return out


def audit_events(
    raw_events: Iterable[dict[str, Any]],
    *,
    as_of: Any,
    ttl_seconds: int = 15 * 60,
    canonical_root: str = DEFAULT_CANONICAL_ROOT,
) -> dict[str, Any]:
    if type(ttl_seconds) is not int or ttl_seconds <= 0:
        raise AuditError("ttl_seconds must be a positive integer")
    if not isinstance(canonical_root, str) or not canonical_root.strip():
        raise AuditError("canonical_root must be a nonempty string")
    now = _timestamp(as_of)
    canonical_root = canonical_root.strip()

    events = [Event.parse(raw, i) for i, raw in enumerate(raw_events)]
    anomalies: list[dict[str, Any]] = []
    seen_ids: dict[str, Event] = {}

    for ev in events:
        if ev.ts > now:
            anomalies.append(
                {"kind": "future_event", "lane": ev.lane, "session": ev.session,
                 "event_id": ev.event_id, "ts": ev.ts}
            )
        if ev.event_id:
            old = seen_ids.get(ev.event_id)
            if old:
                anomalies.append(
                    {"kind": "duplicate_event_id", "event_id": ev.event_id,
                     "first_index": old.index, "duplicate_index": ev.index}
                )
            else:
                seen_ids[ev.event_id] = ev
        if ev.canonical_root and ev.canonical_root != canonical_root:
            anomalies.append(
                {"kind": "noncanonical_root", "lane": ev.lane,
                 "session": ev.session, "observed": ev.canonical_root,
                 "expected": canonical_root, "event_id": ev.event_id}
            )
        if ev.writes_repo and ev.canonical_root is None:
            anomalies.append(
                {"kind": "repo_write_without_root", "lane": ev.lane,
                 "session": ev.session, "event_id": ev.event_id}
            )

    grouped: dict[str, list[Event]] = defaultdict(list)
    for ev in events:
        grouped[ev.lane].append(ev)

    lane_rows: list[dict[str, Any]] = []
    for lane in sorted(grouped):
        lane_events = sorted(grouped[lane], key=lambda e: (e.ts, e.index))
        owners: dict[str, dict[str, Any]] = {}
        claimed_once: set[str] = set()

        for ev in lane_events:
            state = owners.get(ev.session)
            if ev.event == CLAIM:
                claimed_once.add(ev.session)
                owners[ev.session] = {
                    "state": "ACTIVE",
                    "last_ts": ev.ts,
                    "last_event": CLAIM,
                    "requires_artifact": ev.requires_artifact,
                    "artifact": ev.artifact,
                    "last_event_id": ev.event_id,
                }
            elif ev.event == HEARTBEAT:
                if state is None or state["state"] != "ACTIVE":
                    anomalies.append(
                        {"kind": "heartbeat_without_active_claim", "lane": lane,
                         "session": ev.session, "event_id": ev.event_id}
                    )
                    continue
                state["last_ts"] = ev.ts
                state["last_event"] = HEARTBEAT
                state["last_event_id"] = ev.event_id
                if ev.artifact:
                    state["artifact"] = ev.artifact
            else:
                if state is None or ev.session not in claimed_once:
                    anomalies.append(
                        {"kind": "terminal_without_claim", "lane": lane,
                         "session": ev.session, "terminal": ev.event,
                         "event_id": ev.event_id}
                    )
                    owners[ev.session] = {
                        "state": ev.event,
                        "last_ts": ev.ts,
                        "last_event": ev.event,
                        "requires_artifact": ev.requires_artifact,
                        "artifact": ev.artifact,
                        "last_event_id": ev.event_id,
                    }
                    continue
                required = bool(state.get("requires_artifact")) or ev.requires_artifact
                artifact = ev.artifact or state.get("artifact")
                if ev.event == "COMPLETE" and required and not artifact:
                    anomalies.append(
                        {"kind": "completion_without_required_artifact",
                         "lane": lane, "session": ev.session,
                         "event_id": ev.event_id}
                    )
                state["state"] = ev.event
                state["last_ts"] = ev.ts
                state["last_event"] = ev.event
                state["requires_artifact"] = required
                state["artifact"] = artifact
                state["last_event_id"] = ev.event_id

        fresh: list[str] = []
        stale: list[str] = []
        terminal: dict[str, str] = {}
        owner_rows: list[dict[str, Any]] = []
        for session in sorted(owners):
            state = owners[session]
            age = max(0.0, now - float(state["last_ts"]))
            if state["state"] == "ACTIVE":
                (stale if age > ttl_seconds else fresh).append(session)
            else:
                terminal[session] = str(state["state"])
            owner_rows.append(
                {
                    "session": session,
                    "state": state["state"],
                    "age_seconds": round(age, 6),
                    "last_event": state["last_event"],
                    "last_ts": state["last_ts"],
                    "artifact": state.get("artifact"),
                }
            )

        if len(fresh) > 1:
            status = "COLLISION"
        elif fresh and stale:
            status = "ACTIVE_WITH_STALE_OWNER"
        elif fresh:
            status = "ACTIVE"
        elif stale:
            status = "STALE_CLAIM"
        else:
            status = "CLOSED"

        lane_rows.append(
            {
                "lane": lane,
                "status": status,
                "fresh_active_owners": fresh,
                "stale_active_owners": stale,
                "recovery_candidates": stale if not fresh else [],
                "terminal_owners": terminal,
                "owners": owner_rows,
            }
        )

    summary = {
        "lanes": len(lane_rows),
        "active": sum(r["status"] == "ACTIVE" for r in lane_rows),
        "active_with_stale_owner": sum(
            r["status"] == "ACTIVE_WITH_STALE_OWNER" for r in lane_rows
        ),
        "collisions": sum(r["status"] == "COLLISION" for r in lane_rows),
        "stale_claims": sum(r["status"] == "STALE_CLAIM" for r in lane_rows),
        "closed": sum(r["status"] == "CLOSED" for r in lane_rows),
        "anomalies": len(anomalies),
    }
    anomalies.sort(
        key=lambda x: (
            x.get("kind", ""),
            x.get("lane", ""),
            x.get("session", ""),
            x.get("event_id") or "",
            x.get("duplicate_index", -1),
        )
    )
    return {
        "schema": SCHEMA,
        "canonical_root": canonical_root,
        "as_of": now,
        "ttl_seconds": ttl_seconds,
        "policy": {
            "stale_is_overwrite_authority": False,
            "fresh_owner_blocks_recovery": True,
            "noncanonical_root_is_anomaly": True,
        },
        "summary": summary,
        "lanes": lane_rows,
        "anomalies": anomalies,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", nargs="?", default="-", help="JSONL file or '-' for stdin")
    p.add_argument("--as-of", required=True, help="Unix seconds or timezone-aware ISO-8601")
    p.add_argument("--ttl-seconds", type=int, default=15 * 60)
    p.add_argument("--canonical-root", default=DEFAULT_CANONICAL_ROOT)
    p.add_argument("--output", default="-", help="JSON output path or '-' for stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.input == "-":
            raws = load_jsonl(sys.stdin)
        else:
            with open(args.input, "r", encoding="utf-8") as fh:
                raws = load_jsonl(fh)
        report = audit_events(
            raws,
            as_of=args.as_of,
            ttl_seconds=args.ttl_seconds,
            canonical_root=args.canonical_root,
        )
    except (AuditError, OSError) as exc:
        print(f"claim_liveness: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output == "-":
        sys.stdout.write(text)
    else:
        try:
            with open(args.output, "x", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            print(f"claim_liveness: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
