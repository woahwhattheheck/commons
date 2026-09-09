#!/usr/bin/env python3
"""Read-only correlation of journaled Slack send receipts.

This module does not call Slack and does not decide whether messages are
duplicates. It exposes preserved tool-journal metadata so an operator can map
an observed Slack message timestamp back to the journal operation that
returned it.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "commons.slack_operation_audit.v1"
_SLACK_TS = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")


class AuditError(RuntimeError):
    """The journal cannot be audited without guessing."""


def _connect_read_only(path: Path) -> sqlite3.Connection:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise AuditError("tool journal does not exist")
    uri = resolved.as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    return db


def _validate_schema(db: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(tool_calls)").fetchall()
    }
    required = {
        "request_id",
        "call_id",
        "tool_name",
        "state",
        "result_json",
        "updated_at",
    }
    if not required.issubset(columns):
        raise AuditError("tool_calls journal schema is unavailable or incompatible")


def _slack_result(result_json: str | None) -> tuple[str | None, str | None, bool | None, str | None]:
    """Return (channel, ts, uncertain, error) without retaining body text."""
    if not result_json:
        return None, None, None, None
    try:
        value = json.loads(result_json)
    except (TypeError, json.JSONDecodeError):
        return None, None, None, "invalid_result_json"
    if not isinstance(value, dict):
        return None, None, None, "unexpected_result_shape"

    uncertain = value.get("uncertain") if isinstance(value.get("uncertain"), bool) else None
    error = value.get("error") if isinstance(value.get("error"), str) else None
    result = value.get("result")
    if isinstance(result, dict):
        payload = result
    else:
        payload = value
    if error is None and isinstance(payload.get("error"), str):
        error = payload["error"]

    channel = payload.get("channel") if isinstance(payload.get("channel"), str) else None
    ts = payload.get("ts") if isinstance(payload.get("ts"), str) else None
    if ts is not None and not _SLACK_TS.fullmatch(ts):
        ts = None
    return channel, ts, uncertain, error


def slack_post_receipts(path: str | Path) -> list[dict[str, Any]]:
    """Return journal metadata for every preserved slack_post_message operation."""
    db = _connect_read_only(Path(path))
    try:
        _validate_schema(db)
        rows = db.execute(
            """
            SELECT request_id, call_id, tool_name, state, result_json, updated_at
            FROM tool_calls
            WHERE tool_name = 'slack_post_message'
            ORDER BY updated_at, request_id, call_id
            """
        ).fetchall()
    finally:
        db.close()

    receipts: list[dict[str, Any]] = []
    for row in rows:
        channel, slack_ts, uncertain, error = _slack_result(row["result_json"])
        request_id = row["request_id"]
        carrier_request_id = None
        if isinstance(request_id, str) and request_id.startswith("equipment-return:"):
            carrier_request_id = request_id.removeprefix("equipment-return:")
        receipts.append(
            {
                "journal_request_id": request_id,
                "journal_call_id": row["call_id"],
                "state": row["state"],
                "journal_updated_at": row["updated_at"],
                "channel_id": channel,
                "returned_slack_ts": slack_ts,
                "uncertain": uncertain,
                "error": error,
                "carrier_request_id": carrier_request_id,
            }
        )
    return receipts


def _normalize_observed(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not _SLACK_TS.fullmatch(value):
            raise AuditError("observed Slack timestamps must be numeric strings")
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def correlate(path: str | Path, observed_slack_ts: Iterable[str]) -> dict[str, Any]:
    """Correlate exact visible Slack timestamps with preserved send receipts.

    Exact timestamp equality is the only matching rule. Message text is neither
    accepted nor inspected.
    """
    observed = _normalize_observed(observed_slack_ts)
    receipts = slack_post_receipts(path)
    by_ts: dict[str, list[dict[str, Any]]] = {}
    for receipt in receipts:
        ts = receipt["returned_slack_ts"]
        if ts is not None:
            by_ts.setdefault(ts, []).append(receipt)

    matches = [
        {"slack_ts": ts, "receipts": by_ts.get(ts, [])}
        for ts in observed
    ]
    return {
        "schema": SCHEMA,
        "read_only": True,
        "matching_rule": "exact_returned_slack_timestamp",
        "journal_key_semantics": "one_execution_row_per_request_id_and_call_id",
        "message_body_inspected": False,
        "journal_receipt_count": len(receipts),
        "observations": matches,
        "unmatched_slack_ts": [
            item["slack_ts"] for item in matches if not item["receipts"]
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Correlate observed Slack timestamps with read-only tool-journal receipts."
    )
    parser.add_argument("--db", required=True, help="Path to commons_peer_tool_calls.sqlite3")
    parser.add_argument(
        "--slack-ts",
        action="append",
        default=[],
        help="Observed Slack message timestamp; repeat for a cluster.",
    )
    parser.add_argument(
        "--all-receipts",
        action="store_true",
        help="Emit all Slack send receipt metadata instead of timestamp correlation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.all_receipts:
            output: Any = {
                "schema": SCHEMA,
                "read_only": True,
                "message_body_inspected": False,
                "receipts": slack_post_receipts(args.db),
            }
        else:
            if not args.slack_ts:
                raise AuditError("supply at least one --slack-ts or use --all-receipts")
            output = correlate(args.db, args.slack_ts)
    except AuditError as exc:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
