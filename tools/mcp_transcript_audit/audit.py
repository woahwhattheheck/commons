from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections import Counter
from typing import Any

SCHEMA = "commons-mcp-transcript-audit/v1"
VERIFY_SCHEMA = "commons-mcp-transcript-audit-verification/v1"
CAPTURE_SCHEMA = "commons-mcp-transcript-capture/v1"
REQUIRED_PROTOCOL_VERSION = "2025-11-25"
MAX_CAPTURE_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_EVENTS = 10_000

CLIENT = "client_to_server"
SERVER = "server_to_client"
DIRECTIONS = {CLIENT, SERVER}


class StrictJSONError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite JSON constant: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictJSONError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(str(exc)) from exc


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _typed_id_key(value: Any) -> tuple[str, Any]:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("request id must be a string or integer, not bool/null/float")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > 256:
            raise ValueError("request id string exceeds 256 UTF-8 bytes")
        return ("string", value)
    if len(str(value)) > 128:
        raise ValueError("request id integer exceeds 128 digits/sign characters")
    return ("integer", value)


def _id_hash(value: Any) -> str:
    kind, exact = _typed_id_key(value)
    return _sha256(_canonical_bytes({"type": kind, "value": exact}))


def _opposite(direction: str) -> str:
    return SERVER if direction == CLIENT else CLIENT


def _safe_reason(code: str, line: int | None = None) -> dict[str, Any]:
    reason: dict[str, Any] = {"code": code}
    if line is not None:
        reason["line"] = line
    return reason


def _validate_error_object(error: Any) -> None:
    if not isinstance(error, dict):
        raise ValueError("error must be an object")
    allowed = {"code", "message", "data"}
    if not set(error).issubset(allowed) or "code" not in error or "message" not in error:
        raise ValueError("error object has invalid keys")
    if isinstance(error["code"], bool) or not isinstance(error["code"], int):
        raise ValueError("error.code must be an integer")
    if not isinstance(error["message"], str):
        raise ValueError("error.message must be a string")


def _classify_message(message: Any) -> tuple[str, str | None, Any | None]:
    if not isinstance(message, dict):
        raise ValueError("JSON-RPC payload must be an object")
    if message.get("jsonrpc") != "2.0":
        raise ValueError("jsonrpc must equal '2.0'")

    keys = set(message)
    has_method = "method" in message
    has_id = "id" in message
    has_result = "result" in message
    has_error = "error" in message

    if has_method:
        allowed = {"jsonrpc", "id", "method", "params"}
        if not keys.issubset(allowed):
            raise ValueError("request/notification contains unknown top-level keys")
        method = message["method"]
        if not isinstance(method, str) or not method:
            raise ValueError("method must be a non-empty string")
        if "params" in message and not isinstance(message["params"], (dict, list)):
            raise ValueError("params must be an object or array when present")
        if has_id:
            _typed_id_key(message["id"])
            return "request", method, message["id"]
        return "notification", method, None

    allowed = {"jsonrpc", "id", "result", "error"}
    if not keys.issubset(allowed):
        raise ValueError("response contains unknown top-level keys")
    if not has_id:
        raise ValueError("response must contain id")
    _typed_id_key(message["id"])
    if has_result == has_error:
        raise ValueError("response must contain exactly one of result or error")
    if has_error:
        _validate_error_object(message["error"])
    return "response", None, message["id"]


def _decode_capture_line(raw_line: bytes, line_number: int) -> tuple[str, bytes, dict[str, Any]]:
    if len(raw_line) > MAX_LINE_BYTES:
        raise ValueError("capture line exceeds size limit")
    try:
        line_text = raw_line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("capture line is not valid UTF-8") from exc
    envelope = strict_json_loads(line_text)
    if not isinstance(envelope, dict) or set(envelope) != {"direction", "payload_base64"}:
        raise ValueError("capture line must contain exactly direction and payload_base64")
    direction = envelope["direction"]
    if direction not in DIRECTIONS:
        raise ValueError("direction must be client_to_server or server_to_client")
    encoded = envelope["payload_base64"]
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("payload_base64 must be a non-empty string")
    try:
        payload = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ValueError("payload_base64 is not canonical base64 data") from exc
    if not payload or len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("decoded payload is empty or exceeds size limit")
    try:
        payload_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("decoded JSON-RPC payload is not valid UTF-8") from exc
    message = strict_json_loads(payload_text)
    return direction, payload, message


