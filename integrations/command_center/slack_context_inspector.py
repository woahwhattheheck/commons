"""Inspect captured Slack root context with the existing reader; never call Slack.

The input and output can contain private message text. Keep private captures out
of source control. Completeness describes this capture, not live claim ownership.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from .slack_threads import read_thread_context

SCHEMA = "commons.slack-context-capture.v1"
REPORT_SCHEMA = "commons.slack-context-inspection.v1"
MAX_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 64
ROOT = "1700000000.000001"
EARLIER = "1700000010.000002"
CHILD = "1700000020.000003"
CHANNEL = "CDEMO"
SCENARIOS = ("complete", "page_limit", "missing_page", "wrong_child", "unknown_root",
             "conflicting_root", "count_mismatch", "changed_message", "unused_page")


class CaptureError(ValueError):
    """A fixed, non-content-bearing input or output diagnostic."""


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            raise CaptureError("duplicate_json_key")
        value[key] = item
    return value


def _nonfinite(_: str) -> None:
    raise CaptureError("nonfinite_json_number")


def _check_values(value: Any) -> None:
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise CaptureError("capture_too_deep")
        if isinstance(item, str):
            if any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                raise CaptureError("invalid_unicode_scalar")
        elif isinstance(item, float) and not math.isfinite(item):
            raise CaptureError("nonfinite_json_number")
        elif isinstance(item, list):
            pending.extend((x, depth + 1) for x in item)
        elif isinstance(item, dict):
            pending.extend((x, depth + 1) for pair in item.items() for x in pair)


def decode_capture(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise CaptureError("capture_bytes_invalid_or_too_large")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, CaptureError):
            raise
        raise CaptureError("invalid_capture_json") from None
    _check_values(value)
    fields = {"schema", "classification", "captured_at", "channel_id", "selected_message",
              "page_size", "max_pages", "reads"}
    if not isinstance(value, dict) or set(value) != fields or value["schema"] != SCHEMA:
        raise CaptureError("capture_schema_mismatch")
    if value["classification"] not in ("SYNTHETIC_REHEARSAL", "PRIVATE_CAPTURE"):
        raise CaptureError("capture_classification_invalid")
    stamp = value["captured_at"]
    if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
        raise CaptureError("capture_time_invalid")
    try:
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise CaptureError("capture_time_invalid") from None
    for name, maximum in (("page_size", 100), ("max_pages", 10)):
        if type(value[name]) is not int or not 1 <= value[name] <= maximum:
            raise CaptureError("capture_limits_invalid")
    if not isinstance(value["selected_message"], dict):
        raise CaptureError("selected_message_invalid")
    reads = value["reads"]
    if not isinstance(reads, list) or len(reads) > 10:
        raise CaptureError("capture_reads_invalid")
    for read in reads:
        if (not isinstance(read, dict) or set(read) != {"method", "payload", "response"}
                or read["method"] != "conversations.replies"
                or not isinstance(read["payload"], dict) or not isinstance(read["response"], dict)):
            raise CaptureError("capture_read_shape_invalid")
    return value


class CapturedReader:
    """Match each real reader request to its exact captured response, in order."""

    def __init__(self, reads: list[dict[str, Any]]) -> None:
        self.reads = copy.deepcopy(reads)
        self.consumed = 0
        self.requests: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, Any]] = []

    def __call__(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = {"method": method, "payload": copy.deepcopy(payload)}
        self.requests.append(request)
        if self.consumed == len(self.reads):
            self.diagnostics.append({"code": "capture_response_missing", "index": self.consumed})
            raise CaptureError("capture_response_missing")
        captured = self.reads[self.consumed]
        # JSON comparison keeps true distinct from 1; Python dict equality does not.
        if json.dumps(request, sort_keys=True) != json.dumps(
                {"method": captured["method"], "payload": captured["payload"]}, sort_keys=True):
            self.diagnostics.append({"code": "capture_request_mismatch", "index": self.consumed})
            raise CaptureError("capture_request_mismatch")
        self.consumed += 1
        return copy.deepcopy(captured["response"])


def inspect_capture(raw: bytes) -> dict[str, Any]:
    capture = decode_capture(raw)
    provider = CapturedReader(capture["reads"])
    try:
        rows, coverage, complete = read_thread_context(provider, capture["channel_id"],
            copy.deepcopy(capture["selected_message"]), page_size=capture["page_size"],
            max_pages=capture["max_pages"])
    except (ValueError, TypeError, RuntimeError) as exc:
        # Deliberately do not echo malformed provider data or arbitrary exception text.
        raise CaptureError("reader_input_invalid") from exc
    unused = len(capture["reads"]) - provider.consumed
    inspected = bool(complete and not provider.diagnostics and not unused)
    root = coverage["root_resolution"]["thread_ts"]
    refresh = None
    continuation = None
    if root is not None:
        payload = {"channel": capture["channel_id"], "ts": root, "limit": capture["page_size"]}
        refresh = {"method": "conversations.replies", "payload": payload}
        if coverage.get("next_cursor"):
            continuation = {"method": "conversations.replies",
                            "payload": {**payload, "cursor": coverage["next_cursor"]}}
    return {
        "schema": REPORT_SCHEMA,
        "classification": capture["classification"],
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "capture_declared_at": capture["captured_at"],
        "live_freshness": "NOT_CHECKED",
        "selected_message": capture["selected_message"],
        "channel_id": capture["channel_id"],
        "coverage": coverage,
        "capture_inspection_complete": inspected,
        "reads_supplied": len(capture["reads"]),
        "reads_consumed": provider.consumed,
        "reads_unused": unused,
        "requested_reads": provider.requests,
        "capture_diagnostics": provider.diagnostics,
        "observed_messages": rows,
        "refresh_request": refresh,
        "continuation_request": continuation,
        "actions_performed": [],
        "claim_authority": False,
        "provider_write_authority": False,
        "limits": ["No live provider request was made; captured_at is supplied metadata.",
                   "Complete capture coverage is not freshness, vacancy or an atomic claim.",
                   "Continuation is an API cursor within this capture, not a fresh snapshot or connector cursor.",
                   "Private captures and reports can contain complete private message text."],
    }


def render_text(report: dict[str, Any]) -> str:
    coverage = report["coverage"]
    resolution = coverage["root_resolution"]
    lines = ["Slack captured-context inspection", "",
             f"Classification: {report['classification']}",
             f"Capture time (declared): {report['capture_declared_at']}",
             "Live freshness: NOT_CHECKED; no provider actions performed.",
             f"Selected message: {resolution['message_ts']}",
             f"Resolved root: {resolution['thread_ts']} ({resolution['state']})",
             f"Reader coverage complete: {coverage['complete']}",
             f"All supplied capture reads reconciled: {report['capture_inspection_complete']}",
             f"Reason: {coverage.get('reason')}",
             f"Pages read: {coverage['pages_read']}; unused captured reads: {report['reads_unused']}",
             "", "Observed messages (literal JSON strings; no inferred claimant):"]
    for row in report["observed_messages"]:
        lines.append(json.dumps(row, ensure_ascii=True, sort_keys=True))
    lines += ["", "Capture diagnostics: " + json.dumps(report["capture_diagnostics"], sort_keys=True),
              "Refresh request (NOT executed): " + json.dumps(report["refresh_request"], sort_keys=True),
              "Continuation (NOT executed): " + json.dumps(report["continuation_request"], sort_keys=True),
              "", "No result authorizes posting or proves a work slot is free."]
    return "\n".join(lines) + "\n"


def example_capture(scenario: str = "complete") -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise CaptureError("example_scenario_unknown")
    selected = {"ts": CHILD, "subtype": "thread_broadcast", "text": "FICTION: review requested",
                "permalink": "https://fixture.slack.com/archives/CDEMO/p" + CHILD.replace(".", "")
                    + "?thread_ts=" + ROOT + "&cid=CDEMO"}
    parent = {"ts": ROOT, "reply_count": 2, "latest_reply": CHILD, "text": "FICTION: original work order"}
    prior = {"ts": EARLIER, "thread_ts": ROOT, "text": "FICTION: Rowan already took source review"}
    child = {**selected, "thread_ts": ROOT}
    payload = {"channel": CHANNEL, "ts": ROOT, "limit": 2}
    reads = [
        {"method": "conversations.replies", "payload": payload,
         "response": {"ok": True, "messages": [parent, prior], "has_more": True,
                      "response_metadata": {"next_cursor": "fixture-page-2"}}},
        {"method": "conversations.replies", "payload": {**payload, "cursor": "fixture-page-2"},
         "response": {"ok": True, "messages": [child],
                      "response_metadata": {"next_cursor": ""}}}]
    result = {"schema": SCHEMA, "classification": "SYNTHETIC_REHEARSAL",
              "captured_at": "2026-01-01T00:00:00Z", "channel_id": CHANNEL,
              "selected_message": selected, "page_size": 2, "max_pages": 2, "reads": reads}
    if scenario == "page_limit":
        result["max_pages"] = 1
    elif scenario == "missing_page":
        del reads[1:]
    elif scenario == "wrong_child":
        reads[0]["payload"] = {**payload, "ts": CHILD}
        reads[0]["response"] = {"ok": True, "messages": [{"ts": CHILD, "reply_count": 0}]}
        del reads[1:]
    elif scenario == "unknown_root":
        del selected["permalink"]
        reads.clear()
    elif scenario == "conflicting_root":
        selected["thread_ts"] = EARLIER
        reads.clear()
    elif scenario == "count_mismatch":
        reads[1]["response"]["messages"] = []
    elif scenario == "changed_message":
        reads[1]["response"]["messages"] = [{**prior, "text": "FICTION: different newer wording"}, child]
    elif scenario == "unused_page":
        reads.append(copy.deepcopy(reads[-1]))
    return result


def _publish_new(path: Path, body: bytes) -> None:
    # Staging plus same-directory create-only link: no existing name is replaced.
    fd, name = tempfile.mkstemp(prefix=".slack-context-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(name, path)
    finally:
        os.unlink(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    example = sub.add_parser("example", help="Generate an editable fictional capture; no provider access.")
    example.add_argument("--scenario", choices=SCENARIOS, default="complete")
    example.add_argument("--output", type=Path)
    inspect = sub.add_parser("inspect", help="Inspect exact captured responses with the canonical reader.")
    inspect.add_argument("input", type=Path)
    inspect.add_argument("--format", choices=("json", "text"), default="text")
    inspect.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "example":
            result, code = example_capture(args.scenario), 0
            text = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        else:
            with args.input.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            result = inspect_capture(raw)
            code = 0 if result["capture_inspection_complete"] else 1
            text = (render_text(result) if args.format == "text" else
                    json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n")
        if args.output:
            _publish_new(args.output, text.encode("utf-8"))
        else:
            sys.stdout.write(text)
        return code
    except (CaptureError, OSError, UnicodeError) as exc:
        code = str(exc) if isinstance(exc, CaptureError) else "capture_io_error"
        print(json.dumps({"error": code, "completed": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
