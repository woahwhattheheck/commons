#!/usr/bin/env python3
"""Dependency-free MCP facade for unified local TITAN Hands."""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping

from .broker import TitanHandsBroker
from .runtime import TitanHandsRuntime


MCP_PROTOCOL = "2025-03-26"
SERVER_INSTRUCTIONS = (
    "One tool: hands. Set route and op. Default route is computer (Windows or Android DeltaUI). "
    "Observe before acting. Pixels move only through op=capture. Other live routes: file, git, "
    "slack (#commons C0BRGMDQB6G), board (new p/{id}.md only), shell, web. Linux AT-SPI returns "
    "ADAPTER_NOT_WRITTEN. hands_observe/act/capture/targets/capabilities remain compatibility "
    "aliases for computer-use. The server performs requested operations directly and has no "
    "internal approval dialogue."
)

TARGET_PROPERTY = {
    "type": "string",
    "enum": ["windows", "android"],
    "description": "Execution surface. Defaults to windows.",
}

ACTION_PROPERTY = {
    "type": "object",
    "required": ["type"],
    "description": (
        "One semantic or input action. For launch, Windows requires file and accepts an "
        "optional args array. Android prefers the LDA Kotlin operator: common TITAN verbs are "
        "translated, and LDA-native verbs remain free-form. Android launch accepts name/app/package."
    ),
    "properties": {
        "type": {
            "type": "string",
            "description": (
                "Free-form adapter action verb. Built-ins include invoke, set_value, toggle, "
                "expand, collapse, select, focus, click, type_text, key, scroll, launch, wait, "
                "and done."
            ),
        },
        "id": {"type": "string", "description": "Stable node ID from hands_observe."},
        "text": {"type": "string"},
        "value": {"type": "string"},
        "key": {"type": "string"},
        "delta": {"type": "integer"},
        "file": {"type": "string", "description": "Windows executable for launch."},
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional Windows launch arguments; omit when none are needed.",
        },
        "package": {"type": "string", "description": "Android package for launch."},
        "name": {"type": "string", "description": "App or semantic target name."},
        "app": {"type": "string", "description": "Android app name for LDA open_app."},
        "activity": {"type": "string", "description": "Optional Android activity."},
        "milliseconds": {"type": "integer", "minimum": 0},
    },
}

HANDS_TOOL = {
    "name": "hands",
    "description": (
        "Primary TITAN Hands tool. One call routes computer-use, files, git, Slack #commons, "
        "board posts, shell, and web fetch. Set route plus op. Default route is computer. "
        "Call op=catalog for live vs ADAPTER_NOT_WRITTEN. Pixels only when op=capture. "
        "Linux AT-SPI is named and returns ADAPTER_NOT_WRITTEN."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["op"],
        "properties": {
            "route": {
                "type": "string",
                "description": (
                    "computer (default), file, git, slack, board, shell, web, linux, or catalog. "
                    "linux returns ADAPTER_NOT_WRITTEN."
                ),
            },
            "op": {
                "type": "string",
                "description": (
                    "computer: observe, act, capture, done, targets, capabilities. "
                    "file: list, read, write. git: status, diff, log, add, commit. "
                    "slack: read, post. board: read, post. shell: run. web: fetch. catalog: catalog."
                ),
            },
            "target": TARGET_PROPERTY,
            "action": ACTION_PROPERTY,
            "observe_after": {"type": "boolean"},
            "max_nodes": {"type": "integer", "minimum": 1},
            "max_depth": {"type": "integer", "minimum": 0},
            "include_offscreen": {"type": "boolean"},
            "id": {"type": "string"},
            "path": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}},
            "contents": {"type": "string"},
            "text": {"type": "string"},
            "body": {"type": "string"},
            "message": {"type": "string"},
            "command": {
                "description": "Shell string or argv list.",
                "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
            },
            "url": {"type": "string"},
            "from": {"type": "string"},
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "board": {"type": "string"},
            "lane": {"type": "string"},
            "kind": {"type": "string"},
            "channel": {
                "type": "string",
                "description": "Slack dest. Only #commons C0BRGMDQB6G is used.",
            },
            "thread_ts": {"type": "string"},
            "timeout": {"type": "number"},
            "limit": {"type": "integer", "minimum": 1},
            "count": {"type": "integer", "minimum": 1},
            "staged": {"type": "boolean"},
            "method": {"type": "string"},
        },
    },
    "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True},
}

COMPAT_OPS = {
    "hands_targets": "targets",
    "hands_observe": "observe",
    "hands_act": "act",
    "hands_capture": "capture",
    "hands_capabilities": "capabilities",
}

TOOLS = [
    HANDS_TOOL,
    {
        "name": "hands_targets",
        "description": "Compatibility alias. Prefer hands with op=targets.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "hands_observe",
        "description": "Compatibility alias. Prefer hands with route=computer, op=observe. No pixels.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": TARGET_PROPERTY,
                "max_nodes": {"type": "integer", "minimum": 1},
                "max_depth": {"type": "integer", "minimum": 0},
                "include_offscreen": {"type": "boolean"},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "hands_act",
        "description": "Compatibility alias. Prefer hands with route=computer, op=act.",
        "inputSchema": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "target": TARGET_PROPERTY,
                "action": ACTION_PROPERTY,
                "observe_after": {"type": "boolean"},
                "max_nodes": {"type": "integer", "minimum": 1},
                "max_depth": {"type": "integer", "minimum": 0},
            },
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True},
    },
    {
        "name": "hands_capture",
        "description": "Compatibility alias. Prefer hands with route=computer, op=capture.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": TARGET_PROPERTY,
                "id": {"type": "string"},
                "path": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "hands_capabilities",
        "description": "Compatibility alias. Prefer hands with op=capabilities or op=catalog.",
        "inputSchema": {"type": "object", "properties": {"target": TARGET_PROPERTY}},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
]


def _tool_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(dict(result), ensure_ascii=False, separators=(",", ":")),
            }
        ],
        "isError": not bool(result.get("ok")),
    }


def _runtime(surface: TitanHandsBroker | TitanHandsRuntime) -> TitanHandsRuntime:
    if isinstance(surface, TitanHandsRuntime):
        return surface
    return TitanHandsRuntime(broker=surface)


def dispatch(
    surface: TitanHandsBroker | TitanHandsRuntime, message: Mapping[str, Any]
) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    runtime = _runtime(surface)
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        result = {
            "protocolVersion": MCP_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "titan-hands", "version": "0.3.0"},
            "instructions": SERVER_INSTRUCTIONS,
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = dict(params.get("arguments") or {})
        if name == "hands":
            result = _tool_result(runtime.handle(arguments))
        elif name in COMPAT_OPS:
            result = _tool_result(runtime.handle({"op": COMPAT_OPS[name], **arguments}))
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    runtime = TitanHandsRuntime()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = dispatch(runtime, message)
            except Exception as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(exc)},
                }
            if response is not None:
                print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
