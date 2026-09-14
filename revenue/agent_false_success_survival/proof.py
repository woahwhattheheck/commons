"""Deterministic agent false-success survival proof compiler.

This module consumes captured HTTP/MCP exchange evidence.  It never performs a
network request.  Raw response bodies stay in the input bundle; published proof
objects contain only content digests and bounded semantic indicators.
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

CAPTURE_SCHEMA = "agent-false-success-capture/v1"
PROOF_SCHEMA = "agent-false-success-proof/v1"
POLICY_VERSION = "false-success-policy/1"
MAX_CASES = 64
MAX_BODY_BYTES = 64 * 1024
MAX_INPUT_BYTES = 1024 * 1024
MAX_TEXT = 240
REQUIRED_FAMILIES = (
    "HTTP_200_HTML",
    "HTTP_200_LOGIN_HTML",
    "HTTP_200_MISLABELED_HTML",
    "HTTP_NON_2XX",
    "JSON_RPC_ERROR",
    "MCP_TOOL_ERROR",
    "MCP_WRAPPED_HTML",
    "MALFORMED_JSON",
    "VALID_CONTROL",
)
_DISPOSITIONS = {"SUCCESS", "ERROR"}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
_HTML_MARKERS = (
    "<!doctype html",
    "<html",
    "<head",
    "<body",
    "<form",
    "<title",
    "<script",
    "<meta",
)
_LOGIN_MARKERS = (
    "type=\"password\"",
    "type='password'",
    "name=\"password\"",
    "name='password'",
    "sign in",
    "log in",
    "login",
    "authentication required",
)


class ProofError(ValueError):
    """Base validation/proof error."""


class SchemaError(ProofError):
    """Input does not satisfy the strict proof schema."""


@dataclass(frozen=True)
class Classification:
    decision: str
    reasons: tuple[str, ...]
    tags: tuple[str, ...]
    body_sha256: str
    body_bytes: int
    media_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": list(self.reasons),
            "tags": list(self.tags),
            "body_sha256": self.body_sha256,
            "body_bytes": self.body_bytes,
            "media_type": self.media_type,
        }


def _reject_constant(value: str) -> Any:
    raise SchemaError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SchemaError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(raw: str | bytes) -> Any:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SchemaError("JSON input is not strict UTF-8") from exc
    try:
        return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except SchemaError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchemaError("invalid JSON") from exc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_keys(value: Mapping[str, Any], required: Iterable[str], *, where: str) -> None:
    expected = set(required)
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SchemaError(f"{where} keys mismatch; missing={missing} extra={extra}")


def _text(value: Any, *, field: str, max_len: int = MAX_TEXT, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise SchemaError(f"{field} must be a string")
    if len(value) > max_len or (not allow_empty and not value):
        raise SchemaError(f"{field} length is invalid")
    if any(ord(ch) < 0x20 and ch not in "\t" for ch in value):
        raise SchemaError(f"{field} contains control characters")
    return value


def _safe_id(value: Any, *, field: str) -> str:
    text = _text(value, field=field, max_len=96)
    if not _SAFE_ID.fullmatch(text):
        raise SchemaError(f"{field} contains unsupported characters")
    return text


def _hex64(value: Any, *, field: str) -> str:
    if type(value) is not str or not _HEX_64.fullmatch(value):
        raise SchemaError(f"{field} must be lowercase SHA-256 hex")
    return value


def _integer(value: Any, *, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not (minimum <= value <= maximum):
        raise SchemaError(f"{field} must be an integer in [{minimum}, {maximum}]")
    return value


def _utc_second(value: Any, *, field: str) -> str:
    text = _text(value, field=field, max_len=20)
    try:
        parsed = dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError as exc:
        raise SchemaError(f"{field} must be canonical whole-second UTC") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise SchemaError(f"{field} must be canonical whole-second UTC")
    return text


def _decode_body(value: Any) -> bytes:
    text = _text(value, field="body_base64", max_len=((MAX_BODY_BYTES + 2) // 3) * 4 + 8, allow_empty=True)
    try:
        body = base64.b64decode(text.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise SchemaError("body_base64 must be canonical base64") from exc
    if len(body) > MAX_BODY_BYTES:
        raise SchemaError(f"response body exceeds {MAX_BODY_BYTES} bytes")
    if base64.b64encode(body).decode("ascii") != text:
        raise SchemaError("body_base64 is not canonical")
    return body


def _media_type(value: Any) -> str:
    text = _text(value, field="content_type", max_len=160).strip()
    media = text.split(";", 1)[0].strip().casefold()
    if not media or "/" not in media or any(ch.isspace() for ch in media):
        raise SchemaError("content_type has an invalid media type")
    return media


def _looks_html_bytes(body: bytes) -> bool:
    if not body:
        return False
    sample = body[:8192].decode("utf-8", errors="ignore").lstrip("\ufeff\x00 \t\r\n").casefold()
    if any(sample.startswith(marker) for marker in _HTML_MARKERS):
        return True
    if sample.startswith("<!--"):
        close = sample.find("-->")
        if close != -1:
            after = sample[close + 3 :].lstrip()
            return any(after.startswith(marker) for marker in ("<html", "<!doctype", "<body", "<head"))
    return False


def _looks_login_bytes(body: bytes) -> bool:
    if not _looks_html_bytes(body):
        return False
    sample = body[:8192].decode("utf-8", errors="ignore").casefold()
    return any(marker in sample for marker in _LOGIN_MARKERS)


def _looks_html_text(text: str) -> bool:
    return _looks_html_bytes(text.encode("utf-8", errors="ignore"))


def _parse_json_bytes(body: bytes) -> Any:
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaError("response JSON is not strict UTF-8") from exc
    return loads_strict(text)


def _parse_sse(body: bytes) -> Any:
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaError("SSE body is not strict UTF-8") from exc
    events: list[str] = []
    pending: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line == "":
            if pending:
                events.append("\n".join(pending))
                pending = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data = line[5:]
            if data.startswith(" "):
                data = data[1:]
            pending.append(data)
    if pending:
        events.append("\n".join(pending))
    if not events:
        raise SchemaError("SSE response contains no data event")
    parsed: list[Any] = []
    for event in events:
        parsed.append(loads_strict(event))
    # A response stream may contain notifications before the correlated response.
    # For proof classification, the final JSON-RPC object is the terminal evidence.
    return parsed[-1]


def _embedded_html(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    result = payload.get("result")
    if not isinstance(result, dict):
        return False
    content = result.get("content")
    if not isinstance(content, list):
        return False
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and type(item.get("text")) is str:
            if _looks_html_text(item["text"]):
                return True
    return False


def classify_exchange(status: int, content_type: str, body: bytes) -> Classification:
    media = _media_type(content_type)
    reasons: list[str] = []
    tags: set[str] = set()
    body_sha = sha256_bytes(body)

    if not (200 <= status <= 299):
        reasons.append("HTTP_STATUS_NOT_SUCCESS")
        tags.add("HTTP_NON_2XX")

    raw_html = _looks_html_bytes(body)
    if raw_html:
        reasons.append("HTML_BODY")
        if 200 <= status <= 299:
            tags.add("HTTP_200_HTML")
            if _looks_login_bytes(body):
                tags.add("HTTP_200_LOGIN_HTML")
            if media == "application/json" or media.endswith("+json"):
                tags.add("HTTP_200_MISLABELED_HTML")

    payload: Any = None
    parse_failed = False
    json_media = media == "application/json" or media.endswith("+json")
    sse_media = media == "text/event-stream"

    if 200 <= status <= 299 and not raw_html:
        if not (json_media or sse_media):
            reasons.append("UNSUPPORTED_SUCCESS_MEDIA_TYPE")
        else:
            try:
                payload = _parse_sse(body) if sse_media else _parse_json_bytes(body)
            except SchemaError:
                parse_failed = True
                reasons.append("MALFORMED_STRUCTURED_BODY")
                if json_media:
                    tags.add("MALFORMED_JSON")

    if payload is not None:
        if not isinstance(payload, dict):
            reasons.append("JSON_RPC_ENVELOPE_NOT_OBJECT")
        elif payload.get("jsonrpc") != "2.0":
            reasons.append("JSON_RPC_VERSION_INVALID")
        elif "error" in payload and payload.get("error") is not None:
            reasons.append("JSON_RPC_ERROR")
            tags.add("JSON_RPC_ERROR")
        elif "result" not in payload:
            reasons.append("JSON_RPC_RESULT_MISSING")
        else:
            result = payload.get("result")
            if not isinstance(result, dict):
                reasons.append("MCP_RESULT_NOT_OBJECT")
            else:
                if "isError" not in result:
                    reasons.append("MCP_IS_ERROR_MISSING")
                elif type(result["isError"]) is not bool:
                    reasons.append("MCP_IS_ERROR_NOT_BOOL")
                elif result["isError"]:
                    reasons.append("MCP_TOOL_ERROR")
                    tags.add("MCP_TOOL_ERROR")

                if "content" not in result:
                    reasons.append("MCP_CONTENT_MISSING")
                elif not isinstance(result["content"], list):
                    reasons.append("MCP_CONTENT_NOT_LIST")
                else:
                    for item in result["content"]:
                        if not isinstance(item, dict):
                            reasons.append("MCP_CONTENT_ITEM_NOT_OBJECT")
                            continue
                        if type(item.get("type")) is not str or not item["type"]:
                            reasons.append("MCP_CONTENT_TYPE_INVALID")
                        elif item["type"] == "text" and type(item.get("text")) is not str:
                            reasons.append("MCP_TEXT_CONTENT_INVALID")
            if _embedded_html(payload):
                reasons.append("MCP_WRAPPED_HTML")
                tags.add("MCP_WRAPPED_HTML")

    decision = "REJECT" if reasons else "ACCEPT"
    if decision == "ACCEPT":
        tags.add("VALID_CONTROL")
    return Classification(
        decision=decision,
        reasons=tuple(sorted(set(reasons))),
        tags=tuple(sorted(tags)),
        body_sha256=body_sha,
        body_bytes=len(body),
        media_type=media,
    )


def _normalize_case(value: Any, *, index: int) -> tuple[dict[str, Any], bytes, Classification]:
    if not isinstance(value, dict):
        raise SchemaError(f"cases[{index}] must be an object")
    _exact_keys(
        value,
        (
            "id",
            "family",
            "status",
            "content_type",
            "body_base64",
            "observed_client_disposition",
            "client_event_sha256",
            "source_sha256",
        ),
        where=f"cases[{index}]",
    )
    case_id = _safe_id(value["id"], field=f"cases[{index}].id")
    family = _text(value["family"], field=f"cases[{index}].family", max_len=64)
    if family not in REQUIRED_FAMILIES:
        raise SchemaError(f"cases[{index}].family is unsupported")
    status = _integer(value["status"], field=f"cases[{index}].status", minimum=100, maximum=599)
    content_type = _text(value["content_type"], field=f"cases[{index}].content_type", max_len=160)
    body = _decode_body(value["body_base64"])
    disposition = _text(
        value["observed_client_disposition"],
        field=f"cases[{index}].observed_client_disposition",
        max_len=16,
    )
    if disposition not in _DISPOSITIONS:
        raise SchemaError(f"cases[{index}].observed_client_disposition is unsupported")
    normalized = {
        "id": case_id,
        "family": family,
        "status": status,
        "content_type": content_type.strip(),
        "body_base64": base64.b64encode(body).decode("ascii"),
        "observed_client_disposition": disposition,
        "client_event_sha256": _hex64(value["client_event_sha256"], field=f"cases[{index}].client_event_sha256"),
        "source_sha256": _hex64(value["source_sha256"], field=f"cases[{index}].source_sha256"),
    }
    classification = classify_exchange(status, normalized["content_type"], body)
    if family not in classification.tags:
        raise SchemaError(
            f"cases[{index}] declared family {family} is not supported by the captured exchange; "
            f"observed tags={list(classification.tags)}"
        )
    return normalized, body, classification


def normalize_bundle(bundle: Any) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Classification]]]:
    if not isinstance(bundle, dict):
        raise SchemaError("capture bundle must be an object")
    _exact_keys(bundle, ("schema", "client", "captured_at", "cases"), where="bundle")
    if bundle["schema"] != CAPTURE_SCHEMA:
        raise SchemaError("unsupported capture schema")
    client = bundle["client"]
    if not isinstance(client, dict):
        raise SchemaError("client must be an object")
    _exact_keys(client, ("name", "version"), where="client")
    client_norm = {
        "name": _text(client["name"], field="client.name", max_len=120),
        "version": _text(client["version"], field="client.version", max_len=120),
    }
    captured_at = _utc_second(bundle["captured_at"], field="captured_at")
    cases = bundle["cases"]
    if not isinstance(cases, list) or not (1 <= len(cases) <= MAX_CASES):
        raise SchemaError(f"cases must contain between 1 and {MAX_CASES} entries")
    seen_ids: set[str] = set()
    normalized_cases: list[dict[str, Any]] = []
    evidence: list[tuple[dict[str, Any], Classification]] = []
    for index, value in enumerate(cases):
        normalized, _body, classification = _normalize_case(value, index=index)
        if normalized["id"] in seen_ids:
            raise SchemaError(f"duplicate case id: {normalized['id']}")
        seen_ids.add(normalized["id"])
        normalized_cases.append(normalized)
        evidence.append((normalized, classification))
    normalized_bundle = {
        "schema": CAPTURE_SCHEMA,
        "client": client_norm,
        "captured_at": captured_at,
        "cases": normalized_cases,
    }
    return normalized_bundle, evidence


def compile_proof(bundle: Any) -> dict[str, Any]:
    normalized, evidence = normalize_bundle(bundle)
    covered = sorted({case["family"] for case, _ in evidence})
    missing = sorted(set(REQUIRED_FAMILIES) - set(covered))
    findings: list[dict[str, Any]] = []
    false_success_ids: list[str] = []
    mismatch_ids: list[str] = []
    for case, classification in evidence:
        expected_disposition = "SUCCESS" if classification.decision == "ACCEPT" else "ERROR"
        observed = case["observed_client_disposition"]
        matched = observed == expected_disposition
        if not matched:
            mismatch_ids.append(case["id"])
            if classification.decision == "REJECT" and observed == "SUCCESS":
                false_success_ids.append(case["id"])
        findings.append(
            {
                "id": case["id"],
                "family": case["family"],
                "status": case["status"],
                "media_type": classification.media_type,
                "body_sha256": classification.body_sha256,
                "body_bytes": classification.body_bytes,
                "source_sha256": case["source_sha256"],
                "client_event_sha256": case["client_event_sha256"],
                "policy_decision": classification.decision,
                "observed_client_disposition": observed,
                "client_matches_policy": matched,
                "reasons": list(classification.reasons),
            }
        )

    if missing:
        decision = "HOLD_INCOMPLETE_MATRIX"
    elif false_success_ids:
        decision = "FALSE_SUCCESS_DETECTED"
    elif mismatch_ids:
        decision = "CLIENT_MISMATCH"
    else:
        decision = "SURVIVED"

    proof = {
        "policy_version": POLICY_VERSION,
        "client": normalized["client"],
        "captured_at": normalized["captured_at"],
        "capture_bundle_sha256": sha256_bytes(canonical_bytes(normalized)),
        "required_families": list(REQUIRED_FAMILIES),
        "covered_families": covered,
        "missing_families": missing,
        "case_count": len(findings),
        "decision": decision,
        "false_success_case_ids": sorted(false_success_ids),
        "mismatch_case_ids": sorted(mismatch_ids),
        "external_send_authorized": False,
        "production_certified": False,
        "findings": findings,
    }
    return {
        "schema": PROOF_SCHEMA,
        "proof": proof,
        "proof_sha256": sha256_bytes(canonical_bytes(proof)),
    }


def verify_proof(bundle: Any, candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    try:
        _exact_keys(candidate, ("schema", "proof", "proof_sha256"), where="proof envelope")
        if candidate["schema"] != PROOF_SCHEMA:
            return False
        if not isinstance(candidate["proof"], dict):
            return False
        if _hex64(candidate["proof_sha256"], field="proof_sha256") != sha256_bytes(canonical_bytes(candidate["proof"])):
            return False
        expected = compile_proof(bundle)
    except ProofError:
        return False
    return canonical_bytes(candidate) == canonical_bytes(expected)
