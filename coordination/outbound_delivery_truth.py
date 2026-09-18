#!/usr/bin/env python3
"""Deterministic, offline outbound delivery truth compiler.

Provider submission is transport evidence, not proof of delivery. This module
binds retained provider-submission and structured DSN evidence to one immutable
outbound descriptor and emits a conservative transport state plus a projection
for collision/contact ledgers.

It never sends, retries, selects another route, authenticates a provider, or
establishes buyer/payment/revenue truth. Hashes bind retained bytes and replay;
they do not independently prove that a provider/source is genuine.

Threat model: hostile retained data inside a trusted Python interpreter. Direct
mutation of live function code/closure cells/process memory is outside scope.
"""
from __future__ import annotations

import argparse as _argparse
import hashlib as _hashlib
import json as _json
import os as _os
import re as _re
import stat as _stat
import sys as _sys
import unicodedata as _unicodedata
from datetime import datetime as _datetime, timezone as _timezone
from pathlib import Path as _Path
from typing import Any as _Any

_INPUT_SCHEMA = "commons.outbound-delivery-evidence/v1"
_OUTPUT_SCHEMA = "commons.outbound-delivery-truth/v1"
_VERIFY_SCHEMA = "commons.outbound-delivery-verification/v1"
_MAX_INPUT_BYTES = 1_048_576
_MAX_TEXT = 1024
_MAX_EVENTS = 64
_MAX_DEPTH = 18
_MAX_INT = 2**53 - 1
_HEX64_RE = _re.compile(r"^[0-9a-f]{64}$")
_TIMESTAMP_RE = _re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SMTP_RE = _re.compile(r"^[245]\d\d$")
_ENHANCED_RE = _re.compile(r"^[245]\.\d{1,3}\.\d{1,3}$")
_STATES = frozenset({
    "UNSENT",
    "PROVIDER_SUBMITTED_PENDING_DELIVERY",
    "DELIVERED_EVIDENCE",
    "DELIVERY_FAILED",
    "DELIVERY_UNKNOWN",
})
_DSN_ACTIONS = frozenset({"delivered", "delayed", "failed"})
_AUTHORITY = {
    "send_authorized": False,
    "retry_authorized": False,
    "alternate_route_authorized": False,
    "provider_action_authorized": False,
    "buyer_acceptance": False,
    "contract_signed": False,
    "payment_authorized": False,
    "cash_proven": False,
    "receivable_asserted": False,
    "revenue_recognized": False,
}


class DeliveryTruthError(ValueError):
    """Stable domain error for malformed, unbound, or replayed evidence."""


