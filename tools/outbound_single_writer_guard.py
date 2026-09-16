#!/usr/bin/env python3
"""Offline, deterministic single-writer preflight for external outreach.

This module does not contact Slack, Gmail, Muse, a buyer, or any provider. It
consumes provider-normalized evidence and answers one narrow question:
does the retained snapshot show exactly one Muse-selected seat for this exact
outbound intent, with no prior send receipt or conflicting selection?

A READY result is coordination evidence only. It never authorizes an external
send, payment, contract, submission, or revenue recognition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 4096
MAX_TEXT = 1024
MAX_SAFE_INT = (1 << 53) - 1

ASCII_RE = re.compile(r"^[\x20-\x7e]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SLACK_TS_RE = re.compile(r"^[0-9]{10}\.[0-9]{6}$")
PROVIDER_ID_RE = re.compile(r"^[A-Za-z0-9._:@/+<>=-]+$")

RESULTS = {
    "READY_SINGLE_WRITER",
    "HOLD_NO_REQUEST",
    "HOLD_REQUEST_CONFLICT",
    "HOLD_NO_MUSE_DECISION",
    "HOLD_MUSE_CONFLICT",
    "HOLD_DIFFERENT_SEAT_SELECTED",
    "HOLD_ROUTE_MISMATCH",
    "HOLD_ALREADY_SENT",
    "HOLD_AFTER_DNR",
    "HOLD_EVIDENCE_ORDERING",
    "HOLD_SOURCE_CONFLICT",
}

# Deliberately literal in compile_report as well. This public convenience value
# is not an authority-bearing dependency; mutating or rebinding it cannot alter
# compiled reports.
AUTHORITY_FALSE = {
    "externalSendAuthorized": False,
    "providerMutationAuthorized": False,
    "paymentAuthorized": False,
    "contractAuthorized": False,
    "submissionAuthorized": False,
    "revenueRecognized": False,
}


class GuardError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise GuardError(code)


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _fail("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _reject_float(_: str) -> Any:
    _fail("FLOAT_NOT_ALLOWED")


def _reject_constant(_: str) -> Any:
    _fail("NONFINITE_NUMBER")


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        _fail("JSON_TEXT_REQUIRED")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except GuardError:
        raise
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise GuardError("INVALID_JSON") from exc


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError, RecursionError) as exc:
        raise GuardError("CANONICAL_JSON_FAILED") from exc


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dict(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(code)
    return value


def _list(value: Any, code: str, limit: int = MAX_ITEMS) -> list[Any]:
    if not isinstance(value, list):
        _fail(code)
    if len(value) > limit:
        _fail("ARRAY_TOO_LARGE")
    return value


def _exact(obj: dict[str, Any], keys: set[str], code: str = "UNKNOWN_OR_MISSING_FIELD") -> None:
    if set(obj) != keys:
        _fail(code)


def _int(value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("INTEGER_REQUIRED")
    if value < minimum or value > MAX_SAFE_INT:
        _fail("UNSAFE_INTEGER")
    return value


def _text(value: Any, code: str, *, max_len: int = MAX_TEXT) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_len
        or not ASCII_RE.fullmatch(value)
    ):
        _fail(code)
    return value


def _utc(value: Any, code: str = "UTC_REQUIRED") -> str:
    text = _text(value, code, max_len=20)
    if not UTC_RE.fullmatch(text):
        _fail(code)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise GuardError(code) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        _fail(code)
    return text


def _slack_ts(value: Any) -> str:
    text = _text(value, "SLACK_TS_REQUIRED", max_len=24)
    if not SLACK_TS_RE.fullmatch(text):
        _fail("SLACK_TS_REQUIRED")
    return text


def _sha256(value: Any, code: str = "SHA256_REQUIRED") -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        _fail(code)
    return value


def _provider_id(value: Any, code: str) -> str:
    text = _text(value, code, max_len=256)
    if not PROVIDER_ID_RE.fullmatch(text):
        _fail(code)
    return text


def _route(value: Any) -> dict[str, str]:
    obj = _dict(value, "ROUTE_OBJECT_REQUIRED")
    _exact(obj, {"channel", "recipient", "routeKey"})
    channel = _text(obj["channel"], "CHANNEL_REQUIRED", max_len=32)
    if channel not in {"EMAIL", "SLACK_DM", "GITHUB_COMMENT", "FORM", "OTHER"}:
        _fail("CHANNEL_INVALID")
    return {
        "channel": channel,
        "recipient": _text(obj["recipient"], "RECIPIENT_REQUIRED", max_len=320),
        "routeKey": _provider_id(obj["routeKey"], "ROUTE_KEY_REQUIRED"),
    }


def _intent(value: Any) -> dict[str, Any]:
    obj = _dict(value, "INTENT_OBJECT_REQUIRED")
    _exact(
        obj,
        {
            "bodySha256",
            "createdUtc",
            "intentKey",
            "operationId",
            "opportunityKey",
            "route",
            "subjectSha256",
        },
    )
    return {
        "bodySha256": _sha256(obj["bodySha256"]),
        "createdUtc": _utc(obj["createdUtc"]),
        "intentKey": _provider_id(obj["intentKey"], "INTENT_KEY_REQUIRED"),
        "operationId": _provider_id(obj["operationId"], "OPERATION_ID_REQUIRED"),
        "opportunityKey": _provider_id(obj["opportunityKey"], "OPPORTUNITY_KEY_REQUIRED"),
        "route": _route(obj["route"]),
        "subjectSha256": _sha256(obj["subjectSha256"]),
    }


def _request(value: Any) -> dict[str, Any]:
    obj = _dict(value, "REQUEST_OBJECT_REQUIRED")
    _exact(
        obj,
        {
            "intentKey",
            "operationId",
            "opportunityKey",
            "requestedUtc",
            "requestMessageSha256",
            "requesterSeat",
            "routeKey",
            "slackMessageTs",
        },
    )
    return {
        "intentKey": _provider_id(obj["intentKey"], "INTENT_KEY_REQUIRED"),
        "operationId": _provider_id(obj["operationId"], "OPERATION_ID_REQUIRED"),
        "opportunityKey": _provider_id(obj["opportunityKey"], "OPPORTUNITY_KEY_REQUIRED"),
        "requestedUtc": _utc(obj["requestedUtc"]),
        "requestMessageSha256": _sha256(obj["requestMessageSha256"]),
        "requesterSeat": _provider_id(obj["requesterSeat"], "SEAT_REQUIRED"),
        "routeKey": _provider_id(obj["routeKey"], "ROUTE_KEY_REQUIRED"),
        "slackMessageTs": _slack_ts(obj["slackMessageTs"]),
    }


def _decision(value: Any) -> dict[str, Any]:
    obj = _dict(value, "DECISION_OBJECT_REQUIRED")
    _exact(
        obj,
        {
            "decision",
            "decidedUtc",
            "intentKey",
            "leaseId",
            "museMessageSha256",
            "museMessageTs",
            "operationId",
            "opportunityKey",
            "requestSlackMessageTs",
            "routeKey",
            "selectedSeat",
        },
    )
    decision = _text(obj["decision"], "DECISION_REQUIRED", max_len=16)
    if decision not in {"SELECTED", "HOLD", "YIELD", "REVOKED"}:
        _fail("DECISION_INVALID")
    selected = obj["selectedSeat"]
    if selected is None:
        if decision == "SELECTED":
            _fail("SELECTED_SEAT_REQUIRED")
    else:
        selected = _provider_id(selected, "SEAT_REQUIRED")
        if decision != "SELECTED":
            _fail("NONSELECT_DECISION_HAS_SEAT")
    return {
        "decision": decision,
        "decidedUtc": _utc(obj["decidedUtc"]),
        "intentKey": _provider_id(obj["intentKey"], "INTENT_KEY_REQUIRED"),
        "leaseId": _provider_id(obj["leaseId"], "LEASE_ID_REQUIRED"),
        "museMessageSha256": _sha256(obj["museMessageSha256"]),
        "museMessageTs": _slack_ts(obj["museMessageTs"]),
        "operationId": _provider_id(obj["operationId"], "OPERATION_ID_REQUIRED"),
        "opportunityKey": _provider_id(obj["opportunityKey"], "OPPORTUNITY_KEY_REQUIRED"),
        "requestSlackMessageTs": _slack_ts(obj["requestSlackMessageTs"]),
        "routeKey": _provider_id(obj["routeKey"], "ROUTE_KEY_REQUIRED"),
        "selectedSeat": selected,
    }


def _send(value: Any) -> dict[str, Any]:
    obj = _dict(value, "SEND_OBJECT_REQUIRED")
    _exact(
        obj,
        {
            "intentKey",
            "leaseId",
            "operationId",
            "opportunityKey",
            "providerMessageId",
            "routeKey",
            "senderSeat",
            "sentUtc",
        },
    )
    return {
        "intentKey": _provider_id(obj["intentKey"], "INTENT_KEY_REQUIRED"),
        "leaseId": _provider_id(obj["leaseId"], "LEASE_ID_REQUIRED"),
        "operationId": _provider_id(obj["operationId"], "OPERATION_ID_REQUIRED"),
        "opportunityKey": _provider_id(obj["opportunityKey"], "OPPORTUNITY_KEY_REQUIRED"),
        "providerMessageId": _provider_id(obj["providerMessageId"], "PROVIDER_MESSAGE_ID_REQUIRED"),
        "routeKey": _provider_id(obj["routeKey"], "ROUTE_KEY_REQUIRED"),
        "senderSeat": _provider_id(obj["senderSeat"], "SEAT_REQUIRED"),
        "sentUtc": _utc(obj["sentUtc"]),
    }


def _dnr(value: Any) -> dict[str, Any]:
    obj = _dict(value, "DNR_OBJECT_REQUIRED")
    _exact(obj, {"createdUtc", "opportunityKey", "providerRef", "reasonCode", "routeKey"})
    return {
        "createdUtc": _utc(obj["createdUtc"]),
        "opportunityKey": _provider_id(obj["opportunityKey"], "OPPORTUNITY_KEY_REQUIRED"),
        "providerRef": _provider_id(obj["providerRef"], "PROVIDER_REF_REQUIRED"),
        "reasonCode": _provider_id(obj["reasonCode"], "REASON_CODE_REQUIRED"),
        "routeKey": _provider_id(obj["routeKey"], "ROUTE_KEY_REQUIRED"),
    }


def normalize_snapshot(raw: Any) -> dict[str, Any]:
    obj = _dict(raw, "ROOT_OBJECT_REQUIRED")
    _exact(
        obj,
        {
            "asOfUtc",
            "decisions",
            "dnr",
            "intent",
            "requests",
            "schemaVersion",
            "sendReceipts",
            "sourceObservations",
        },
    )
    if _int(obj["schemaVersion"], minimum=1) != SCHEMA_VERSION:
        _fail("SCHEMA_VERSION_UNSUPPORTED")
    intent = _intent(obj["intent"])
    requests = [_request(v) for v in _list(obj["requests"], "REQUESTS_REQUIRED")]
    decisions = [_decision(v) for v in _list(obj["decisions"], "DECISIONS_REQUIRED")]
    sends = [_send(v) for v in _list(obj["sendReceipts"], "SEND_RECEIPTS_REQUIRED")]
    dnr = [_dnr(v) for v in _list(obj["dnr"], "DNR_REQUIRED")]
    observations = [_sha256(v, "SOURCE_OBSERVATION_SHA_REQUIRED") for v in _list(obj["sourceObservations"], "SOURCE_OBSERVATIONS_REQUIRED")]
    if not observations:
        _fail("SOURCE_OBSERVATIONS_EMPTY")
    if len(set(observations)) != len(observations):
        _fail("DUPLICATE_SOURCE_OBSERVATION")
    if len({r["slackMessageTs"] for r in requests}) != len(requests):
        _fail("DUPLICATE_REQUEST_TS")
    if len({d["museMessageTs"] for d in decisions}) != len(decisions):
        _fail("DUPLICATE_DECISION_TS")
    if len({d["leaseId"] for d in decisions}) != len(decisions):
        _fail("DUPLICATE_LEASE_ID")
    if len({s["providerMessageId"] for s in sends}) != len(sends):
        _fail("DUPLICATE_PROVIDER_MESSAGE_ID")
    if len({d["providerRef"] for d in dnr}) != len(dnr):
        _fail("DUPLICATE_DNR_PROVIDER_REF")
    return {
        "asOfUtc": _utc(obj["asOfUtc"]),
        "decisions": sorted(decisions, key=lambda d: (d["decidedUtc"], d["museMessageTs"])),
        "dnr": sorted(dnr, key=lambda d: (d["createdUtc"], d["providerRef"])),
        "intent": intent,
        "requests": sorted(requests, key=lambda r: (r["requestedUtc"], r["slackMessageTs"])),
        "schemaVersion": SCHEMA_VERSION,
        "sendReceipts": sorted(sends, key=lambda s: (s["sentUtc"], s["providerMessageId"])),
        "sourceObservations": sorted(observations),
    }


def _same_intent(row: dict[str, Any], intent: dict[str, Any]) -> bool:
    return (
        row["intentKey"] == intent["intentKey"]
        and row["operationId"] == intent["operationId"]
        and row["opportunityKey"] == intent["opportunityKey"]
        and row["routeKey"] == intent["route"]["routeKey"]
    )


def _evaluate(snapshot: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    intent = snapshot["intent"]
    as_of = snapshot["asOfUtc"]
    matching_requests = [r for r in snapshot["requests"] if _same_intent(r, intent)]
    foreign_requests = [
        r for r in snapshot["requests"]
        if r["intentKey"] == intent["intentKey"] and not _same_intent(r, intent)
    ]
    matching_decisions = [d for d in snapshot["decisions"] if _same_intent(d, intent)]
    matching_sends = [s for s in snapshot["sendReceipts"] if _same_intent(s, intent)]
    route_dnr = [
        d for d in snapshot["dnr"]
        if d["opportunityKey"] == intent["opportunityKey"]
        and d["routeKey"] == intent["route"]["routeKey"]
    ]

    if foreign_requests:
        return "HOLD_SOURCE_CONFLICT", ["INTENT_KEY_REBOUND_TO_DIFFERENT_SCOPE"], {}

    if any(r["requestedUtc"] > as_of for r in matching_requests):
        return "HOLD_EVIDENCE_ORDERING", ["REQUEST_AFTER_AS_OF"], {}
    if any(d["decidedUtc"] > as_of for d in matching_decisions):
        return "HOLD_EVIDENCE_ORDERING", ["DECISION_AFTER_AS_OF"], {}
    if any(s["sentUtc"] > as_of for s in matching_sends):
        return "HOLD_EVIDENCE_ORDERING", ["SEND_AFTER_AS_OF"], {}
    if any(d["createdUtc"] > as_of for d in route_dnr):
        return "HOLD_EVIDENCE_ORDERING", ["DNR_AFTER_AS_OF"], {}

    if route_dnr:
        latest = route_dnr[-1]
        return "HOLD_AFTER_DNR", [f"DNR:{latest['reasonCode']}"], {
            "dnrProviderRef": latest["providerRef"]
        }

    if matching_sends:
        latest = matching_sends[-1]
        return "HOLD_ALREADY_SENT", ["MATCHING_SEND_RECEIPT_EXISTS"], {
            "providerMessageId": latest["providerMessageId"],
            "senderSeat": latest["senderSeat"],
        }

    if not matching_requests:
        return "HOLD_NO_REQUEST", ["NO_MATCHING_MUSE_REQUEST"], {}

    seats = {r["requesterSeat"] for r in matching_requests}
    if len(seats) > 1:
        # Multiple contenders are expected pre-adjudication, but every request for
        # the exact intent must remain independently identifiable. The Muse
        # decision below chooses one. Do not treat contention itself as error.
        pass
    if len({r["requestMessageSha256"] for r in matching_requests}) != len(matching_requests):
        return "HOLD_REQUEST_CONFLICT", ["DUPLICATE_REQUEST_MESSAGE_HASH"], {}

    if not matching_decisions:
        return "HOLD_NO_MUSE_DECISION", ["NO_MATCHING_MUSE_DECISION"], {}

    # Any decision must reference an exact request for this intent.
    requests_by_ts = {r["slackMessageTs"]: r for r in matching_requests}
    bad_decisions = [
        d for d in matching_decisions
        if d["requestSlackMessageTs"] not in requests_by_ts
        or d["decidedUtc"] < requests_by_ts[d["requestSlackMessageTs"]]["requestedUtc"]
    ]
    if bad_decisions:
        return "HOLD_EVIDENCE_ORDERING", ["DECISION_NOT_BOUND_TO_PRIOR_REQUEST"], {}

    latest_by_time = matching_decisions[-1]
    same_latest_time = [d for d in matching_decisions if d["decidedUtc"] == latest_by_time["decidedUtc"]]
    if len(same_latest_time) > 1:
        # Simultaneous provider decisions are ambiguous even if they happen to
        # select the same seat: one must be durably canonical.
        return "HOLD_MUSE_CONFLICT", ["MULTIPLE_LATEST_MUSE_DECISIONS"], {}

    # A later HOLD/YIELD/REVOKED supersedes a prior selection.
    if latest_by_time["decision"] != "SELECTED":
        return "HOLD_NO_MUSE_DECISION", [f"LATEST_MUSE_DECISION_{latest_by_time['decision']}"], {
            "leaseId": latest_by_time["leaseId"]
        }

    selected_seats = {
        d["selectedSeat"]
        for d in matching_decisions
        if d["decision"] == "SELECTED"
        and d["decidedUtc"] == latest_by_time["decidedUtc"]
    }
    if len(selected_seats) != 1:
        return "HOLD_MUSE_CONFLICT", ["MUSE_SELECTION_AMBIGUOUS"], {}

    selected = latest_by_time["selectedSeat"]
    selected_request = requests_by_ts[latest_by_time["requestSlackMessageTs"]]
    if selected != selected_request["requesterSeat"]:
        return "HOLD_MUSE_CONFLICT", ["SELECTED_SEAT_DOES_NOT_MATCH_BOUND_REQUEST"], {
            "leaseId": latest_by_time["leaseId"]
        }

    # The exact route is already enforced by _same_intent, but keep a distinct
    # truth surface because route collision is the high-cost operational error.
    if latest_by_time["routeKey"] != intent["route"]["routeKey"]:
        return "HOLD_ROUTE_MISMATCH", ["MUSE_ROUTE_MISMATCH"], {
            "leaseId": latest_by_time["leaseId"]
        }

    return "READY_SINGLE_WRITER", ["EXACT_MUSE_SELECTION_AND_NO_PRIOR_SEND"], {
        "leaseId": latest_by_time["leaseId"],
        "selectedSeat": selected,
        "requestSlackMessageTs": latest_by_time["requestSlackMessageTs"],
        "museMessageTs": latest_by_time["museMessageTs"],
    }


def compile_report(raw: Any) -> dict[str, Any]:
    snapshot = normalize_snapshot(raw)
    result, reasons, selection = _evaluate(snapshot)
    if result not in RESULTS:
        _fail("INTERNAL_RESULT_ERROR")
    payload = {
        # Literal code-owned ceiling: public AUTHORITY_FALSE mutation/rebinding
        # cannot influence these values.
        "authorities": {
            "contractAuthorized": False,
            "externalSendAuthorized": False,
            "paymentAuthorized": False,
            "providerMutationAuthorized": False,
            "revenueRecognized": False,
            "submissionAuthorized": False,
        },
        "intentKey": snapshot["intent"]["intentKey"],
        "operationId": snapshot["intent"]["operationId"],
        "opportunityKey": snapshot["intent"]["opportunityKey"],
        "reasons": reasons,
        "result": result,
        "route": snapshot["intent"]["route"],
        "schemaVersion": SCHEMA_VERSION,
        "selection": selection,
        "sourceDigestSha256": sha256_text(canonical_json(snapshot)),
    }
    return {
        "payload": payload,
        "receiptSha256": sha256_text(canonical_json(payload)),
    }


def verify_report(raw: Any, report: Any) -> dict[str, Any]:
    expected = compile_report(raw)
    if not isinstance(report, dict):
        return {"reason": "REPORT_OBJECT_REQUIRED", "valid": False}
    if set(report) != {"payload", "receiptSha256"}:
        return {"reason": "REPORT_SCHEMA_MISMATCH", "valid": False}
    receipt = report.get("receiptSha256")
    if not isinstance(receipt, str) or not SHA256_RE.fullmatch(receipt):
        return {"reason": "REPORT_RECEIPT_INVALID", "valid": False}
    try:
        payload_digest = sha256_text(canonical_json(report.get("payload")))
    except GuardError:
        return {"reason": "REPORT_PAYLOAD_INVALID", "valid": False}
    if receipt != payload_digest:
        return {"reason": "REPORT_RECEIPT_MISMATCH", "valid": False}
    try:
        if canonical_json(report) != canonical_json(expected):
            return {"reason": "REPORT_SEMANTIC_MISMATCH", "valid": False}
    except GuardError:
        return {"reason": "REPORT_SEMANTIC_MISMATCH", "valid": False}
    return {"reason": None, "valid": True}


def _read_regular_file(path: str) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise GuardError("INPUT_OPEN_FAILED") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            _fail("INPUT_NOT_REGULAR_FILE")
        if info.st_size < 0 or info.st_size > MAX_INPUT_BYTES:
            _fail("INPUT_TOO_LARGE")
        chunks: list[bytes] = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_INPUT_BYTES:
            _fail("INPUT_TOO_LARGE")
        try:
            return data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise GuardError("INPUT_NOT_UTF8") from exc
    finally:
        os.close(fd)


def _write_exclusive(path: str, text: str) -> None:
    parent = os.path.dirname(path) or "."
    if not os.path.isdir(parent):
        _fail("OUTPUT_PARENT_MISSING")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise GuardError("OUTPUT_EXISTS") from exc
    except OSError as exc:
        raise GuardError("OUTPUT_OPEN_FAILED") from exc
    try:
        data = text.encode("utf-8")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                _fail("OUTPUT_WRITE_FAILED")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_path(path: str) -> Any:
    return strict_json_loads(_read_regular_file(path))


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline Muse-backed outbound single-writer preflight"
    )
    subs = parser.add_subparsers(dest="command", required=True)
    preflight = subs.add_parser("preflight", help="compile a single-writer preflight report")
    preflight.add_argument("snapshot")
    preflight.add_argument("output")
    verify = subs.add_parser("verify", help="verify report against exact source snapshot")
    verify.add_argument("snapshot")
    verify.add_argument("report")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            report = compile_report(_load_path(args.snapshot))
            _write_exclusive(args.output, canonical_json(report) + "\n")
            print(report["payload"]["result"])
            return 0
        result = verify_report(_load_path(args.snapshot), _load_path(args.report))
        if result["valid"]:
            print("VERIFIED")
            return 0
        print(result["reason"] or "VERIFY_FAILED", file=sys.stderr)
        return 2
    except GuardError as exc:
        print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
