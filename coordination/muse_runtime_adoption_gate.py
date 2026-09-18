#!/usr/bin/env python3
"""Offline evidence gate for Muse atomic runtime adoption.

This module diagnoses whether one retained transcript is internally consistent with
one session-bound SELECTED -> LEASED -> CONSUMED -> GO sequence.  It never grants
send authority and never independently authenticates the live Muse runtime or a
provider send.
"""
from __future__ import annotations

import argparse as _argparse
import hashlib as _hashlib
import json as _json
import os as _os
import stat as _stat
import sys as _sys
import time as _time
import unicodedata as _unicodedata
from datetime import datetime as _datetime, timezone as _timezone
from pathlib import Path as _Path
from typing import Any as _Any

_INPUT_SCHEMA = "commons.muse-runtime-adoption-evidence/v1"
_OUTPUT_SCHEMA = "commons.muse-runtime-adoption-diagnostic/v1"
_VERIFY_SCHEMA = "commons.muse-runtime-adoption-verification/v1"
_MAX_INPUT_BYTES = 1_048_576
_MAX_TEXT = 512
_MAX_EVENTS = 128
_MAX_DEPTH = 20
_MAX_INT = 2**53 - 1
_MAX_FRESHNESS_SECONDS = 86_400
_EVENT_CLASSES = frozenset({"SELECTED", "LEASED", "CONSUMED", "GO", "COMMIT"})
_POSITIVE_SEQUENCE = ("SELECTED", "LEASED", "CONSUMED", "GO")
_STATUS = frozenset(
    {
        "ATOMIC_SEQUENCE_OBSERVED",
        "HOLD_SELECTED_ONLY",
        "HOLD_NO_CONSUME",
        "HOLD_NO_GO",
        "HOLD_DUPLICATE_GO",
        "HOLD_WRONG_SESSION",
        "HOLD_SCOPE_DRIFT",
        "HOLD_RUNTIME_DRIFT",
        "HOLD_STALE_CAPTURE",
        "HOLD_EVIDENCE",
    }
)
_AUTHORITY = {
    "send_authorized": False,
    "muse_authorized": False,
    "provider_action_authorized": False,
    "provider_send_proven": False,
    "buyer_acceptance": False,
    "contract_signed": False,
    "payment_authorized": False,
    "cash_proven": False,
    "receivable_asserted": False,
    "revenue_recognized": False,
}


class AdoptionGateError(ValueError):
    """Stable domain error for malformed or untrusted evidence."""