def _build_api():
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    verify_schema = _VERIFY_SCHEMA
    states = frozenset(_STATES)
    dsn_actions = frozenset(_DSN_ACTIONS)
    authority_items = tuple(sorted(_AUTHORITY.items()))
    max_input_bytes = _MAX_INPUT_BYTES
    max_text = _MAX_TEXT
    max_events = _MAX_EVENTS
    max_depth = _MAX_DEPTH
    max_int = _MAX_INT
    error_cls = DeliveryTruthError
    sha256_ctor = _hashlib.sha256
    normalize_unicode = _unicodedata.normalize
    unicode_category = _unicodedata.category
    dt_cls = _datetime
    utc = _timezone.utc
    hex64_fullmatch = _HEX64_RE.fullmatch
    timestamp_fullmatch = _TIMESTAMP_RE.fullmatch
    smtp_fullmatch = _SMTP_RE.fullmatch
    enhanced_fullmatch = _ENHANCED_RE.fullmatch
    json_decoder_cls = _json.JSONDecoder
    quote_json = _json.encoder.encode_basestring
    path_cls = _Path
    os_open = _os.open
    os_read = _os.read
    os_fstat = _os.fstat
    os_close = _os.close
    s_isreg = _stat.S_ISREG
    flags = _os.O_RDONLY | getattr(_os, "O_CLOEXEC", 0) | getattr(_os, "O_NOFOLLOW", 0)

    def fail(message: str) -> None:
        raise error_cls(message)

    def bounded_int(token: str) -> int:
        if len(token) > 16:
            fail("integer token exceeds bounded length")
        try:
            value = int(token, 10)
        except ValueError as exc:
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
        parse_int=bounded_int,
        parse_float=reject_float,
        parse_constant=reject_constant,
        strict=True,
    )
    raw_decode = decoder.raw_decode

    def walk_plain(value: _Any, depth: int = 0) -> None:
        if depth > max_depth:
            fail("JSON nesting exceeds limit")
        if value is None or type(value) in (bool, int, str):
            if type(value) is int and not (-max_int <= value <= max_int):
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
        fail("JSON must contain exact built-in plain values")

    def loads_strict(data: str | bytes) -> _Any:
        if type(data) is bytes:
            if len(data) > max_input_bytes:
                fail("input exceeds byte limit")
            try:
                text_value = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise error_cls("input must be UTF-8") from exc
        elif type(data) is str:
            if len(data.encode("utf-8")) > max_input_bytes:
                fail("input exceeds byte limit")
            text_value = data
        else:
            fail("JSON input must be str or bytes")
        stripped = text_value.lstrip()
        try:
            value, end = raw_decode(stripped)
        except (ValueError, RecursionError) as exc:
            raise error_cls("invalid JSON") from exc
        if stripped[end:].strip():
            fail("trailing JSON data is not admitted")
        walk_plain(value)
        return value

    def canonical(value: _Any) -> bytes:
        walk_plain(value)

        def emit(item: _Any) -> str:
            if item is None:
                return "null"
            if item is True:
                return "true"
            if item is False:
                return "false"
            if type(item) is int:
                return str(item)
            if type(item) is str:
                return quote_json(item)
            if type(item) is list:
                return "[" + ",".join(emit(v) for v in item) + "]"
            if type(item) is dict:
                return "{" + ",".join(
                    quote_json(key) + ":" + emit(item[key]) for key in sorted(item)
                ) + "}"
            fail("value is not canonical JSON")
        try:
            return emit(value).encode("utf-8")
        except UnicodeEncodeError as exc:
            raise error_cls("value is not UTF-8 encodable") from exc

    def digest(value: _Any) -> str:
        return sha256_ctor(canonical(value)).hexdigest()

    def text(value: _Any, name: str, maximum: int = max_text) -> str:
        if type(value) is not str or not value or len(value) > maximum:
            fail(f"{name} must be non-empty text <= {maximum} chars")
        if value != value.strip():
            fail(f"{name} must not have leading/trailing whitespace")
        if normalize_unicode("NFC", value) != value:
            fail(f"{name} must use NFC-normalized Unicode")
        visible = False
        for ch in value:
            category = unicode_category(ch)
            if category.startswith("C"):
                fail(f"{name} contains a control/format/surrogate codepoint")
            if not ch.isspace() and not category.startswith("M"):
                visible = True
        if not visible:
            fail(f"{name} must contain a visible base character")
        return value

    def sha(value: _Any, name: str) -> str:
        value = text(value, name, 64)
        if hex64_fullmatch(value) is None:
            fail(f"{name} must be lowercase SHA-256 hex")
        return value

    def timestamp(value: _Any, name: str) -> tuple[str, int]:
        value = text(value, name, 20)
        if timestamp_fullmatch(value) is None:
            fail(f"{name} must be canonical UTC second timestamp")
        try:
            parsed = dt_cls(
                int(value[0:4]), int(value[5:7]), int(value[8:10]),
                int(value[11:13]), int(value[14:16]), int(value[17:19]), tzinfo=utc,
            )
        except ValueError as exc:
            raise error_cls(f"{name} is not a real UTC timestamp") from exc
        if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
            fail(f"{name} must be canonical UTC second timestamp")
        return value, int(parsed.timestamp())

    def exact_keys(value: _Any, name: str, required: set[str], optional: set[str] | None = None) -> dict:
        if type(value) is not dict:
            fail(f"{name} must be an object")
        optional = optional or set()
        missing = required - set(value)
        extra = set(value) - (required | optional)
        if missing:
            fail(f"{name} missing fields: {sorted(missing)}")
        if extra:
            fail(f"{name} has unexpected fields: {sorted(extra)}")
        return value

    def source_binding(value: _Any, name: str) -> dict[str, str]:
        value = exact_keys(value, name, {"source_ref", "source_sha256"})
        return {
            "source_ref": text(value["source_ref"], f"{name}.source_ref"),
            "source_sha256": sha(value["source_sha256"], f"{name}.source_sha256"),
        }

    def normalize_outbound(value: _Any) -> dict[str, str]:
        required = {
            "operation_key", "organization_id", "counterparty", "route", "purpose",
            "provider", "subject_sha256", "body_sha256",
        }
        value = exact_keys(value, "outbound", required)
        return {
            "operation_key": text(value["operation_key"], "outbound.operation_key", 240),
            "organization_id": text(value["organization_id"], "outbound.organization_id", 240),
            "counterparty": text(value["counterparty"], "outbound.counterparty"),
            "route": text(value["route"], "outbound.route"),
            "purpose": text(value["purpose"], "outbound.purpose"),
            "provider": text(value["provider"], "outbound.provider", 120).casefold(),
            "subject_sha256": sha(value["subject_sha256"], "outbound.subject_sha256"),
            "body_sha256": sha(value["body_sha256"], "outbound.body_sha256"),
        }

    def normalize_submission(value: _Any, out: dict[str, str], name: str) -> dict:
        required = {
            "provider", "provider_message_id", "provider_thread_id", "recipient",
            "submitted_at", "source",
        }
        value = exact_keys(value, name, required)
        submitted_at, submitted_s = timestamp(value["submitted_at"], f"{name}.submitted_at")
        row = {
            "provider": text(value["provider"], f"{name}.provider", 120).casefold(),
            "provider_message_id": text(value["provider_message_id"], f"{name}.provider_message_id", 512),
            "provider_thread_id": text(value["provider_thread_id"], f"{name}.provider_thread_id", 512),
            "recipient": text(value["recipient"], f"{name}.recipient"),
            "submitted_at": submitted_at,
            "source": source_binding(value["source"], f"{name}.source"),
            "_submitted_s": submitted_s,
        }
        if row["provider"] != out["provider"]:
            fail(f"{name} provider does not bind outbound descriptor")
        if row["recipient"].casefold() != out["route"].casefold():
            fail(f"{name} recipient does not bind outbound route")
        return row

    def normalize_event(value: _Any, sub: dict, out: dict, index: int) -> dict:
        name = f"delivery_events[{index}]"
        required = {
            "event_id", "kind", "provider", "provider_message_id", "provider_thread_id",
            "recipient", "observed_at", "source", "dsn",
        }
        value = exact_keys(value, name, required)
        kind = text(value["kind"], f"{name}.kind", 64)
        if kind != "DSN":
            fail(f"{name}.kind must be DSN")
        observed_at, observed_s = timestamp(value["observed_at"], f"{name}.observed_at")
        row = {
            "event_id": text(value["event_id"], f"{name}.event_id", 240),
            "kind": kind,
            "provider": text(value["provider"], f"{name}.provider", 120).casefold(),
            "provider_message_id": text(value["provider_message_id"], f"{name}.provider_message_id", 512),
            "provider_thread_id": text(value["provider_thread_id"], f"{name}.provider_thread_id", 512),
            "recipient": text(value["recipient"], f"{name}.recipient"),
            "observed_at": observed_at,
            "source": source_binding(value["source"], f"{name}.source"),
            "_observed_s": observed_s,
        }
        if row["provider"] != sub["provider"] or row["provider"] != out["provider"]:
            fail(f"{name} provider binding mismatch")
        if row["provider_message_id"] != sub["provider_message_id"]:
            fail(f"{name} message binding mismatch")
        if row["provider_thread_id"] != sub["provider_thread_id"]:
            fail(f"{name} thread binding mismatch")
        if row["recipient"].casefold() != sub["recipient"].casefold() or row["recipient"].casefold() != out["route"].casefold():
            fail(f"{name} recipient binding mismatch")
        if observed_s < sub["_submitted_s"]:
            fail(f"{name} predates provider submission")

        dsn = exact_keys(
            value["dsn"], f"{name}.dsn",
            {"action", "smtp_status", "enhanced_status", "final_recipient", "original_message_id"},
            {"diagnostic_code"},
        )
        action = text(dsn["action"], f"{name}.dsn.action", 32).casefold()
        if action not in dsn_actions:
            fail(f"{name}.dsn.action is unsupported")
        smtp_status = text(dsn["smtp_status"], f"{name}.dsn.smtp_status", 3)
        enhanced_status = text(dsn["enhanced_status"], f"{name}.dsn.enhanced_status", 16)
        if smtp_fullmatch(smtp_status) is None:
            fail(f"{name}.dsn.smtp_status must be a 2xx/4xx/5xx code")
        if enhanced_fullmatch(enhanced_status) is None:
            fail(f"{name}.dsn.enhanced_status must be an enhanced status code")
        final_recipient = text(dsn["final_recipient"], f"{name}.dsn.final_recipient")
        original_message_id = text(dsn["original_message_id"], f"{name}.dsn.original_message_id", 512)
        if final_recipient.casefold() != out["route"].casefold():
            fail(f"{name}.dsn final recipient does not bind outbound route")
        if original_message_id != sub["provider_message_id"]:
            fail(f"{name}.dsn original message does not bind submission")
        major = smtp_status[0]
        if major != enhanced_status[0]:
            fail(f"{name}.dsn SMTP/enhanced status classes conflict")
        expected_major = {"failed": "5", "delayed": "4", "delivered": "2"}[action]
        if major != expected_major:
            fail(f"{name}.dsn action/status class conflict")
        diag = dsn.get("diagnostic_code")
        if diag is not None:
            diag = text(diag, f"{name}.dsn.diagnostic_code", 2048)
        row["dsn"] = {
            "action": action,
            "smtp_status": smtp_status,
            "enhanced_status": enhanced_status,
            "final_recipient": final_recipient,
            "original_message_id": original_message_id,
            "diagnostic_code": diag,
        }
        return row

    def strip_private(row):
        if row is None:
            return None
        return {k: v for k, v in row.items() if not k.startswith("_")}

    def normalize(packet: _Any) -> dict:
        packet = exact_keys(
            packet, "packet",
            {"schema", "outbound", "outbound_descriptor_sha256", "submission", "legacy_local_sent", "delivery_events"},
        )
        if packet["schema"] != input_schema:
            fail("input schema mismatch")
        out = normalize_outbound(packet["outbound"])
        out_digest = digest(out)
        supplied_digest = sha(packet["outbound_descriptor_sha256"], "outbound_descriptor_sha256")
        if supplied_digest != out_digest:
            fail("outbound descriptor digest mismatch")

        raw_submission = packet["submission"]
        raw_legacy = packet["legacy_local_sent"]
        if raw_submission is not None and raw_legacy is not None:
            fail("submission and legacy_local_sent are mutually exclusive")
        sub = normalize_submission(raw_submission, out, "submission") if raw_submission is not None else None
        legacy = normalize_submission(raw_legacy, out, "legacy_local_sent") if raw_legacy is not None else None

        events_raw = packet["delivery_events"]
        if type(events_raw) is not list or len(events_raw) > max_events:
            fail("delivery_events must be a bounded array")
        if events_raw and sub is None:
            fail("delivery evidence requires a provider submission receipt")
        events = [normalize_event(item, sub, out, i) for i, item in enumerate(events_raw)] if sub is not None else []

        seen_ids = set()
        seen_source_sha = set()
        seen_semantics = set()
        previous_s = None
        for item in events:
            if item["event_id"] in seen_ids:
                fail("duplicate delivery event id")
            seen_ids.add(item["event_id"])
            source_sha = item["source"]["source_sha256"]
            if source_sha in seen_source_sha:
                fail("duplicate/reminted delivery source generation")
            seen_source_sha.add(source_sha)
            semantic = digest({
                "kind": item["kind"],
                "provider": item["provider"],
                "provider_message_id": item["provider_message_id"],
                "provider_thread_id": item["provider_thread_id"],
                "recipient": item["recipient"].casefold(),
                "dsn": item["dsn"],
            })
            if semantic in seen_semantics:
                fail("duplicate/reminted delivery semantics")
            seen_semantics.add(semantic)
            if previous_s is not None and item["_observed_s"] < previous_s:
                fail("delivery events must be in nondecreasing observation order")
            previous_s = item["_observed_s"]

        return {
            "schema": input_schema,
            "outbound": out,
            "outbound_descriptor_sha256": out_digest,
            "submission": strip_private(sub),
            "legacy_local_sent": strip_private(legacy),
            "delivery_events": [strip_private(item) for item in events],
            "_submission_with_time": sub,
            "_legacy_with_time": legacy,
        }

    def classify(normalized: dict) -> tuple[str, list[str]]:
        sub = normalized["_submission_with_time"]
        legacy = normalized["_legacy_with_time"]
        events = normalized["delivery_events"]
        if sub is None and legacy is None:
            return "UNSENT", ["no provider submission evidence"]
        if sub is None and legacy is not None:
            return "DELIVERY_UNKNOWN", ["historical local-SENT is not delivery evidence"]
        if not events:
            return "PROVIDER_SUBMITTED_PENDING_DELIVERY", ["provider submission observed; no delivery evidence retained"]
        terminal = {row["dsn"]["action"] for row in events if row["dsn"]["action"] in {"delivered", "failed"}}
        if terminal == {"delivered", "failed"}:
            return "DELIVERY_UNKNOWN", ["conflicting terminal delivery evidence"]
        if "failed" in terminal:
            return "DELIVERY_FAILED", ["structured hard DSN bound to exact submission"]
        if "delivered" in terminal:
            return "DELIVERED_EVIDENCE", ["structured delivered DSN bound to exact submission"]
        return "DELIVERY_UNKNOWN", ["only transient/ambiguous DSN evidence retained"]

    def projection(state: str, normalized: dict) -> dict:
        if state not in states:
            fail("internal state error")
        submission_seen = normalized["_submission_with_time"] is not None or normalized["_legacy_with_time"] is not None
        if state == "DELIVERY_FAILED":
            route_viability, contact_state = "DEAD_ROUTE", "DEAD_ROUTE_NOT_CONTACTED"
        elif state == "DELIVERED_EVIDENCE":
            route_viability, contact_state = "DELIVERED_ROUTE", "DELIVERED_CONTACT"
        elif state == "UNSENT":
            route_viability, contact_state = "UNTRIED_ROUTE", "NO_CONTACT_ATTEMPT"
        else:
            route_viability, contact_state = "UNKNOWN_ROUTE", "UNCONFIRMED_CONTACT"
        return {
            "provider_submission_seen": submission_seen,
            "route_viability": route_viability,
            "organization_contact_state": contact_state,
            "organization_contacted_from_this_generation": state == "DELIVERED_EVIDENCE",
            "successful_contact_count_delta": 1 if state == "DELIVERED_EVIDENCE" else 0,
            "revenue_activity_count_delta": 0,
            "treat_as_delivered_for_collision_history": state == "DELIVERED_EVIDENCE",
            "same_route_delivery_failed": state == "DELIVERY_FAILED",
            "alternate_route_contact_authorized": False,
        }

    def compile_packet(packet: _Any) -> dict:
        normalized = normalize(packet)
        state, reasons = classify(normalized)
        clean_input = {
            "schema": normalized["schema"],
            "outbound": normalized["outbound"],
            "outbound_descriptor_sha256": normalized["outbound_descriptor_sha256"],
            "submission": normalized["submission"],
            "legacy_local_sent": normalized["legacy_local_sent"],
            "delivery_events": normalized["delivery_events"],
        }
        report = {
            "schema": output_schema,
            "input_sha256": digest(clean_input),
            "outbound_descriptor_sha256": normalized["outbound_descriptor_sha256"],
            "state": state,
            "reasons": reasons,
            "transport": {
                "provider": normalized["outbound"]["provider"],
                "route": normalized["outbound"]["route"],
                "provider_message_id": (
                    normalized["submission"]["provider_message_id"] if normalized["submission"] is not None
                    else normalized["legacy_local_sent"]["provider_message_id"] if normalized["legacy_local_sent"] is not None
                    else None
                ),
                "provider_thread_id": (
                    normalized["submission"]["provider_thread_id"] if normalized["submission"] is not None
                    else normalized["legacy_local_sent"]["provider_thread_id"] if normalized["legacy_local_sent"] is not None
                    else None
                ),
                "delivery_event_count": len(normalized["delivery_events"]),
            },
            "collision_projection": projection(state, normalized),
            "evidence_claims": {
                "provider_submission_is_delivery_proof": False,
                "absence_of_dsn_is_delivery_proof": False,
                "retained_hashes_authenticate_provider": False,
                "structured_delivery_evidence_observed": state == "DELIVERED_EVIDENCE",
                "structured_hard_failure_observed": state == "DELIVERY_FAILED",
            },
            "authority": dict(authority_items),
        }
        report["receipt_sha256"] = digest(report)
        return report

    def verify(packet: _Any, report: _Any) -> dict:
        if type(report) is not dict:
            fail("report must be an object")
        if report.get("schema") != output_schema:
            fail("report schema mismatch")
        supplied = dict(report)
        receipt = supplied.pop("receipt_sha256", None)
        if type(receipt) is not str or hex64_fullmatch(receipt) is None:
            return {"schema": verify_schema, "valid": False, "reason": "receipt_missing_or_invalid", "state": None, "authority": dict(authority_items)}
        if digest(supplied) != receipt:
            return {"schema": verify_schema, "valid": False, "reason": "receipt_mismatch", "state": None, "authority": dict(authority_items)}
        expected = compile_packet(packet)
        if canonical(expected) != canonical(report):
            return {"schema": verify_schema, "valid": False, "reason": "semantic_recompile_mismatch", "state": expected["state"], "authority": dict(authority_items)}
        return {"schema": verify_schema, "valid": True, "reason": "exact_recompile_match", "state": expected["state"], "authority": dict(authority_items)}

    def read_file(path_value) -> bytes:
        path = path_cls(path_value)
        fd = os_open(path, flags)
        try:
            st = os_fstat(fd)
            if not s_isreg(st.st_mode):
                fail("retained path must be a regular file")
            if st.st_size > max_input_bytes:
                fail("retained file exceeds byte limit")
            remaining = st.st_size
            chunks = []
            while remaining:
                chunk = os_read(fd, min(65536, remaining))
                if not chunk:
                    fail("retained file truncated during read")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os_read(fd, 1):
                fail("retained file grew during read")
            after = os_fstat(fd)
            before_id = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
            after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            if before_id != after_id:
                fail("retained file generation changed during read")
            return b"".join(chunks)
        finally:
            os_close(fd)

    def read_json(path_value):
        return loads_strict(read_file(path_value))

    return loads_strict, canonical, digest, compile_packet, verify, read_json


