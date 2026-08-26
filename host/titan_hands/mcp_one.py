#!/usr/bin/env python3
"""One-tool MCP stdio facade for TITAN Hands.

The five-tool host.titan_hands.mcp_server and four-tool Windows facade stay.
This entry point advertises a single model-facing tool that routes through
the existing observe/act/capture/capabilities contract.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping

from host.titan_hands.mcp_server import ACTION_PROPERTY, MCP_PROTOCOL, _tool_result
from host.titan_hands.one_tool import TitanHandsOne


SERVER_INSTRUCTIONS = (
    "One TITAN Hands call. Set op to observe, act, capture, capabilities, targets, or reset. "
    "Set target to windows, android, linux, files, git, slack, board, shell, or browser. "
    "Windows and Android use the existing DeltaUI adapters. Linux AT-SPI is named next. "
    "Normal observations contain no screenshots. Pixels are returned only when op is capture. "
    "The server performs requested operations directly and has no internal approval dialogue."
)

TOOL = {
    "name": "titan_hands",
    "description": (
        "One model-facing TITAN Hands call. Routes computer-use, files/git, Slack #commons, "
        "board posts, shell, and browser through the existing DeltaUI contract. "
        "Pixels are returned only when op is capture."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "description": "observe, act, capture, capabilities, targets, or reset. Free-form; typed failure if unimplemented.",
            },
            "target": {
                "type": "string",
                "description": (
                    "windows, android, linux, files, git, slack, board, shell, or browser. "
                    "Defaults to windows. Linux AT-SPI is named next."
                ),
            },
            "action": ACTION_PROPERTY,
            "observe_after": {"type": "boolean"},
            "max_nodes": {"type": "integer", "minimum": 1},
            "max_depth": {"type": "integer", "minimum": 0},
            "include_offscreen": {"type": "boolean"},
            "id": {"type": "string"},
            "path": {"type": "string"},
            "text": {"type": "string"},
            "body": {"type": "string"},
            "command": {"type": "string"},
        },
    },
    "annotations": {
        "readOnlyHint": False,
        "destructiveHint": True,
        "openWorldHint": True,
    },
}


def dispatch(router: TitanHandsOne, message: Mapping[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": MCP_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "titan-hands-one", "version": "0.3.0"},
            "instructions": SERVER_INSTRUCTIONS,
        }
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "titan_hands":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        result = _tool_result(router.handle(dict(arguments)))
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
    router = TitanHandsOne()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = dispatch(router, message)
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
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
