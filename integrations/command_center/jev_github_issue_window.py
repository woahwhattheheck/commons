"""Bounded GitHub issue-update window + explicit gap-minute coverage.

This is a pure coverage adapter. It does not invent a second Jev client,
collector root, or credential road. Callers supply already-read GitHub issue
update rows (number + updated_at). The adapter:

- records an explicit missing minute as incomplete LOWER_BOUND coverage
- pages a later issue-update window without treating a cap as a census
- emits a connector-projection packet the landed ledger adapter accepts
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from integrations.command_center.jev_connector_projection import project

SCHEMA = "commons.jev_github_issue_window/v1"
PROJECTION_SCHEMA = "commons.jev_connector_projection/v1"
UTC = timezone.utc


class WindowError(ValueError):
    """Malformed issue-update window input."""


def _instant(value: Any, where: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise WindowError(f"{where}: timestamp must end in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WindowError(f"{where}: invalid timestamp") from exc
    if parsed.tzinfo != UTC:
        raise WindowError(f"{where}: not UTC")
    return parsed


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _token(value: Any, where: str) -> str:
    if type(value) is not str or not value or len(value) > 191:
        raise WindowError(f"{where}: invalid token")
    return value


def compile_window(packet: dict[str, Any]) -> dict[str, Any]:
    """Compile provider issue-update rows into a projection packet + coverage receipt."""
    if type(packet) is not dict:
        raise WindowError("packet must be an object")
    if packet.get("schema") != SCHEMA:
        raise WindowError("unsupported schema")
    owner = _token(packet.get("owner"), "owner")
    repo = _token(packet.get("repo"), "repo")
    snapshot_id = _token(packet.get("snapshot_id"), "snapshot_id")
    observed_at = _instant(packet.get("observed_at"), "observed_at")
    gap_start = _instant(packet.get("gap_start"), "gap_start")
    gap_end = _instant(packet.get("gap_end"), "gap_end")
    window_start = _instant(packet.get("window_start"), "window_start")
    window_end = _instant(packet.get("window_end"), "window_end")
    if not (gap_start < gap_end <= window_start < window_end <= observed_at):
        raise WindowError("gap and update windows must be ordered and not after observation")
    page = packet.get("page")
    page_size = packet.get("page_size")
    has_more = packet.get("has_more")
    if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 100:
        raise WindowError("page/page_size out of range")
    if type(has_more) is not bool:
        raise WindowError("has_more must be boolean")
    rows = packet.get("issues")
    if type(rows) is not list:
        raise WindowError("issues must be a list")

    records = []
    seen = set()
    for raw in rows:
        if type(raw) is not dict:
            raise WindowError("issue row must be an object")
        number = raw.get("number")
        if type(number) is not int or number < 1:
            raise WindowError("issue number invalid")
        updated = _instant(raw.get("updated_at"), "issue.updated_at")
        if not (window_start <= updated <= window_end):
            raise WindowError(f"issue #{number} outside declared update window")
        if number in seen:
            continue
        seen.add(number)
        records.append({
            "provider_event_id": str(number),
            "provider_event_time": _utc(updated),
            "observed_at": _utc(observed_at),
            "resource_scope": f"{owner}/{repo}",
            "event_type": "ISSUE",
            "actor_id": None,
            "work_id": f"github-issue-{number}",
            "operation_id": f"jev-16537-issue-window-{number}",
            "source_url": f"https://github.com/{owner}/{repo}/issues/{number}",
        })

    source_url = f"https://github.com/{owner}/{repo}/issues?q=updated%3A%3E%3D{_utc(window_start)}"
    projection = {
        "schema": PROJECTION_SCHEMA,
        "snapshot_id": snapshot_id,
        "max_source_age_seconds": 3600,
        "sources": [
            {
                "source_id": "github-issue-update-window",
                "connector": "github-issues-list",
                "provider": "github",
                "scope": [f"{owner}/{repo}"],
                "cursor": f"page-{page}",
                "high_water_mark": _utc(window_end),
                "observed_at": _utc(observed_at),
                "last_successful_read": _utc(observed_at),
                "status": "PARTIAL" if has_more else "OK",
                "cooldown_until": None,
                "coverage": {
                    "window_start": _utc(window_start),
                    "window_end": _utc(window_end),
                    "complete": not has_more,
                    "has_more": has_more,
                    "pages_read": page,
                    "items_read": len(records),
                },
                "source_url": source_url,
                "records": records,
            },
            {
                "source_id": "github-gap-minute-1924",
                "connector": "github-issues-list",
                "provider": "github",
                "scope": [f"{owner}/{repo}"],
                "cursor": None,
                "high_water_mark": _utc(gap_start),
                "observed_at": _utc(observed_at),
                "last_successful_read": None,
                "status": "PARTIAL",
                "cooldown_until": None,
                "coverage": {
                    "window_start": _utc(gap_start),
                    "window_end": _utc(gap_end),
                    "complete": False,
                    "has_more": True,
                    "pages_read": 0,
                    "items_read": 0,
                },
                "source_url": f"https://github.com/{owner}/{repo}/issues",
                "records": [],
            },
        ],
    }
    ledger = project(projection)
    return {
        "schema": SCHEMA,
        "snapshot_id": snapshot_id,
        "owner": owner,
        "repo": repo,
        "processed_issue_count": len(records),
        "processed_issue_numbers": sorted(seen),
        "update_window": {"start": _utc(window_start), "end": _utc(window_end), "complete": not has_more, "has_more": has_more, "page": page, "page_size": page_size},
        "gap_minute": {"start": _utc(gap_start), "end": _utc(gap_end), "complete": False, "items_read": 0, "status": "LOWER_BOUND"},
        "ledger_schema": ledger["schema"],
        "ledger_event_count": len(ledger["events"]),
        "ledger_source_ids": [source["source_id"] for source in ledger["sources"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a GitHub issue-update window packet.")
    parser.add_argument("input", nargs="?", help="JSON packet path; stdin if omitted")
    parser.add_argument("-o", "--output", help="Write JSON receipt here")
    args = parser.parse_args(argv)
    raw = sys.stdin.read() if args.input in (None, "-") else open(args.input, encoding="utf-8").read()
    packet = json.loads(raw)
    receipt = compile_window(packet)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
