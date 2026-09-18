# SPDX-License-Identifier: MIT
"""Strict Muse CLEAR reply parser for outbound duplicate-claim arbitration.

Accepts ONLY exact SELECTED|HOLD|COLLISION wire lines that bind the full
request tuple. Prose ``Cleared:`` replies, truncated keys, and key mismatches
are rejected with structured reason codes so the liveness ledger stays
fail-closed (MALFORMED_OR_UNDERBOUND_DECISION).

This module never authorizes send, contact, or provider mutation.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

REASON_OK = "OK"
REASON_UNDERBOUND_PROSE = "UNDERBOUND_PROSE"
REASON_KEY_TRUNCATED = "KEY_TRUNCATED"
REASON_KEY_MISMATCH = "KEY_MISMATCH"
REASON_MALFORMED_WIRE = "MALFORMED_WIRE"
REASON_BOUND_MISMATCH = "BOUND_MISMATCH"

DECISIONS = frozenset({"SELECTED", "HOLD", "COLLISION"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
# Exact single-line CLEAR wire (token order fixed; no prose prefix/suffix).
WIRE_RE = re.compile(
    r"^(SELECTED|HOLD|COLLISION)"
    r" key=(?P<key>\S+)"
    r" seat=(?P<seat>\S+)"
    r" counterparty=(?P<counterparty>\S+)"
    r" route=(?P<route>[0-9a-f]{64})"
    r" purpose=(?P<purpose>[0-9a-f]{64})"
    r" retry=(?P<retry>\S+)"
    r"(?: writer=(?P<writer>\S+)| reason=(?P<reason>\S+)| holders=(?P<holders>\S+))?$"
)
PROSE_CLEARED_RE = re.compile(
    r"(?i)^\s*cleared\b|you are the one sending|you are the one publishing|"
    r"m\s*use\s+arbitration\s+request"
)
TRUNCATION_MARK_RE = re.compile(r"(?:\.\.\.|…|\u2026)$")


def _as_request_tuple(request: Mapping[str, Any]) -> dict[str, str]:
    """Normalize REQUEST or already-flat tuple dict into comparable fields."""
    if "request_key" in request:
        return {
            "request_key": str(request["request_key"]),
            "seat_id": str(request["seat_id"]),
            "counterparty_key": str(request["counterparty_key"]),
            "route_sha256": str(request["route_sha256"]),
            "purpose_sha256": str(request["purpose_sha256"]),
            "retry_policy_generation": str(request["retry_policy_generation"]),
        }
    raise ValueError("request must include request_key and bound tuple fields")


def _looks_truncated(observed: str, expected: str) -> bool:
    if not observed or not expected:
        return False
    if TRUNCATION_MARK_RE.search(observed):
        return True
    if observed == expected:
        return False
    # Proper prefix of the expected full key (common Muse truncation).
    if expected.startswith(observed) and len(observed) < len(expected):
        return True
    # Observed is expected with ellipsis stripped.
    stripped = TRUNCATION_MARK_RE.sub("", observed)
    if stripped and expected.startswith(stripped) and stripped != expected:
        return True
    return False


def parse_clear_reply(text: str, request: Mapping[str, Any]) -> dict[str, Any]:
    """Parse a Muse CLEAR reply against an exact REQUEST tuple.

    Returns a structured result::

        {
          "ok": bool,
          "reason": "OK"|"UNDERBOUND_PROSE"|"KEY_TRUNCATED"|"KEY_MISMATCH"|...,
          "decision": "SELECTED"|"HOLD"|"COLLISION"|None,
          "bound": {...}|None,
          "extra": {"writer"|"reason"|"holders": ...}|None,
          "raw_line": str|None,
        }
    """
    if type(text) is not str:
        return _reject(REASON_MALFORMED_WIRE, raw_line=None)
    req = _as_request_tuple(request)
    expected_key = req["request_key"]

    # Work on the first non-empty line; CLEAR wire is a single line.
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    if not lines:
        return _reject(REASON_MALFORMED_WIRE, raw_line=None)

    # If any line starts with prose Cleared: / narrative, reject immediately
    # even if a later line looks wire-shaped (fail closed).
    for ln in lines:
        if PROSE_CLEARED_RE.search(ln) and not WIRE_RE.match(ln):
            # Also catch key= fragments inside prose for truncation/mismatch.
            key_m = re.search(r"(?i)\bkey=([^\s,·]+)", ln)
            if key_m:
                observed = key_m.group(1).rstrip(".,;")
                if _looks_truncated(observed, expected_key):
                    return _reject(REASON_KEY_TRUNCATED, raw_line=ln, decision=None)
                if observed != expected_key:
                    return _reject(REASON_KEY_MISMATCH, raw_line=ln, decision=None)
            return _reject(REASON_UNDERBOUND_PROSE, raw_line=ln)

    # Prefer an exact wire match on any line; otherwise underbound.
    match = None
    raw_line = None
    for ln in lines:
        m = WIRE_RE.match(ln)
        if m:
            match = m
            raw_line = ln
            break
    if match is None:
        # Non-wire text that still mentions a key.
        joined = " ".join(lines)
        if PROSE_CLEARED_RE.search(joined) or re.search(r"(?i)\bcleared\b", joined):
            key_m = re.search(r"(?i)\bkey=([^\s,·]+)", joined)
            if key_m:
                observed = key_m.group(1).rstrip(".,;")
                if _looks_truncated(observed, expected_key):
                    return _reject(REASON_KEY_TRUNCATED, raw_line=lines[0])
                if observed != expected_key:
                    return _reject(REASON_KEY_MISMATCH, raw_line=lines[0])
            return _reject(REASON_UNDERBOUND_PROSE, raw_line=lines[0])
        key_m = re.search(r"(?i)\bkey=([^\s,·]+)", joined)
        if key_m:
            observed = key_m.group(1).rstrip(".,;")
            if _looks_truncated(observed, expected_key):
                return _reject(REASON_KEY_TRUNCATED, raw_line=lines[0])
            if observed != expected_key:
                return _reject(REASON_KEY_MISMATCH, raw_line=lines[0])
        return _reject(REASON_MALFORMED_WIRE, raw_line=lines[0])

    decision = match.group(1)
    observed_key = match.group("key")
    if _looks_truncated(observed_key, expected_key):
        return _reject(REASON_KEY_TRUNCATED, raw_line=raw_line, decision=decision)
    if observed_key != expected_key:
        return _reject(REASON_KEY_MISMATCH, raw_line=raw_line, decision=decision)

    bound = {
        "bound_request_key": observed_key,
        "bound_seat_id": match.group("seat"),
        "bound_counterparty_key": match.group("counterparty"),
        "bound_route_sha256": match.group("route"),
        "bound_purpose_sha256": match.group("purpose"),
        "bound_retry_policy_generation": match.group("retry"),
    }
    if not HEX64.match(bound["bound_route_sha256"]) or not HEX64.match(bound["bound_purpose_sha256"]):
        return _reject(REASON_MALFORMED_WIRE, raw_line=raw_line, decision=decision)

    expected_bound = {
        "bound_request_key": req["request_key"],
        "bound_seat_id": req["seat_id"],
        "bound_counterparty_key": req["counterparty_key"],
        "bound_route_sha256": req["route_sha256"],
        "bound_purpose_sha256": req["purpose_sha256"],
        "bound_retry_policy_generation": req["retry_policy_generation"],
    }
    if bound != expected_bound:
        return {
            "ok": False,
            "reason": REASON_BOUND_MISMATCH,
            "decision": decision,
            "bound": bound,
            "extra": None,
            "raw_line": raw_line,
        }

    # Disposition-specific extras (optional but validated when present).
    extra: dict[str, str] = {}
    if decision == "SELECTED":
        writer = match.group("writer")
        if writer:
            extra["writer"] = writer
    elif decision == "HOLD":
        reason = match.group("reason")
        if reason:
            extra["reason"] = reason
    elif decision == "COLLISION":
        holders = match.group("holders")
        if holders:
            extra["holders"] = holders

    return {
        "ok": True,
        "reason": REASON_OK,
        "decision": decision,
        "bound": bound,
        "extra": extra or None,
        "raw_line": raw_line,
    }


def _reject(
    reason: str,
    *,
    raw_line: Optional[str],
    decision: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "decision": decision,
        "bound": None,
        "extra": None,
        "raw_line": raw_line,
    }


def decision_event_from_parse(
    parse_result: Mapping[str, Any],
    *,
    provider_event_id: str,
    provider_event_sha256: str,
    observed_at: str,
    supersedes_provider_event_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a ledger DECISION event from an OK parse result."""
    if not parse_result.get("ok"):
        raise ValueError("cannot mint DECISION from non-OK clear parse")
    bound = parse_result["bound"]
    event = {
        "type": "DECISION",
        "provider_event_id": provider_event_id,
        "provider_event_sha256": provider_event_sha256,
        "observed_at": observed_at,
        "decision": parse_result["decision"],
        "bound_request_key": bound["bound_request_key"],
        "bound_seat_id": bound["bound_seat_id"],
        "bound_counterparty_key": bound["bound_counterparty_key"],
        "bound_route_sha256": bound["bound_route_sha256"],
        "bound_purpose_sha256": bound["bound_purpose_sha256"],
        "bound_retry_policy_generation": bound["bound_retry_policy_generation"],
        "supersedes_provider_event_id": supersedes_provider_event_id,
    }
    return event