def _validate_initialize_request(message: dict[str, Any]) -> str:
    params = message.get("params")
    if not isinstance(params, dict):
        raise ValueError("initialize params must be an object")
    required = {"protocolVersion", "capabilities", "clientInfo"}
    if not required.issubset(params):
        raise ValueError("initialize params missing protocolVersion/capabilities/clientInfo")
    protocol = params["protocolVersion"]
    if not isinstance(protocol, str) or not protocol:
        raise ValueError("initialize protocolVersion must be a non-empty string")
    if not isinstance(params["capabilities"], dict):
        raise ValueError("initialize capabilities must be an object")
    if not isinstance(params["clientInfo"], dict):
        raise ValueError("initialize clientInfo must be an object")
    return protocol


def _validate_initialize_result(message: dict[str, Any]) -> str:
    result = message.get("result")
    if not isinstance(result, dict):
        raise ValueError("initialize response must be a success result object")
    required = {"protocolVersion", "capabilities", "serverInfo"}
    if not required.issubset(result):
        raise ValueError("initialize result missing protocolVersion/capabilities/serverInfo")
    protocol = result["protocolVersion"]
    if not isinstance(protocol, str) or not protocol:
        raise ValueError("initialize result protocolVersion must be a non-empty string")
    if not isinstance(result["capabilities"], dict):
        raise ValueError("initialize result capabilities must be an object")
    if not isinstance(result["serverInfo"], dict):
        raise ValueError("initialize result serverInfo must be an object")
    return protocol


