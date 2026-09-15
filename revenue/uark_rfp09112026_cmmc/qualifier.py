#!/usr/bin/env python3
"""Fail-closed currentness facade for the UArk RFP09112026 qualifier.

The original deterministic compiler is retained in ``_qualifier_core.py``.  This
facade adds the trusted-time and frozen-source expiry rules required for
production use while preserving the published packet schema and receipts.
"""
from __future__ import annotations

import copy
import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_CORE_PATH = Path(__file__).with_name("_qualifier_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "uark_rfp09112026_qualifier_core", _CORE_PATH
)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import contract
    raise ImportError(f"cannot load UArk qualifier core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

# Preserve the original public/library surface.  Definitions below deliberately
# replace the compiler, verifier, renderer, and CLI entry point.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

ADDENDUM_RECHECK_BOUNDARY_UTC = "2026-10-06T05:00:00Z"
_FUTURE_SKEW = timedelta(minutes=5)
Clock = Callable[[], datetime]


def _trusted_now(now: datetime | None = None) -> datetime:
    value = datetime.now(timezone.utc) if now is None else now
    if not isinstance(value, datetime):
        raise InputError("trusted clock must return datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise InputError("trusted clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _utc_text(value: datetime) -> str:
    return _trusted_now(value).isoformat().replace("+00:00", "Z")


def _refresh_receipts(packet: dict[str, Any]) -> dict[str, Any]:
    decision = packet["decision"]
    decision.pop("decision_receipt_sha256", None)
    decision["decision_receipt_sha256"] = sha256_obj(decision)
    packet.pop("packet_receipt_sha256", None)
    packet["packet_receipt_sha256"] = sha256_obj(packet)
    return packet


def _apply_currentness(packet: dict[str, Any]) -> dict[str, Any]:
    evaluated = _dt(packet["evaluated_at_utc"])
    source_checked = _dt(packet["source_generation"]["hogbid_checked_at_utc"])
    recheck_boundary = _dt(ADDENDUM_RECHECK_BOUNDARY_UTC)
    blockers: list[str] = []

    if evaluated < source_checked:
        blockers.append("EVALUATION_PRECEDES_SOURCE_CAPTURE")
    if (
        evaluated >= recheck_boundary
        and source_checked < recheck_boundary
        and packet["source_generation"]["addenda_state"] == "NONE_LISTED"
    ):
        blockers.append("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED")

    if not blockers:
        return packet

    decision = packet["decision"]
    existing = list(decision["blockers"])
    for blocker in blockers:
        if blocker not in existing:
            existing.append(blocker)
    decision["blockers"] = existing
    if decision["status"] != "NO_BID":
        decision["status"] = "HOLD"
    decision["submission_ready"] = False
    return _refresh_receipts(packet)


def compile_qualification(intake: Any) -> dict[str, Any]:
    """Compile deterministic intake and enforce source/evaluation chronology."""
    return _apply_currentness(_core.compile_qualification(intake))


def compile_production(
    intake: Any,
    *,
    now: datetime | None = None,
    clock: Clock | None = None,
) -> dict[str, Any]:
    """Compile using trusted process time, never caller-supplied evaluation time."""
    if now is not None and clock is not None:
        raise InputError("provide now or clock, not both")
    trusted = _trusted_now(clock() if clock is not None else now)
    stamped = copy.deepcopy(intake)
    if not isinstance(stamped, dict):
        raise InputError("intake must be an object")
    stamped["evaluated_at_utc"] = _utc_text(trusted)
    return compile_qualification(stamped)


def verify_packet(packet: Any) -> bool:
    """Verify receipt integrity and the currentness-aware deterministic semantics."""
    required = {
        "schema", "operation", "owner", "model", "evaluated_at_utc", "buyer",
        "rfp_number", "question_deadline_utc", "proposal_deadline_utc",
        "last_planned_addendum_date", "internal_workshare_target_usd",
        "price_boundary", "source_generation", "candidate", "decision",
        "packet_receipt_sha256",
    }
    if not isinstance(packet, dict) or set(packet) != required:
        raise InputError("packet schema mismatch")
    receipt = packet["packet_receipt_sha256"]
    if not isinstance(receipt, str) or not SHA_RE.fullmatch(receipt):
        raise InputError("packet receipt invalid")
    unsigned = copy.deepcopy(packet)
    unsigned.pop("packet_receipt_sha256")
    if sha256_obj(unsigned) != receipt:
        raise InputError("packet receipt mismatch")
    intake = {
        "schema": SCHEMA,
        "evaluated_at_utc": packet["evaluated_at_utc"],
        "source_generation": packet["source_generation"],
        "candidate": packet["candidate"],
    }
    expected = compile_qualification(intake)
    if packet != expected:
        raise InputError("packet semantic verification failed")
    return True


def _decision_body(decision: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(decision)
    body.pop("decision_receipt_sha256", None)
    return body


def verify_packet_current(
    packet: Any,
    *,
    now: datetime | None = None,
    clock: Clock | None = None,
) -> bool:
    """Verify semantics and ensure trusted current time reproduces the decision."""
    verify_packet(packet)
    if now is not None and clock is not None:
        raise InputError("provide now or clock, not both")
    trusted = _trusted_now(clock() if clock is not None else now)
    evaluated = _dt(packet["evaluated_at_utc"])
    if evaluated > trusted + _FUTURE_SKEW:
        raise InputError("packet evaluation time is ahead of trusted current time")
    current_intake = {
        "schema": SCHEMA,
        "evaluated_at_utc": _utc_text(trusted),
        "source_generation": packet["source_generation"],
        "candidate": packet["candidate"],
    }
    current = compile_qualification(current_intake)
    if _decision_body(packet["decision"]) != _decision_body(current["decision"]):
        raise InputError("packet decision is no longer current")
    return True


def render_markdown(packet: dict[str, Any]) -> str:
    verify_packet(packet)
    decision = packet["decision"]
    blockers = "\n".join(f"- {item}" for item in decision["blockers"]) or "- none"
    risks = "\n".join(f"- {item}" for item in decision["risks"]) or "- none"
    return (
        "# UArk RFP09112026 qualification\n\n"
        f"**Route:** `{decision['route_requested']}`  \n"
        f"**Status:** `{decision['status']}`  \n"
        f"**Submission ready:** `{str(decision['submission_ready']).lower()}`  \n"
        f"**Internal workshare target:** `${packet['internal_workshare_target_usd']:,}`"
        f" — `{packet['price_boundary']}`\n\n"
        "## Blockers\n" + blockers + "\n\n"
        "## Risks / packet gaps\n" + risks + "\n\n"
        "## Authority boundary\n"
        "This result authorizes no buyer or partner contact, no portal action, no "
        "signature, no price commitment, no certification/assessment representation, "
        "no FCI/CUI handling, no contract acceptance, and no award/revenue claim. "
        "Any email requires a fresh collision/provider-history fence and explicit "
        "Muse single-writer selection.\n\n"
        f"Receipt: `{packet['packet_receipt_sha256']}`\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "compile":
            packet = compile_production(read_json_file(args.input_json))
            json_text = canonical_json(packet) + "\n"
            markdown_text = render_markdown(packet)
            if args.json_out:
                _write_exclusive(args.json_out, json_text)
            else:
                sys.stdout.write(json_text)
            if args.markdown_out:
                _write_exclusive(args.markdown_out, markdown_text)
            return 0
        if args.command == "verify":
            verify_packet_current(read_json_file(args.packet_json))
            print("VERIFIED")
            return 0
        raise InputError("unknown command")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
