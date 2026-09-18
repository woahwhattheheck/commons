#!/usr/bin/env python3
"""Read-only live conformance checker for the public Commons MCP connector.

Default mode never writes. Supply ``--write-canary`` plus ``--canary-id`` to
send one append-only canary; unit tests and CI must not pass that flag.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Callable
from urllib.request import OpenerDirector, Request

PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
CONNECTOR_NAME = "Commons"
TRANSPORT = "Streamable HTTP"
AUTH_MODE = "None"
PROTOCOL_OFFER = "2025-03-26"
TIMEOUT_S = 15

SOURCE_CORE_TOOLS = (
    "discover_commons_capabilities",
    "search_commons",
    "read_commons_resource",
    "open_commons_composer",
    "fire_action",
    "append_post",
    "append_model_post",
    "post_to_action_pad",
    "route_grokcom_revenue_work",
    "create_memory_board",
    "append_memory",
    "verify_durability",
    "read_observatory",
    "observe_work",
    "project_live_work",
    "continue_from_observation",
)
ADAPTER_EXTRA_TOOLS = ("get_send_link",)
EXPECTED_SOURCE_TOOLS = SOURCE_CORE_TOOLS + ADAPTER_EXTRA_TOOLS
READONLY_TOOLS = frozenset(
    {
        "discover_commons_capabilities",
        "search_commons",
        "read_commons_resource",
        "open_commons_composer",
        "verify_durability",
        "read_observatory",
        "observe_work",
        "project_live_work",
        "continue_from_observation",
        "get_send_link",
    }
)
OAUTH_PATHS = (
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-protected-resource",
)

HttpFn = Callable[..., tuple[int, dict[str, str], bytes]]


def _repo_root() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir)
    )


def load_source_surface(repo_root: str | None = None) -> dict[str, Any]:
    """Load the canonical source MCP surface. Fallback constants if import fails."""
    root = repo_root or _repo_root()
    tools = list(EXPECTED_SOURCE_TOOLS)
    version = "1.2.0"
    name = "commons"
    resources: list[str] = []
    templates: list[str] = []
    annotations: dict[str, dict[str, Any]] = {}
    required: dict[str, list[str]] = {}
    imported = False
    try:
        if root not in sys.path:
            sys.path.insert(0, root)
        import commons_mcp as cm  # type: ignore
        from api import mcp as adapter  # type: ignore

        imported = True
        name = cm.SERVER_NAME
        version = cm.SERVER_VERSION
        tools = [row["name"] for row in cm.TOOL_DEFINITIONS]
        if adapter.GET_SEND_LINK_TOOL["name"] not in tools:
            tools.append(adapter.GET_SEND_LINK_TOOL["name"])
        resources = [row["uri"] for row in cm.RESOURCES]
        templates = [row["uriTemplate"] for row in cm.RESOURCE_TEMPLATES]
        for row in list(cm.TOOL_DEFINITIONS) + [adapter.GET_SEND_LINK_TOOL]:
            annotations[row["name"]] = dict(row.get("annotations") or {})
            schema = row.get("inputSchema") or {}
            required[row["name"]] = list(schema.get("required") or [])
    except Exception as exc:  # pragma: no cover - exercised when isolated
        annotations = {
            "verify_durability": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": True,
            },
            "get_send_link": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
            "fire_action": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": True,
            },
        }
        required = {"append_post": ["id", "body"], "verify_durability": ["id"]}
        return {
            "name": name,
            "version": version,
            "tools": list(EXPECTED_SOURCE_TOOLS),
            "resources": resources,
            "resource_templates": templates,
            "annotations": annotations,
            "required": required,
            "imported": False,
            "import_error": str(exc),
        }
    return {
        "name": name,
        "version": version,
        "tools": tools,
        "resources": resources,
        "resource_templates": templates,
        "annotations": annotations,
        "required": required,
        "imported": imported,
        "import_error": None,
    }


def http_exchange(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = TIMEOUT_S,
    opener: OpenerDirector | None = None,
) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, data=body, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout) as response:
            raw = response.read()
            return int(response.status), {k.lower(): v for k, v in response.headers.items()}, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return int(exc.code), hdrs, raw


def rpc(
    url: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
    timeout: float = TIMEOUT_S,
    opener: OpenerDirector | None = None,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    status, headers, raw = http_exchange(
        url,
        method="POST",
        body=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_OFFER,
        },
        timeout=timeout,
        opener=opener,
    )
    try:
        parsed = json.loads(raw.decode("utf-8") or "null")
    except json.JSONDecodeError:
        parsed = {"parse_error": True, "raw_utf8": raw.decode("utf-8", "replace")[:4000]}
    return status, headers, parsed if isinstance(parsed, dict) else {"non_object": parsed}


def measure_live(
    url: str = PUBLIC_MCP_URL,
    *,
    timeout: float = TIMEOUT_S,
    opener: OpenerDirector | None = None,
) -> dict[str, Any]:
    init_status, init_headers, init_body = rpc(
        url,
        "initialize",
        {
            "protocolVersion": PROTOCOL_OFFER,
            "capabilities": {},
            "clientInfo": {"name": "grok-web-commons", "version": "1"},
        },
        request_id=1,
        timeout=timeout,
        opener=opener,
    )
    tools_status, tools_headers, tools_body = rpc(
        url, "tools/list", {}, request_id=2, timeout=timeout, opener=opener
    )
    resources_status, _, resources_body = rpc(
        url, "resources/list", {}, request_id=3, timeout=timeout, opener=opener
    )
    templates_status, _, templates_body = rpc(
        url, "resources/templates/list", {}, request_id=4, timeout=timeout, opener=opener
    )
    get_status, _, get_body = http_exchange(url, method="GET", timeout=timeout, opener=opener)
    head_status, head_headers, _ = http_exchange(
        url, method="HEAD", timeout=timeout, opener=opener
    )
    origin = url.rsplit("/mcp", 1)[0] if url.endswith("/mcp") else url
    oauth = {}
    for path in OAUTH_PATHS:
        status, _, _ = http_exchange(
            origin + path, method="GET", timeout=timeout, opener=opener
        )
        oauth[path] = status

    init_result = init_body.get("result") if isinstance(init_body.get("result"), dict) else {}
    server = init_result.get("serverInfo") if isinstance(init_result.get("serverInfo"), dict) else {}
    tools = []
    tool_rows = ((tools_body.get("result") or {}).get("tools") if isinstance(tools_body.get("result"), dict) else None)
    if isinstance(tool_rows, list):
        tools = tool_rows
    resource_rows = ((resources_body.get("result") or {}).get("resources") if isinstance(resources_body.get("result"), dict) else None)
    template_rows = ((templates_body.get("result") or {}).get("resourceTemplates") if isinstance(templates_body.get("result"), dict) else None)

    annotations = {}
    required = {}
    names = []
    for row in tools:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        names.append(row["name"])
        annotations[row["name"]] = dict(row.get("annotations") or {})
        schema = row.get("inputSchema") or {}
        required[row["name"]] = list(schema.get("required") or [])

    session = init_headers.get("mcp-session-id") or tools_headers.get("mcp-session-id")
    return {
        "url": url,
        "http": {
            "initialize": init_status,
            "tools_list": tools_status,
            "resources_list": resources_status,
            "templates_list": templates_status,
            "GET": get_status,
            "HEAD": head_status,
        },
        "protocolVersion": init_result.get("protocolVersion"),
        "name": server.get("name"),
        "version": server.get("version"),
        "instructions": init_result.get("instructions"),
        "tools": names,
        "tool_rows": tools,
        "annotations": annotations,
        "required": required,
        "resources": [
            row.get("uri")
            for row in (resource_rows or [])
            if isinstance(row, dict) and isinstance(row.get("uri"), str)
        ],
        "resource_templates": [
            row.get("uriTemplate")
            for row in (template_rows or [])
            if isinstance(row, dict) and isinstance(row.get("uriTemplate"), str)
        ],
        "session": session,
        "oauth_metadata": oauth,
        "head_protocol": head_headers.get("mcp-protocol-version"),
        "raw": {
            "initialize": init_body,
            "tools_list": {"names": names, "count": len(names)},
            "resources_list": {"uris": [
                row.get("uri")
                for row in (resource_rows or [])
                if isinstance(row, dict)
            ]},
        },
    }


def compare(source: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    source_tools = list(source.get("tools") or [])
    live_tools = list(live.get("tools") or [])
    source_set = set(source_tools)
    live_set = set(live_tools)
    missing_tools = [name for name in source_tools if name not in live_set]
    extra_tools = [name for name in live_tools if name not in source_set]
    source_resources = list(source.get("resources") or [])
    live_resources = list(live.get("resources") or [])
    missing_resources = [uri for uri in source_resources if uri not in set(live_resources)]
    extra_resources = [uri for uri in live_resources if uri not in set(source_resources)]
    annotation_drift = []
    for name in sorted(source_set & live_set):
        want = source.get("annotations", {}).get(name)
        got = live.get("annotations", {}).get(name)
        if want and got and want != got:
            annotation_drift.append({"tool": name, "source": want, "live": got})
    required_drift = []
    for name in sorted(source_set & live_set):
        want = list(source.get("required", {}).get(name) or [])
        got = list(live.get("required", {}).get(name) or [])
        if want != got:
            required_drift.append({"tool": name, "source": want, "live": got})

    version_match = source.get("version") == live.get("version") and source.get("name") == live.get("name")
    transport_ok = (
        live.get("http", {}).get("initialize") == 200
        and live.get("http", {}).get("tools_list") == 200
        and live.get("http", {}).get("GET") == 200
        and live.get("session") in (None, "")
        and all(status == 404 for status in (live.get("oauth_metadata") or {}).values())
    )
    parity = (
        not missing_tools
        and not extra_tools
        and version_match
        and not annotation_drift
        and not required_drift
        and transport_ok
        and not missing_resources
    )
    if parity:
        state = "LIVE_SOURCE_PARITY_VERIFIED"
    elif live.get("name") == "commons" and live_tools:
        state = "STALE_DEPLOYMENT"
    else:
        state = "LIVE_PROBE_FAILED"
    return {
        "parity": parity,
        "state": state,
        "missing_tools": missing_tools,
        "extra_tools": extra_tools,
        "missing_resources": missing_resources,
        "extra_resources": extra_resources,
        "annotation_drift": annotation_drift,
        "required_drift": required_drift,
        "version": {"source": source.get("version"), "live": live.get("version")},
        "transport_ok": transport_ok,
        "sessionless": live.get("session") in (None, ""),
        "auth": AUTH_MODE,
        "oauth_absent": all(status == 404 for status in (live.get("oauth_metadata") or {}).values()),
    }


def write_canary(
    url: str,
    canary_id: str,
    body: str,
    *,
    timeout: float = TIMEOUT_S,
    opener: OpenerDirector | None = None,
) -> dict[str, Any]:
    status, _, payload = rpc(
        url,
        "tools/call",
        {"name": "append_post", "arguments": {"id": canary_id, "body": body}},
        request_id=99,
        timeout=timeout,
        opener=opener,
    )
    return {"http": status, "response": payload}


def build_report(
    source: dict[str, Any],
    live: dict[str, Any],
    drift: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": bool(drift.get("parity")),
        "connector": {
            "name": CONNECTOR_NAME,
            "url": live.get("url") or PUBLIC_MCP_URL,
            "transport": TRANSPORT,
            "auth": AUTH_MODE,
            "headers": None,
        },
        "source": {
            "name": source.get("name"),
            "version": source.get("version"),
            "tools": source.get("tools"),
            "tool_count": len(source.get("tools") or []),
            "resources": source.get("resources"),
            "imported": source.get("imported"),
        },
        "live": {
            "name": live.get("name"),
            "version": live.get("version"),
            "protocolVersion": live.get("protocolVersion"),
            "tools": live.get("tools"),
            "tool_count": len(live.get("tools") or []),
            "resources": live.get("resources"),
            "http": live.get("http"),
            "session": live.get("session"),
            "oauth_metadata": live.get("oauth_metadata"),
        },
        "drift": {
            "state": drift.get("state"),
            "missing_tools": drift.get("missing_tools"),
            "extra_tools": drift.get("extra_tools"),
            "missing_resources": drift.get("missing_resources"),
            "extra_resources": drift.get("extra_resources"),
            "annotation_drift": drift.get("annotation_drift"),
            "required_drift": drift.get("required_drift"),
            "version": drift.get("version"),
            "transport_ok": drift.get("transport_ok"),
        },
        "write": None,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=PUBLIC_MCP_URL)
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S)
    parser.add_argument(
        "--write-canary",
        action="store_true",
        default=False,
        help="DANGER: perform one append_post. Off by default. Never use in unit tests or CI.",
    )
    parser.add_argument("--canary-id", default="")
    parser.add_argument("--canary-body", default="grok-web-commons live checker canary")
    parser.add_argument("--repo-root", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = load_source_surface(args.repo_root or None)
    live = measure_live(args.url, timeout=args.timeout)
    drift = compare(source, live)
    report = build_report(source, live, drift)
    if args.write_canary:
        if not args.canary_id:
            report["write"] = {
                "ok": False,
                "error": "write-canary requires --canary-id",
            }
        else:
            report["write"] = write_canary(
                args.url, args.canary_id, args.canary_body, timeout=args.timeout
            )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["ok"] and (report.get("write") in (None, {}) or report.get("write", {}).get("ok") is not False) else 1


if __name__ == "__main__":
    sys.exit(main())