def _receipt_with_hash(receipt: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    out = dict(unsigned)
    out["receipt_sha256"] = _sha256(_canonical_bytes(unsigned))
    return out


def audit_transcript(
    source: bytes,
    *,
    required_protocol_version: str = REQUIRED_PROTOCOL_VERSION,
) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    method_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    seen_request_ids: set[tuple[str, tuple[str, Any]]] = set()
    pending: dict[tuple[str, tuple[str, Any]], dict[str, Any]] = {}
    completed: set[tuple[str, tuple[str, Any]]] = set()

    init_request_key: tuple[str, tuple[str, Any]] | None = None
    init_request_line: int | None = None
    init_response_line: int | None = None
    init_requested_version: str | None = None
    init_negotiated_version: str | None = None
    initialized_line: int | None = None
    initialized = False

    if not isinstance(source, bytes):
        raise TypeError("source must be bytes")
    if not isinstance(required_protocol_version, str) or not required_protocol_version:
        raise ValueError("required_protocol_version must be a non-empty string")

    if len(source) > MAX_CAPTURE_BYTES:
        reasons.append(_safe_reason("CAPTURE_TOO_LARGE"))
    if b"\x00" in source:
        reasons.append(_safe_reason("NUL_BYTE_IN_CAPTURE"))

    raw_lines = source.splitlines()
    nonempty = [(i + 1, line) for i, line in enumerate(raw_lines) if line.strip()]
    if not nonempty:
        reasons.append(_safe_reason("EMPTY_CAPTURE"))
    if len(nonempty) > MAX_EVENTS:
        reasons.append(_safe_reason("TOO_MANY_EVENTS"))

    stop_semantic_processing = bool(reasons)

    for event_index, (line_number, raw_line) in enumerate(nonempty, start=1):
        if event_index > MAX_EVENTS:
            break
        line_row: dict[str, Any] = {
            "line": line_number,
            "capture_line_sha256": _sha256(raw_line),
            "capture_line_bytes": len(raw_line),
        }
        if stop_semantic_processing:
            evidence.append(line_row)
            continue
        try:
            direction, payload, message = _decode_capture_line(raw_line, line_number)
            kind, method, request_id = _classify_message(message)
        except (ValueError, StrictJSONError) as exc:
            code = "INVALID_CAPTURE_EVENT"
            text = str(exc)
            if "duplicate JSON key" in text:
                code = "DUPLICATE_JSON_KEY"
            elif "non-finite JSON constant" in text:
                code = "NONFINITE_JSON"
            elif "UTF-8" in text:
                code = "INVALID_UTF8"
            elif "size limit" in text:
                code = "EVENT_TOO_LARGE"
            reasons.append(_safe_reason(code, line_number))
            evidence.append(line_row)
            stop_semantic_processing = True
            continue

        line_row.update(
            {
                "direction": direction,
                "payload_sha256": _sha256(payload),
                "payload_bytes": len(payload),
                "kind": kind,
            }
        )
        direction_counts[direction] += 1
        kind_counts[kind] += 1
        if method is not None:
            line_row["method"] = method
            method_counts[method] += 1
        if request_id is not None:
            line_row["request_id_sha256"] = _id_hash(request_id)
        evidence.append(line_row)

        # The spec requires initialization to be the first interaction.
        if event_index == 1:
            if not (direction == CLIENT and kind == "request" and method == "initialize"):
                reasons.append(_safe_reason("INITIALIZE_NOT_FIRST_INTERACTION", line_number))
            else:
                try:
                    init_requested_version = _validate_initialize_request(message)
                except ValueError:
                    reasons.append(_safe_reason("INVALID_INITIALIZE_REQUEST", line_number))
                if init_requested_version != required_protocol_version:
                    reasons.append(_safe_reason("REQUIRED_PROTOCOL_VERSION_NOT_REQUESTED", line_number))

        if kind == "request":
            assert request_id is not None
            key = (direction, _typed_id_key(request_id))
            if key in seen_request_ids:
                reasons.append(_safe_reason("REQUEST_ID_REUSED", line_number))
            else:
                seen_request_ids.add(key)
                pending[key] = {"line": line_number, "method": method}

            if method == "initialize":
                if direction != CLIENT or init_request_key is not None or event_index != 1:
                    reasons.append(_safe_reason("INVALID_INITIALIZE_REQUEST_POSITION", line_number))
                else:
                    init_request_key = key
                    init_request_line = line_number
            elif not initialized:
                # 2025-11-25 allows ping as the sole pre-init-response request exception.
                if method != "ping":
                    reasons.append(_safe_reason("REQUEST_BEFORE_INITIALIZED", line_number))

        elif kind == "notification":
            if method == "notifications/initialized":
                if direction != CLIENT:
                    reasons.append(_safe_reason("INITIALIZED_NOTIFICATION_WRONG_DIRECTION", line_number))
                if initialized_line is not None:
                    reasons.append(_safe_reason("INITIALIZED_NOTIFICATION_DUPLICATE", line_number))
                if init_response_line is None:
                    reasons.append(_safe_reason("INITIALIZED_BEFORE_INITIALIZE_RESPONSE", line_number))
                if direction == CLIENT and init_response_line is not None and initialized_line is None:
                    initialized_line = line_number
                    initialized = True
            elif not initialized:
                # Server logging is the spec's pre-initialized notification exception.
                if not (direction == SERVER and method == "notifications/message"):
                    reasons.append(_safe_reason("NOTIFICATION_BEFORE_INITIALIZED", line_number))

        else:  # response
            assert request_id is not None
            request_key = (_opposite(direction), _typed_id_key(request_id))
            prior = pending.pop(request_key, None)
            if prior is None:
                if request_key in completed:
                    reasons.append(_safe_reason("DUPLICATE_RESPONSE", line_number))
                else:
                    reasons.append(_safe_reason("ORPHAN_RESPONSE", line_number))
            else:
                completed.add(request_key)
                line_row["response_to_method"] = prior["method"]
                if init_request_key == request_key:
                    if direction != SERVER:
                        reasons.append(_safe_reason("INITIALIZE_RESPONSE_WRONG_DIRECTION", line_number))
                    if init_response_line is not None:
                        reasons.append(_safe_reason("INITIALIZE_RESPONSE_DUPLICATE", line_number))
                    else:
                        init_response_line = line_number
                        try:
                            init_negotiated_version = _validate_initialize_result(message)
                        except ValueError:
                            reasons.append(_safe_reason("INVALID_INITIALIZE_RESPONSE", line_number))
                        if init_negotiated_version != required_protocol_version:
                            reasons.append(_safe_reason("REQUIRED_PROTOCOL_VERSION_NOT_NEGOTIATED", line_number))
                        if (
                            init_requested_version is not None
                            and init_negotiated_version is not None
                            and init_requested_version != init_negotiated_version
                        ):
                            reasons.append(_safe_reason("PROTOCOL_VERSION_MISMATCH", line_number))
                elif not initialized:
                    request_method = prior["method"]
                    if request_method != "ping":
                        reasons.append(_safe_reason("RESPONSE_BEFORE_INITIALIZED", line_number))

    if not stop_semantic_processing:
        if init_request_line is None:
            reasons.append(_safe_reason("INITIALIZE_REQUEST_MISSING"))
        if init_response_line is None:
            reasons.append(_safe_reason("INITIALIZE_RESPONSE_MISSING"))
        if initialized_line is None:
            reasons.append(_safe_reason("INITIALIZED_NOTIFICATION_MISSING"))
        if pending:
            reasons.append(_safe_reason("UNRESOLVED_REQUESTS"))

    # Stable reason set/order. Do not expose parser exception text or payload content.
    reasons = sorted(
        {json.dumps(r, sort_keys=True, separators=(",", ":")): r for r in reasons}.values(),
        key=lambda r: (r.get("line", 0), r["code"]),
    )

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS" if not reasons else "HOLD",
        "required_protocol_version": required_protocol_version,
        "negotiated_protocol_version": init_negotiated_version,
        "source_sha256": _sha256(source),
        "source_bytes": len(source),
        "event_count": len(nonempty),
        "counts": {
            "client_to_server": direction_counts[CLIENT],
            "server_to_client": direction_counts[SERVER],
            "requests": kind_counts["request"],
            "responses": kind_counts["response"],
            "notifications": kind_counts["notification"],
        },
        "lifecycle": {
            "initialize_request_line": init_request_line,
            "initialize_response_line": init_response_line,
            "initialized_notification_line": initialized_line,
        },
        "method_counts": dict(sorted(method_counts.items())),
        "evidence": evidence,
        "reasons": reasons,
        "authority": {
            "network_access": False,
            "tool_execution": False,
            "server_mutation": False,
            "external_action": False,
        },
    }
    return _receipt_with_hash(receipt)


