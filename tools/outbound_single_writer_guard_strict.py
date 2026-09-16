#!/usr/bin/env python3
"""Route/scope fence for the Muse-backed outbound single-writer core.

The core evaluator deliberately matches exact rows. This wrapper adds an earlier
fail-closed fence: if the same intent key appears on any request, Muse decision,
or send receipt with a different operation/opportunity/route, it refuses READY
and exposes whether the rebound was scope- or route-specific.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import outbound_single_writer_guard as core


def _strict_conflict(snapshot: dict[str, Any]) -> tuple[str, str] | None:
    intent = snapshot["intent"]
    rows = snapshot["requests"] + snapshot["decisions"] + snapshot["sendReceipts"]
    for row in rows:
        if row["intentKey"] != intent["intentKey"]:
            continue
        if (
            row["operationId"] != intent["operationId"]
            or row["opportunityKey"] != intent["opportunityKey"]
        ):
            return "HOLD_SOURCE_CONFLICT", "INTENT_KEY_REBOUND_TO_DIFFERENT_SCOPE"
        if row["routeKey"] != intent["route"]["routeKey"]:
            return "HOLD_ROUTE_MISMATCH", "INTENT_KEY_REBOUND_TO_DIFFERENT_ROUTE"
    return None


def _hold_report(snapshot: dict[str, Any], result: str, reason: str) -> dict[str, Any]:
    payload = {
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
        "reasons": [reason],
        "result": result,
        "route": snapshot["intent"]["route"],
        "schemaVersion": core.SCHEMA_VERSION,
        "selection": {},
        "sourceDigestSha256": core.sha256_text(core.canonical_json(snapshot)),
    }
    return {
        "payload": payload,
        "receiptSha256": core.sha256_text(core.canonical_json(payload)),
    }


def compile_report(raw: Any) -> dict[str, Any]:
    snapshot = core.normalize_snapshot(raw)
    conflict = _strict_conflict(snapshot)
    if conflict is None:
        return core.compile_report(snapshot)
    result, reason = conflict
    return _hold_report(snapshot, result, reason)


def verify_report(raw: Any, report: Any) -> dict[str, Any]:
    expected = compile_report(raw)
    if not isinstance(report, dict):
        return {"reason": "REPORT_OBJECT_REQUIRED", "valid": False}
    if set(report) != {"payload", "receiptSha256"}:
        return {"reason": "REPORT_SCHEMA_MISMATCH", "valid": False}
    receipt = report.get("receiptSha256")
    if not isinstance(receipt, str) or not core.SHA256_RE.fullmatch(receipt):
        return {"reason": "REPORT_RECEIPT_INVALID", "valid": False}
    try:
        digest = core.sha256_text(core.canonical_json(report.get("payload")))
        if receipt != digest:
            return {"reason": "REPORT_RECEIPT_MISMATCH", "valid": False}
        if core.canonical_json(report) != core.canonical_json(expected):
            return {"reason": "REPORT_SEMANTIC_MISMATCH", "valid": False}
    except core.GuardError:
        return {"reason": "REPORT_SEMANTIC_MISMATCH", "valid": False}
    return {"reason": None, "valid": True}


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strict Muse-backed outbound single-writer preflight")
    subs = parser.add_subparsers(dest="command", required=True)
    preflight = subs.add_parser("preflight")
    preflight.add_argument("snapshot")
    preflight.add_argument("output")
    verify = subs.add_parser("verify")
    verify.add_argument("snapshot")
    verify.add_argument("report")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            report = compile_report(core._load_path(args.snapshot))
            core._write_exclusive(args.output, core.canonical_json(report) + "\n")
            print(report["payload"]["result"])
            return 0
        result = verify_report(core._load_path(args.snapshot), core._load_path(args.report))
        if result["valid"]:
            print("VERIFIED")
            return 0
        print(result["reason"] or "VERIFY_FAILED", file=sys.stderr)
        return 2
    except core.GuardError as exc:
        print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