def _build_api():
    # Capture trust-bearing primitives and semantic constants once. Public module
    # rebinding after import cannot steer this generation of the exported API.
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    verify_schema = _VERIFY_SCHEMA
    max_input_bytes = _MAX_INPUT_BYTES
    max_text = _MAX_TEXT
    max_events = _MAX_EVENTS
    max_depth = _MAX_DEPTH
    max_int = _MAX_INT
    max_freshness_seconds = _MAX_FRESHNESS_SECONDS
    event_classes = frozenset(_EVENT_CLASSES)
    positive_sequence = tuple(_POSITIVE_SEQUENCE)
    status_values = frozenset(_STATUS)
    authority_items = tuple(sorted(_AUTHORITY.items()))
    error_cls = AdoptionGateError
    path_cls = _Path
    sha256_ctor = _hashlib.sha256
    normalize = _unicodedata.normalize
    category = _unicodedata.category
    dt_cls = _datetime
    utc = _timezone.utc
    time_ns = _time.time_ns
    json_decoder_cls = _json.JSONDecoder
    quote_json = _json.encoder.encode_basestring_ascii
    os_open = _os.open
    os_read = _os.read
    os_fstat = _os.fstat
    os_close = _os.close
    os_flags = {
        "O_RDONLY": _os.O_RDONLY,
        "O_CLOEXEC": getattr(_os, "O_CLOEXEC", 0),
        "O_NOFOLLOW": getattr(_os, "O_NOFOLLOW", 0),
    }
    s_isreg = _stat.S_ISREG

    def fail(message: str) -> None:
        raise error_cls(message)

    def bounded_int_token(token: str) -> int:
        # Bound parser work before int() sees attacker-sized text.
        if len(token) > 16:
            fail("integer token exceeds bounded length")
        try:
            value = int(token, 10)
        except ValueError as exc:  # pragma: no cover - JSON lexer normally filters
            raise error_cls("invalid integer token") from exc
        if value < -max_int or value > max_int:
            fail("integer exceeds safe range")
        return value

    def reject_float(_token: str):
        fail("floating-point JSON is not admitted")

    def reject_constant(_token: str):
        fail("non-finite JSON is not admitted")

    def object_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                fail(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    decoder = json_decoder_cls(
        object_pairs_hook=object_pairs,
        parse_int=bounded_int_token,
        parse_float=reject_float,
        parse_constant=reject_constant,
        strict=True,
    )
    raw_decode = decoder.raw_decode

    def walk_plain(value: _Any, depth: int = 0) -> None:
        if depth > max_depth:
            fail("JSON nesting exceeds limit")
        if value is None or type(value) in (bool, int, str):
            if type(value) is int and (value < -max_int or value > max_int):
                fail("integer exceeds safe range")
            if type(value) is str:
                try:
                    value.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise error_cls("lone surrogate is not admitted") from exc
            return
        if type(value) is list:
            if len(value) > max_events * 4:
                fail("array exceeds limit")
            for item in value:
                walk_plain(item, depth + 1)
            return
        if type(value) is dict:
            if len(value) > 128:
                fail("object exceeds key limit")
            for key, item in value.items():
                if type(key) is not str:
                    fail("object keys must be text")
                walk_plain(key, depth + 1)
                walk_plain(item, depth + 1)
            return
        fail("JSON value is not an exact built-in plain type")

    def loads_strict(data: str | bytes) -> _Any:
        if type(data) is bytes:
            if len(data) > max_input_bytes:
                fail("input exceeds byte limit")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise error_cls("input must be UTF-8") from exc
        elif type(data) is str:
            try:
                encoded = data.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise error_cls("input contains invalid Unicode") from exc
            if len(encoded) > max_input_bytes:
                fail("input exceeds byte limit")
            text = data
        else:
            fail("JSON input must be str or bytes")
        try:
            value, end = raw_decode(text)
        except (ValueError, RecursionError) as exc:
            if isinstance(exc, error_cls):
                raise
            raise error_cls("invalid JSON") from exc
        if text[end:].strip():
            fail("trailing JSON content is not admitted")
        walk_plain(value)
        return value

    def canonical(value: _Any) -> bytes:
        walk_plain(value)

        def enc(v: _Any, depth: int = 0) -> str:
            if depth > max_depth:
                fail("canonical JSON nesting exceeds limit")
            if v is None:
                return "null"
            if v is True:
                return "true"
            if v is False:
                return "false"
            if type(v) is int:
                return str(v)
            if type(v) is str:
                return quote_json(v)
            if type(v) is list:
                return "[" + ",".join(enc(x, depth + 1) for x in v) + "]"
            if type(v) is dict:
                parts = []
                for key in sorted(v):
                    parts.append(quote_json(key) + ":" + enc(v[key], depth + 1))
                return "{" + ",".join(parts) + "}"
            fail("unsupported canonical JSON type")
            raise AssertionError

        return enc(value).encode("utf-8")

    def digest(value: _Any) -> str:
        return sha256_ctor(canonical(value)).hexdigest()

    def text(value: _Any, name: str, *, maximum: int = max_text) -> str:
        if type(value) is not str or not value or len(value) > maximum:
            fail(f"{name} must be non-empty text <= {maximum} chars")
        if value != value.strip():
            fail(f"{name} must not have leading/trailing whitespace")
        if normalize("NFC", value) != value:
            fail(f"{name} must use NFC Unicode")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise error_cls(f"{name} contains invalid Unicode") from exc
        visible = False
        for ch in value:
            cat = category(ch)
            if cat.startswith("C"):
                fail(f"{name} contains a control/format/surrogate codepoint")
            if not ch.isspace() and not cat.startswith("M"):
                visible = True
        if not visible:
            fail(f"{name} must contain a visible base character")
        return value

    def sha(value: _Any, name: str) -> str:
        value = text(value, name, maximum=64)
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            fail(f"{name} must be lowercase SHA-256 hex")
        return value

    def integer(value: _Any, name: str, *, minimum: int = 0, maximum: int = max_int) -> int:
        if type(value) is not int or value < minimum or value > maximum:
            fail(f"{name} must be integer in [{minimum},{maximum}]")
        return value

    def exact_keys(value: _Any, name: str, keys: set[str]) -> dict[str, _Any]:
        if type(value) is not dict:
            fail(f"{name} must be an object")
        actual = set(value)
        if actual != keys:
            missing = sorted(keys - actual)
            extra = sorted(actual - keys)
            fail(f"{name} schema mismatch missing={missing} extra={extra}")
        return value

    def parse_utc(value: _Any, name: str) -> tuple[str, int]:
        value = text(value, name, maximum=32)
        if not value.endswith("Z"):
            fail(f"{name} must be canonical UTC ending in Z")
        try:
            dt = dt_cls.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise error_cls(f"{name} is not valid UTC") from exc
        if dt.tzinfo != utc or dt.microsecond != 0:
            fail(f"{name} must be whole-second UTC")
        canonical_text = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if canonical_text != value:
            fail(f"{name} must be canonical whole-second UTC")
        return value, int(dt.timestamp())

    def utc_from_epoch(second: int) -> str:
        integer(second, "epoch_second")
        return dt_cls.fromtimestamp(second, tz=utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    root_keys = {
        "schema",
        "operation_key",
        "counterparty",
        "route",
        "purpose",
        "lease_id",
        "selected_session",
        "runtime",
        "capture",
        "transcript_source_ref",
        "transcript_source_sha256",
        "events",
    }
    runtime_keys = {"instance_id", "build_id", "source_sha256"}
    capture_keys = {"captured_at", "max_age_seconds"}
    event_base = {
        "id",
        "event_class",
        "occurred_at",
        "operation_key",
        "counterparty",
        "route",
        "purpose",
        "lease_id",
        "session",
        "runtime_instance_id",
        "runtime_build_id",
        "runtime_source_sha256",
        "source_ref",
        "source_sha256",
    }

    def normalize_packet(packet: _Any) -> dict[str, _Any]:
        exact_keys(packet, "packet", root_keys)
        if packet["schema"] != input_schema:
            fail("unsupported input schema")
        runtime = exact_keys(packet["runtime"], "runtime", runtime_keys)
        capture = exact_keys(packet["capture"], "capture", capture_keys)
        events = packet["events"]
        if type(events) is not list or not events or len(events) > max_events:
            fail(f"events must be a non-empty list <= {max_events}")

        out: dict[str, _Any] = {
            "schema": input_schema,
            "operation_key": text(packet["operation_key"], "operation_key", maximum=240),
            "counterparty": text(packet["counterparty"], "counterparty"),
            "route": text(packet["route"], "route"),
            "purpose": text(packet["purpose"], "purpose"),
            "lease_id": text(packet["lease_id"], "lease_id", maximum=128),
            "selected_session": text(packet["selected_session"], "selected_session", maximum=160),
            "runtime": {
                "instance_id": text(runtime["instance_id"], "runtime.instance_id", maximum=160),
                "build_id": text(runtime["build_id"], "runtime.build_id", maximum=160),
                "source_sha256": sha(runtime["source_sha256"], "runtime.source_sha256"),
            },
            "capture": {},
            "transcript_source_ref": text(packet["transcript_source_ref"], "transcript_source_ref"),
            "transcript_source_sha256": sha(packet["transcript_source_sha256"], "transcript_source_sha256"),
            "events": [],
        }
        captured_text, captured_s = parse_utc(capture["captured_at"], "capture.captured_at")
        out["capture"] = {
            "captured_at": captured_text,
            "captured_at_s": captured_s,
            "max_age_seconds": integer(
                capture["max_age_seconds"],
                "capture.max_age_seconds",
                minimum=1,
                maximum=max_freshness_seconds,
            ),
        }

        seen_ids: set[str] = set()
        previous_event_s: int | None = None
        for idx, raw in enumerate(events):
            if type(raw) is not dict:
                fail(f"events[{idx}] must be an object")
            cls = raw.get("event_class")
            if type(cls) is not str or cls not in event_classes:
                fail(f"events[{idx}].event_class is unsupported")
            keys = set(event_base)
            if cls in {"CONSUMED", "GO"}:
                keys.add("capability_sha256")
            elif cls == "COMMIT":
                keys.update({"capability_sha256", "provider", "provider_message_id"})
            exact_keys(raw, f"events[{idx}]", keys)
            event_id = text(raw["id"], f"events[{idx}].id", maximum=160)
            if event_id in seen_ids:
                fail("duplicate event id is not admitted")
            seen_ids.add(event_id)
            occurred_text, occurred_s = parse_utc(raw["occurred_at"], f"events[{idx}].occurred_at")
            if previous_event_s is not None and occurred_s <= previous_event_s:
                fail("events must be strictly increasing in retained order")
            previous_event_s = occurred_s
            event: dict[str, _Any] = {
                "id": event_id,
                "event_class": cls,
                "occurred_at": occurred_text,
                "occurred_at_s": occurred_s,
                "operation_key": text(raw["operation_key"], f"events[{idx}].operation_key", maximum=240),
                "counterparty": text(raw["counterparty"], f"events[{idx}].counterparty"),
                "route": text(raw["route"], f"events[{idx}].route"),
                "purpose": text(raw["purpose"], f"events[{idx}].purpose"),
                "lease_id": text(raw["lease_id"], f"events[{idx}].lease_id", maximum=128),
                "session": text(raw["session"], f"events[{idx}].session", maximum=160),
                "runtime_instance_id": text(raw["runtime_instance_id"], f"events[{idx}].runtime_instance_id", maximum=160),
                "runtime_build_id": text(raw["runtime_build_id"], f"events[{idx}].runtime_build_id", maximum=160),
                "runtime_source_sha256": sha(raw["runtime_source_sha256"], f"events[{idx}].runtime_source_sha256"),
                "source_ref": text(raw["source_ref"], f"events[{idx}].source_ref"),
                "source_sha256": sha(raw["source_sha256"], f"events[{idx}].source_sha256"),
            }
            if cls in {"CONSUMED", "GO", "COMMIT"}:
                event["capability_sha256"] = sha(raw["capability_sha256"], f"events[{idx}].capability_sha256")
            if cls == "COMMIT":
                event["provider"] = text(raw["provider"], f"events[{idx}].provider", maximum=80)
                event["provider_message_id"] = text(
                    raw["provider_message_id"], f"events[{idx}].provider_message_id", maximum=240
                )
            out["events"].append(event)
        return out

    def input_projection(normalized: dict[str, _Any]) -> dict[str, _Any]:
        # Strip parser-only epoch helpers before hashing/emitting source identity.
        projected = {
            key: value
            for key, value in normalized.items()
            if key not in {"events", "capture"}
        }
        projected["capture"] = {
            "captured_at": normalized["capture"]["captured_at"],
            "max_age_seconds": normalized["capture"]["max_age_seconds"],
        }
        projected["events"] = []
        for event in normalized["events"]:
            projected["events"].append({key: value for key, value in event.items() if key != "occurred_at_s"})
        return projected

    def status_for(normalized: dict[str, _Any], now_s: int) -> tuple[str, list[str], dict[str, int]]:
        integer(now_s, "now_s")
        capture = normalized["capture"]
        events = normalized["events"]
        reasons: list[str] = []
        counts = {name: 0 for name in sorted(event_classes)}
        for event in events:
            counts[event["event_class"]] += 1

        # Future evidence/capture and capture-before-event are evidence failures.
        if capture["captured_at_s"] > now_s:
            reasons.append("capture_is_future")
        if any(event["occurred_at_s"] > now_s for event in events):
            reasons.append("event_is_future")
        if events[-1]["occurred_at_s"] > capture["captured_at_s"]:
            reasons.append("capture_precedes_latest_event")
        if reasons:
            return "HOLD_EVIDENCE", reasons, counts

        if now_s > capture["captured_at_s"] + capture["max_age_seconds"]:
            return "HOLD_STALE_CAPTURE", ["capture_exceeds_freshness_window"], counts

        root_scope = (
            normalized["operation_key"],
            normalized["counterparty"],
            normalized["route"],
            normalized["purpose"],
            normalized["lease_id"],
        )
        for event in events:
            event_scope = (
                event["operation_key"],
                event["counterparty"],
                event["route"],
                event["purpose"],
                event["lease_id"],
            )
            if event_scope != root_scope:
                return "HOLD_SCOPE_DRIFT", [f"scope_drift:{event['id']}"], counts

        runtime = normalized["runtime"]
        runtime_tuple = (runtime["instance_id"], runtime["build_id"], runtime["source_sha256"])
        for event in events:
            event_runtime = (
                event["runtime_instance_id"],
                event["runtime_build_id"],
                event["runtime_source_sha256"],
            )
            if event_runtime != runtime_tuple:
                return "HOLD_RUNTIME_DRIFT", [f"runtime_drift:{event['id']}"], counts

        selected = normalized["selected_session"]
        for event in events:
            if event["session"] != selected:
                return "HOLD_WRONG_SESSION", [f"wrong_session:{event['id']}"], counts

        # A transcript must start with exactly one SELECTED and at most one LEASED/
        # CONSUMED. Duplicate GO has its own terminal state because it is the
        # reproduced economic failure class.
        if counts["GO"] > 1:
            return "HOLD_DUPLICATE_GO", ["multiple_go_events"], counts
        if counts["SELECTED"] != 1:
            return "HOLD_EVIDENCE", ["selected_count_must_equal_one"], counts
        if counts["LEASED"] > 1 or counts["CONSUMED"] > 1 or counts["COMMIT"] > 1:
            return "HOLD_EVIDENCE", ["non_go_event_count_exceeds_one"], counts

        classes = [event["event_class"] for event in events]
        if classes[0] != "SELECTED":
            return "HOLD_EVIDENCE", ["first_event_must_be_selected"], counts
        if counts["LEASED"] == 0:
            if len(events) == 1:
                return "HOLD_SELECTED_ONLY", ["selection_observed_without_lease"], counts
            return "HOLD_EVIDENCE", ["events_after_selected_without_lease"], counts
        if counts["CONSUMED"] == 0:
            if "GO" in classes or "COMMIT" in classes:
                return "HOLD_NO_CONSUME", ["go_or_commit_without_consume"], counts
            return "HOLD_NO_CONSUME", ["lease_not_consumed"], counts
        if counts["GO"] == 0:
            if "COMMIT" in classes:
                return "HOLD_NO_GO", ["commit_without_go"], counts
            return "HOLD_NO_GO", ["consume_observed_without_go"], counts

        # Require exactly the positive prefix, with optional COMMIT last.
        expected = list(positive_sequence)
        if classes[:4] != expected:
            return "HOLD_EVIDENCE", ["atomic_sequence_order_mismatch"], counts
        if len(classes) > 5 or (len(classes) == 5 and classes[4] != "COMMIT"):
            return "HOLD_EVIDENCE", ["events_after_go_are_not_single_commit"], counts

        consumed = next(event for event in events if event["event_class"] == "CONSUMED")
        go = next(event for event in events if event["event_class"] == "GO")
        if consumed["capability_sha256"] != go["capability_sha256"]:
            return "HOLD_EVIDENCE", ["consume_go_capability_digest_mismatch"], counts
        if counts["COMMIT"] == 1:
            commit = next(event for event in events if event["event_class"] == "COMMIT")
            if commit["capability_sha256"] != go["capability_sha256"]:
                return "HOLD_EVIDENCE", ["commit_go_capability_digest_mismatch"], counts
        return "ATOMIC_SEQUENCE_OBSERVED", ["retained_sequence_internally_consistent"], counts

    def compile_at(packet: _Any, now_s: int) -> dict[str, _Any]:
        normalized = normalize_packet(packet)
        now_s = integer(now_s, "now_s")
        status, reasons, counts = status_for(normalized, now_s)
        projected = input_projection(normalized)
        commit = next((e for e in normalized["events"] if e["event_class"] == "COMMIT"), None)
        diagnostic: dict[str, _Any] = {
            "schema": output_schema,
            "input_schema": input_schema,
            "input_sha256": digest(projected),
            "operation_key": normalized["operation_key"],
            "counterparty": normalized["counterparty"],
            "route": normalized["route"],
            "purpose": normalized["purpose"],
            "lease_id": normalized["lease_id"],
            "selected_session": normalized["selected_session"],
            "runtime": dict(normalized["runtime"]),
            "captured_at": normalized["capture"]["captured_at"],
            "max_age_seconds": normalized["capture"]["max_age_seconds"],
            "evaluated_at": utc_from_epoch(now_s),
            "status": status,
            "reasons": reasons,
            "event_counts": counts,
            "event_classes": [e["event_class"] for e in normalized["events"]],
            "atomic_sequence_consistent": status == "ATOMIC_SEQUENCE_OBSERVED",
            "provider_commit_observed": commit is not None,
            "provider_commit": (
                {"provider": commit["provider"], "provider_message_id": commit["provider_message_id"]}
                if commit is not None
                else None
            ),
            "evidence_claims": {
                "retained_transcript_internally_consistent": status == "ATOMIC_SEQUENCE_OBSERVED",
                "runtime_deployment_independently_authenticated": False,
                "provider_send_independently_authenticated": False,
            },
            "authority": dict(authority_items),
        }
        diagnostic["receipt_sha256"] = digest(diagnostic)
        return diagnostic

    def process_now_s() -> int:
        return time_ns() // 1_000_000_000

    def compile_current(packet: _Any) -> dict[str, _Any]:
        return compile_at(packet, process_now_s())

    diagnostic_keys = {
        "schema",
        "input_schema",
        "input_sha256",
        "operation_key",
        "counterparty",
        "route",
        "purpose",
        "lease_id",
        "selected_session",
        "runtime",
        "captured_at",
        "max_age_seconds",
        "evaluated_at",
        "status",
        "reasons",
        "event_counts",
        "event_classes",
        "atomic_sequence_consistent",
        "provider_commit_observed",
        "provider_commit",
        "evidence_claims",
        "authority",
        "receipt_sha256",
    }

    def verify_artifact(packet: _Any, diagnostic: _Any) -> tuple[bool, str, dict[str, _Any] | None]:
        try:
            exact_keys(diagnostic, "diagnostic", diagnostic_keys)
            if diagnostic["schema"] != output_schema or diagnostic["input_schema"] != input_schema:
                return False, "schema_mismatch", None
            receipt = sha(diagnostic["receipt_sha256"], "diagnostic.receipt_sha256")
            unsigned = dict(diagnostic)
            unsigned.pop("receipt_sha256")
            if digest(unsigned) != receipt:
                return False, "receipt_mismatch", None
            if diagnostic["status"] not in status_values:
                return False, "status_invalid", None
            evaluated_text, evaluated_s = parse_utc(diagnostic["evaluated_at"], "diagnostic.evaluated_at")
            if evaluated_text != diagnostic["evaluated_at"]:
                return False, "evaluated_at_invalid", None
            expected = compile_at(packet, evaluated_s)
            if canonical(expected) != canonical(diagnostic):
                return False, "semantic_recompile_mismatch", expected
            return True, "artifact_authenticated", expected
        except error_cls as exc:
            return False, f"artifact_invalid:{exc}", None

    def verify_current(packet: _Any, diagnostic: _Any) -> dict[str, _Any]:
        valid, reason, _expected = verify_artifact(packet, diagnostic)
        now_s = process_now_s()
        current = compile_at(packet, now_s)
        current_status = current["status"]
        artifact_status = diagnostic.get("status") if type(diagnostic) is dict else None
        current_match = bool(valid and artifact_status == current_status)
        result = {
            "schema": verify_schema,
            "valid": current_match,
            "reason": "CURRENT_STATUS_MATCH" if current_match else reason if not valid else "CURRENT_STATUS_CHANGED",
            "artifact_status": artifact_status,
            "current_status": current_status,
            "checked_at": utc_from_epoch(now_s),
            "send_authorized": False,
            "provider_action_authorized": False,
            "provider_send_proven": False,
            "payment_authorized": False,
            "cash_proven": False,
            "revenue_recognized": False,
        }
        result["receipt_sha256"] = digest(result)
        return result

    def read_file(path_value: str | _os.PathLike[str]) -> bytes:
        path = path_cls(path_value)
        flags = os_flags["O_RDONLY"] | os_flags["O_CLOEXEC"] | os_flags["O_NOFOLLOW"]
        try:
            fd = os_open(path, flags)
        except OSError as exc:
            raise error_cls(f"cannot open retained file: {path}") from exc
        try:
            st = os_fstat(fd)
            if not s_isreg(st.st_mode) or st.st_size < 0 or st.st_size > max_input_bytes:
                fail("retained file must be bounded regular file")
            chunks = []
            remaining = st.st_size
            while remaining:
                chunk = os_read(fd, min(65536, remaining))
                if not chunk:
                    fail("retained file truncated during read")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os_read(fd, 1):
                fail("retained file grew during read")
            after = os_fstat(fd)
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                st.st_dev,
                st.st_ino,
                st.st_size,
                st.st_mtime_ns,
                st.st_ctime_ns,
            ):
                fail("retained file generation changed during read")
            return b"".join(chunks)
        finally:
            os_close(fd)

    def read_packet(path_value):
        value = loads_strict(read_file(path_value))
        normalize_packet(value)
        return value

    def read_diagnostic(path_value):
        value = loads_strict(read_file(path_value))
        if type(value) is not dict:
            fail("diagnostic file must contain an object")
        return value

    return (
        loads_strict,
        canonical,
        normalize_packet,
        compile_at,
        compile_current,
        verify_artifact,
        verify_current,
        read_packet,
        read_diagnostic,
    )


(
    loads_strict,
    canonical_json,
    _normalize_packet,
    _compile_at_for_test,
    compile_current,
    verify_artifact,
    verify_current,
    _read_packet,
    _read_diagnostic,
) = _build_api()


def _build_cli(*, read_packet=_read_packet, read_diagnostic=_read_diagnostic, compile_fn=compile_current, verify_fn=verify_current, canonical=canonical_json):
    parser_cls = _argparse.ArgumentParser
    stdout_buffer = _sys.stdout.buffer
    error_cls = AdoptionGateError
    os_error_cls = OSError

    def main(argv: list[str] | None = None) -> int:
        parser = parser_cls(description="Offline retained-evidence gate for Muse atomic runtime adoption")
        sub = parser.add_subparsers(dest="command", required=True)
        p_compile = sub.add_parser("compile", help="compile a CURRENT diagnostic from retained transcript evidence")
        p_compile.add_argument("--input", required=True)
        p_verify = sub.add_parser("verify", help="authenticate a diagnostic and recheck its CURRENT status")
        p_verify.add_argument("--input", required=True)
        p_verify.add_argument("--diagnostic", required=True)
        args = parser.parse_args(argv)
        try:
            packet = read_packet(args.input)
            if args.command == "compile":
                result = compile_fn(packet)
                return 0 if result["status"] == "ATOMIC_SEQUENCE_OBSERVED" else 3
            result = verify_fn(packet, read_diagnostic(args.diagnostic))
            return 0 if (
                result["valid"] and result["current_status"] == "ATOMIC_SEQUENCE_OBSERVED"
            ) else 3
        except (error_cls, os_error_cls):
            return 2

    return main


main = _build_cli()


if __name__ == "__main__":
    raise SystemExit(main())