def verify_receipt(
    source: bytes,
    receipt_bytes: bytes,
    *,
    required_protocol_version: str = REQUIRED_PROTOCOL_VERSION,
) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        receipt_text = receipt_bytes.decode("utf-8")
        supplied = strict_json_loads(receipt_text)
    except (UnicodeDecodeError, StrictJSONError):
        supplied = None
        reasons.append("INVALID_RECEIPT_JSON")

    if not isinstance(supplied, dict):
        if "INVALID_RECEIPT_JSON" not in reasons:
            reasons.append("RECEIPT_MUST_BE_OBJECT")
    else:
        supplied_sha = supplied.get("receipt_sha256")
        unsigned = dict(supplied)
        unsigned.pop("receipt_sha256", None)
        if not isinstance(supplied_sha, str) or supplied_sha != _sha256(_canonical_bytes(unsigned)):
            reasons.append("RECEIPT_SELF_HASH_MISMATCH")
        if supplied.get("schema") != SCHEMA:
            reasons.append("RECEIPT_SCHEMA_MISMATCH")
        recomputed = audit_transcript(source, required_protocol_version=required_protocol_version)
        if _canonical_bytes(supplied) != _canonical_bytes(recomputed):
            reasons.append("RECEIPT_RECOMPUTE_MISMATCH")

    reasons = sorted(set(reasons))
    verification: dict[str, Any] = {
        "schema": VERIFY_SCHEMA,
        "valid": not reasons,
        "source_sha256": _sha256(source),
        "receipt_file_sha256": _sha256(receipt_bytes),
        "reasons": reasons,
        "authority": {
            "network_access": False,
            "tool_execution": False,
            "server_mutation": False,
            "external_action": False,
        },
    }
    unsigned_verification = dict(verification)
    verification["verification_sha256"] = _sha256(_canonical_bytes(unsigned_verification))
    return verification


def encode_capture_event(direction: str, message: dict[str, Any]) -> bytes:
    """Helper for deterministic fixtures/recorders; not required by the auditor."""
    if direction not in DIRECTIONS:
        raise ValueError("invalid direction")
    payload = _canonical_bytes(message)
    envelope = {
        "direction": direction,
        "payload_base64": base64.b64encode(payload).decode("ascii"),
    }
    return _canonical_bytes(envelope)


def canonical_json_bytes(value: Any) -> bytes:
    """Public helper for callers that need byte-stable receipt serialization."""
    return _canonical_bytes(value)