loads_strict, canonical_json, sha256_json, compile_packet, verify_report, _read_json = _build_api()


def _build_cli(*, read_json=_read_json, compile_fn=compile_packet, verify_fn=verify_report, canonical=canonical_json):
    parser_cls = _argparse.ArgumentParser
    stdout = _sys.stdout.buffer
    error_cls = DeliveryTruthError
    os_error_cls = OSError

    def main(argv: list[str] | None = None) -> int:
        parser = parser_cls(description="Offline DSN-aware outbound delivery truth compiler")
        sub = parser.add_subparsers(dest="command", required=True)
        p_compile = sub.add_parser("compile")
        p_compile.add_argument("--input", required=True)
        p_verify = sub.add_parser("verify")
        p_verify.add_argument("--input", required=True)
        p_verify.add_argument("--report", required=True)
        args = parser.parse_args(argv)
        try:
            packet = read_json(args.input)
            if args.command == "compile":
                stdout.write(canonical(compile_fn(packet)) + b"\n")
                return 0
            result = verify_fn(packet, read_json(args.report))
            stdout.write(canonical(result) + b"\n")
            return 0 if result["valid"] else 3
        except (error_cls, os_error_cls):
            return 2
    return main


main = _build_cli()


if __name__ == "__main__":
    raise SystemExit(main())
