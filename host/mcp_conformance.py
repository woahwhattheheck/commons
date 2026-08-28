#!/usr/bin/env python3
"""Dependency-free MCP endpoint conformance runner.

The runner is deliberately transport- and vendor-neutral. It performs public MCP
discovery, records exact hashes, and can optionally invoke any named tool when
the caller explicitly supplies its arguments. Reports omit response bodies and
URL credentials by default so the durable receipt can be shared safely.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "commons-mcp-conformance-receipt-v1"
PROTOCOL_VERSION = "2025-06-18"
DEFAULT_REQUIRED_TOOLS = (
    "open_commons_composer",
    "fire_action",
    "append_post",
    "append_model_post",
    "post_to_action_pad",
    "create_memory_board",
    "append_memory",
    "verify_durability",
    "get_send_link",
)
DISCOVERY_METHODS = ("tools/list", "resources/list", "prompts/list")


class ConformanceError(RuntimeError):
    """A typed transport or protocol failure suitable for a public receipt."""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def receipt(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.details}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def public_endpoint(raw: str) -> str:
    """Remove userinfo, query, and fragment from the shareable endpoint label."""
    parsed = urllib.parse.urlsplit(str(raw))
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = "[" + host + "]"
    if parsed.port is not None:
        host += ":" + str(parsed.port)
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _decode_response(body: bytes, content_type: str) -> dict[str, Any]:
    text = body.decode("utf-8")
    if content_type.lower().startswith("text/event-stream"):
        events: list[str] = []
        data_lines: list[str] = []
        for line in text.splitlines():
            if line == "":
                if data_lines:
                    events.append("\n".join(data_lines))
                    data_lines = []
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if data_lines:
            events.append("\n".join(data_lines))
        for event in reversed(events):
            try:
                value = json.loads(event)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise ConformanceError("INVALID_SSE", "SSE response contained no JSON object")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConformanceError(
            "INVALID_JSON",
            "MCP response was not valid JSON",
            response_sha256=hashlib.sha256(body).hexdigest(),
        ) from exc
    if not isinstance(value, dict):
        raise ConformanceError("INVALID_RPC", "MCP response must be a JSON object")
    return value


class MCPClient:
    def __init__(self, endpoint: str, *, timeout: float = 20.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.session_id = ""
        self.next_id = 1

    def _request(self, payload: dict[str, Any], *, expect_response: bool = True) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        packed = canonical_json(payload).encode("utf-8")
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "commons-mcp-conformance/1",
        }
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        request = urllib.request.Request(self.endpoint, data=packed, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                content_type = str(response.headers.get("Content-Type") or "application/json").split(";", 1)[0].strip()
                observed_session = str(response.headers.get("MCP-Session-Id") or "")
                if observed_session:
                    self.session_id = observed_session
                transport = {
                    "http_status": int(response.status),
                    "content_type": content_type,
                    "request_sha256": hashlib.sha256(packed).hexdigest(),
                    "response_sha256": hashlib.sha256(body).hexdigest(),
                    "response_bytes": len(body),
                }
                if not expect_response or response.status == 202 or not body:
                    return None, transport
                return _decode_response(body, content_type), transport
        except urllib.error.HTTPError as exc:
            body = exc.read()
            raise ConformanceError(
                "HTTP_ERROR",
                "MCP endpoint returned HTTP %d" % exc.code,
                http_status=exc.code,
                response_sha256=hashlib.sha256(body).hexdigest(),
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ConformanceError(
                "TRANSPORT_ERROR",
                "MCP endpoint could not be reached",
                error_type=type(exc).__name__,
            ) from exc

    def call(self, method: str, params: Any | None = None) -> tuple[Any, dict[str, Any]]:
        request_id = self.next_id
        self.next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        response, transport = self._request(payload)
        if response is None:
            raise ConformanceError("MISSING_RPC", "%s returned no JSON-RPC response" % method)
        if response.get("jsonrpc") != "2.0" or response.get("id") != request_id:
            raise ConformanceError("INVALID_RPC", "%s returned a mismatched JSON-RPC envelope" % method)
        if "error" in response:
            error = response["error"] if isinstance(response["error"], dict) else {}
            raise ConformanceError(
                "RPC_ERROR",
                "%s returned JSON-RPC error" % method,
                rpc_code=error.get("code"),
                rpc_message=str(error.get("message") or ""),
            )
        if "result" not in response:
            raise ConformanceError("INVALID_RPC", "%s response has no result" % method)
        return response["result"], transport

    def notify(self, method: str, params: Any | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        _response, transport = self._request(payload, expect_response=False)
        return transport


def _discovery_row(client: MCPClient, method: str) -> tuple[dict[str, Any], Any | None]:
    try:
        result, transport = client.call(method, {})
        return {"state": "SUPPORTED", **transport}, result
    except ConformanceError as exc:
        state = "UNSUPPORTED" if exc.code == "RPC_ERROR" and exc.details.get("rpc_code") == -32601 else "FAILED"
        return {"state": state, "error": exc.receipt()}, None


def _names(result: Any, key: str) -> list[str]:
    if not isinstance(result, dict) or not isinstance(result.get(key), list):
        return []
    names = []
    for item in result[key]:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return sorted(set(names))


def run_conformance(
    endpoint: str,
    *,
    timeout: float = 20.0,
    required_tools: tuple[str, ...] = DEFAULT_REQUIRED_TOOLS,
    call_tool: str = "",
    call_arguments: dict[str, Any] | None = None,
    include_call_result: bool = False,
) -> dict[str, Any]:
    started = utc_now()
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "measured_at": started,
        "endpoint": public_endpoint(endpoint),
        "input_sha256": sha256_text(endpoint),
        "protocol_requested": PROTOCOL_VERSION,
        "required_tools": sorted(set(required_tools)),
        "transport": {},
        "discovery": {},
        "capabilities": {},
        "tool_call": None,
        "errors": [],
    }
    client = MCPClient(endpoint, timeout=timeout)
    try:
        initialize, init_transport = client.call(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "commons-mcp-conformance", "version": "1.0.0"},
            },
        )
        receipt["transport"]["initialize"] = init_transport
        if not isinstance(initialize, dict):
            raise ConformanceError("INVALID_INITIALIZE", "initialize result must be an object")
        receipt["protocol_negotiated"] = initialize.get("protocolVersion")
        receipt["server_info"] = initialize.get("serverInfo", {})
        receipt["capabilities"] = initialize.get("capabilities", {})
        try:
            receipt["transport"]["initialized"] = client.notify("notifications/initialized", {})
        except ConformanceError as exc:
            receipt["transport"]["initialized"] = {"state": "FAILED", "error": exc.receipt()}

        results: dict[str, Any] = {}
        for method in DISCOVERY_METHODS:
            row, value = _discovery_row(client, method)
            receipt["discovery"][method] = row
            results[method] = value

        tool_names = _names(results.get("tools/list"), "tools")
        receipt["tool_names"] = tool_names
        missing = sorted(set(required_tools) - set(tool_names))
        receipt["tool_parity"] = {
            "present": sorted(set(required_tools) & set(tool_names)),
            "missing": missing,
            "complete": not missing,
        }
        receipt["resource_names"] = _names(results.get("resources/list"), "resources")
        receipt["prompt_names"] = _names(results.get("prompts/list"), "prompts")

        if call_tool:
            arguments = call_arguments or {}
            request_fingerprint = {"name": call_tool, "arguments": arguments}
            call_row: dict[str, Any] = {
                "name": call_tool,
                "request_sha256": sha256_text(canonical_json(request_fingerprint)),
            }
            try:
                result, transport = client.call(
                    "tools/call",
                    {"name": call_tool, "arguments": arguments},
                )
                packed_result = canonical_json(result)
                call_row.update(
                    {
                        "state": "RETURNED",
                        "transport": transport,
                        "result_sha256": sha256_text(packed_result),
                        "result_bytes": len(packed_result.encode("utf-8")),
                    }
                )
                if include_call_result:
                    call_row["result"] = result
            except ConformanceError as exc:
                call_row.update({"state": "FAILED", "error": exc.receipt()})
            receipt["tool_call"] = call_row

        discovery_failed = [
            method for method, row in receipt["discovery"].items()
            if row["state"] == "FAILED"
        ]
        call_failed = bool(receipt["tool_call"] and receipt["tool_call"]["state"] == "FAILED")
        if discovery_failed or call_failed:
            receipt["status"] = "FAIL"
        elif missing or any(row["state"] == "UNSUPPORTED" for row in receipt["discovery"].values()):
            receipt["status"] = "PARTIAL"
        else:
            receipt["status"] = "PASS"
    except ConformanceError as exc:
        receipt["status"] = "FAIL"
        receipt["errors"].append(exc.receipt())

    unsigned = canonical_json(receipt)
    receipt["receipt_sha256"] = sha256_text(unsigned)
    return receipt


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit("--arguments-json must be valid JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit("--arguments-json must decode to an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="HTTP(S) MCP endpoint")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--require-tool",
        action="append",
        default=None,
        help="tool name required for parity; repeatable (defaults to Commons shared tools)",
    )
    parser.add_argument("--call-tool", default="", help="explicitly invoke this discovered or undiscovered tool")
    parser.add_argument("--arguments-json", default="{}", help="JSON object for --call-tool")
    parser.add_argument(
        "--include-call-result",
        action="store_true",
        help="include the tool response body in the report; default records only hashes and size",
    )
    parser.add_argument("--output", help="write the canonical JSON receipt to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    required = tuple(args.require_tool) if args.require_tool is not None else DEFAULT_REQUIRED_TOOLS
    report = run_conformance(
        args.endpoint,
        timeout=args.timeout,
        required_tools=required,
        call_tool=args.call_tool,
        call_arguments=_parse_arguments(args.arguments_json),
        include_call_result=args.include_call_result,
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["status"] in {"PASS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
