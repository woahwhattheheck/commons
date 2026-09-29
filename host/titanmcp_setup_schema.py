#!/usr/bin/env python3
"""Unique titanmcp 1.4.5 setup-schema KEEP remainder.

Pins ChatGPT-use contracts that this seat's Sep 4 batteries named under
older codes (TASK_REQUIRED / BAD_ROLE / unknown-tool isError). Live pad
1.4.5 now fails those calls with room_id-then-task / agent_name /
NEED_REQUIRED / JSON-RPC -32602. Isolated classifier stays green without
reminting pad runtime, Commons /mcp, or Latch titanmcp.html.

Live judge: https://webmcp-pad.vercel.app/mcp
Commons KEEP: https://commons-spark-mcp.vercel.app/mcp
leftover --bake / --deploy / --go REFUSED sent=0.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ID = "cursor-titanmcp-setup-schema-20260929-01"
PAD_MCP = "https://webmcp-pad.vercel.app/mcp"
PAD_HTML = "https://webmcp-pad.vercel.app/webmcp"
COMMONS_MCP = "https://commons-spark-mcp.vercel.app/mcp"
REFUSE = ("--send", "--apply", "--go", "--autopilot", "--live", "--checkout", "--deploy", "--bake")
DO_NOT_REMINT = (
    "api/mcp.py",
    "commons_mcp.py",
    "titanmcp.html",
    "webmcp.html",
    ".github/workflows/webmcp-pad-production.yml",
    "p/cursor-titanmcp-bake-road-merge-20260904-01.md",
    "p/latch-titanmcp-html-145-20260905-01.md",
)

# Live tools/list 2026-09-29. Do not pin SERVER_VERSION as the bake discriminator.
TOOL_NAMES = (
    "create_room",
    "list_rooms",
    "post_message",
    "list_messages",
    "invite_agent",
    "set_role",
    "list_roles",
    "list_operators",
    "get_operator",
    "submit_task",
    "plan_task",
    "assign_piece",
    "list_assignments",
    "claim_assignment",
    "report_assignment_result",
    "check_subscription",
    "create_play_token",
    "request_setup",
    "get_setup_status",
    "list_research_power",
    "list_custom_tooling",
    "list_connectors",
    "get_connector",
    "attach_connector_to_room",
)
FIRST_PARTY_IDS = ("titan-hands", "harborline-origin", "peer-worker")

# Recorded live packets (2026-09-29). Classifier tests use these; CLI re-measures.
PACKET_MALFORMED = {
    "jsonrpc": "2.0",
    "id": None,
    "error": {"code": -32700, "message": "Parse error", "data": "JSONDecodeError"},
}
PACKET_UNKNOWN_METHOD = {
    "jsonrpc": "2.0",
    "id": 3,
    "error": {"code": -32601, "message": "Method not found"},
}
PACKET_MISSING_NAME = {
    "jsonrpc": "2.0",
    "id": 4,
    "error": {"code": -32602, "message": "tool name required"},
}
PACKET_UNKNOWN_TOOL = {
    "jsonrpc": "2.0",
    "id": 5,
    "error": {"code": -32602, "message": "unknown tool: no_such_tool"},
}
PACKET_REQUEST_SETUP_MISSING_NEED = {
    "jsonrpc": "2.0",
    "id": 8,
    "result": {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "ok": False,
                        "error": "BAD_ARGUMENT",
                        "argument": "need",
                        "hint": "arguments.need is required",
                    }
                ),
            }
        ],
        "structuredContent": {
            "ok": False,
            "error": "BAD_ARGUMENT",
            "argument": "need",
            "hint": "arguments.need is required",
        },
        "isError": True,
    },
}
PACKET_REQUEST_SETUP_EMPTY_NEED = {
    "jsonrpc": "2.0",
    "id": 4,
    "result": {
        "content": [{"type": "text", "text": json.dumps({"ok": False, "error": "NEED_REQUIRED"})}],
        "structuredContent": {"ok": False, "error": "NEED_REQUIRED"},
        "isError": True,
    },
}
PACKET_SUBMIT_TASK_EMPTY_TITLE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "ok": False,
                        "error": "BAD_ARGUMENT",
                        "argument": "task",
                        "hint": "arguments.task is required",
                    }
                ),
            }
        ],
        "structuredContent": {
            "ok": False,
            "error": "BAD_ARGUMENT",
            "argument": "task",
            "hint": "arguments.task is required",
        },
        "isError": True,
    },
}
PACKET_SET_ROLE_MISSING_ROLE = {
    "jsonrpc": "2.0",
    "id": 3,
    "result": {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "ok": False,
                        "error": "BAD_ARGUMENT",
                        "argument": "agent_name",
                        "hint": "arguments.agent_name is required",
                    }
                ),
            }
        ],
        "structuredContent": {
            "ok": False,
            "error": "BAD_ARGUMENT",
            "argument": "agent_name",
            "hint": "arguments.agent_name is required",
        },
        "isError": True,
    },
}


def structured_content(packet: dict[str, Any]) -> dict[str, Any]:
    result = packet.get("result")
    if not isinstance(result, dict):
        return {}
    sc = result.get("structuredContent")
    if isinstance(sc, dict):
        return sc
    return {}


def jsonrpc_error(packet: dict[str, Any]) -> dict[str, Any]:
    err = packet.get("error")
    return err if isinstance(err, dict) else {}


def classify_setup_packet(kind: str, packet: dict[str, Any]) -> dict[str, Any]:
    """Name the 1.4.5 ChatGPT-use remainder. Never silent 0."""
    sc = structured_content(packet)
    err = jsonrpc_error(packet)
    if kind == "request_setup_missing_need":
        ok = (
            packet.get("result", {}).get("isError") is True
            and sc.get("error") == "BAD_ARGUMENT"
            and sc.get("argument") == "need"
        )
        pin = "BAD_ARGUMENT.need"
    elif kind == "request_setup_empty_need":
        ok = packet.get("result", {}).get("isError") is True and sc.get("error") == "NEED_REQUIRED"
        pin = "NEED_REQUIRED"
    elif kind == "submit_task_empty_title":
        ok = (
            packet.get("result", {}).get("isError") is True
            and sc.get("error") == "BAD_ARGUMENT"
            and sc.get("argument") == "task"
        )
        pin = "BAD_ARGUMENT.task"
    elif kind == "set_role_missing_role":
        ok = (
            packet.get("result", {}).get("isError") is True
            and sc.get("error") == "BAD_ARGUMENT"
            and sc.get("argument") == "agent_name"
        )
        pin = "BAD_ARGUMENT.agent_name"
    elif kind == "unknown_tool":
        ok = err.get("code") == -32602 and "unknown tool" in str(err.get("message") or "")
        pin = "jsonrpc.-32602"
    elif kind == "malformed":
        ok = err.get("code") == -32700
        pin = "jsonrpc.-32700"
    elif kind == "unknown_method":
        ok = err.get("code") == -32601
        pin = "jsonrpc.-32601"
    elif kind == "missing_name":
        ok = err.get("code") == -32602 and "tool name required" in str(err.get("message") or "")
        pin = "jsonrpc.-32602.name"
    else:
        return {"kind": kind, "ok": False, "pin": "", "note": "unknown kind"}
    return {"kind": kind, "ok": bool(ok), "pin": pin, "structured": sc, "error": err}


def first_party_ids(payload: dict[str, Any]) -> list[str]:
    sc = structured_content(payload) if "result" in payload else payload
    rows = sc.get("first_party") or payload.get("first_party") or []
    ids = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
    return ids


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "TITANMCP_SETUP_SCHEMA",
        "id": ID,
        "refused": flag,
        "sent": 0,
        "cash": 0,
        "invented_stripe_urls": False,
        "verdict": "REFUSED",
        "note": (
            f"{flag} REFUSED. Did not remint pad runtime, Commons api/mcp.py, "
            "or Latch titanmcp.html. leftover bake/deploy sent=0."
        ),
    }


def _rpc(url: str, obj: Any | None = None, *, raw: bytes | None = None, origin: str = "") -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    }
    if origin:
        headers["Origin"] = origin
    data = raw if raw is not None else json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return {
                "status": resp.status,
                "packet": json.loads(body.decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read()
        try:
            packet = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            packet = {"raw": raw_body[:200].decode("utf-8", "replace")}
        return {"status": exc.code, "packet": packet}


def _call(name: str, arguments: dict[str, Any], request_id: int = 1) -> dict[str, Any]:
    return _rpc(
        PAD_MCP,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )


def measure() -> dict[str, Any]:
    errors: list[str] = []
    init = _rpc(
        PAD_MCP,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "titanmcp-setup-schema", "version": "1"},
            },
        },
    )
    info = ((init.get("packet") or {}).get("result") or {}).get("serverInfo") or {}
    if info.get("name") != "titanmcp":
        errors.append("pad_name")
    listed = _rpc(PAD_MCP, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = [row.get("name") for row in ((listed.get("packet") or {}).get("result") or {}).get("tools") or []]
    if tuple(names) != TOOL_NAMES:
        errors.append("tool_names")
    checks = {
        "request_setup_missing_need": classify_setup_packet(
            "request_setup_missing_need",
            _call("request_setup", {}, 8).get("packet") or {},
        ),
        "request_setup_empty_need": classify_setup_packet(
            "request_setup_empty_need",
            _call("request_setup", {"need": ""}, 9).get("packet") or {},
        ),
        "submit_task_empty_title": classify_setup_packet(
            "submit_task_empty_title",
            _call("submit_task", {"room_id": "r1", "title": ""}, 10).get("packet") or {},
        ),
        "set_role_missing_role": classify_setup_packet(
            "set_role_missing_role",
            _call("set_role", {"room_id": "r1"}, 11).get("packet") or {},
        ),
        "unknown_tool": classify_setup_packet(
            "unknown_tool",
            _call("no_such_tool", {}, 12).get("packet") or {},
        ),
        "malformed": classify_setup_packet(
            "malformed",
            _rpc(PAD_MCP, raw=b"{not json").get("packet") or {},
        ),
        "unknown_method": classify_setup_packet(
            "unknown_method",
            _rpc(
                PAD_MCP,
                {"jsonrpc": "2.0", "id": 13, "method": "no_such_method", "params": {}},
            ).get("packet")
            or {},
        ),
        "missing_name": classify_setup_packet(
            "missing_name",
            _rpc(
                PAD_MCP,
                {"jsonrpc": "2.0", "id": 14, "method": "tools/call", "params": {}},
            ).get("packet")
            or {},
        ),
    }
    for key, row in checks.items():
        if not row.get("ok"):
            errors.append(key)
    tooling = _call("list_custom_tooling", {}, 15).get("packet") or {}
    fp = first_party_ids(tooling)
    fp_count = structured_content(tooling).get("first_party_count")
    if "peer-worker" not in fp or fp_count != 3:
        errors.append("first_party")
    origin = _rpc(
        PAD_MCP,
        {
            "jsonrpc": "2.0",
            "id": 16,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt-origin", "version": "1"},
            },
        },
        origin="https://chatgpt.com",
    )
    origin_name = ((origin.get("packet") or {}).get("result") or {}).get("serverInfo") or {}
    if origin_name.get("name") != "titanmcp":
        errors.append("chatgpt_origin")
    commons = _rpc(
        COMMONS_MCP,
        {
            "jsonrpc": "2.0",
            "id": 17,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "titanmcp-setup-schema", "version": "1"},
            },
        },
    )
    commons_info = ((commons.get("packet") or {}).get("result") or {}).get("serverInfo") or {}
    if commons_info.get("name") != "commons" or commons_info.get("version") != "1.4.0":
        errors.append("commons_keep")
    html_ok = False
    html_bytes = 0
    try:
        req = urllib.request.Request(PAD_HTML, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            html_bytes = len(raw)
            html_ok = resp.status == 200 and b"registerTool" in raw and b"modelContext" in raw
    except Exception as visc:
        errors.append("html_" + type(visc).__name__)
    if not html_ok:
        errors.append("webmcp_html")
    return {
        "kind": "TITANMCP_SETUP_SCHEMA",
        "id": ID,
        "pad_initialize": {"status": init.get("status"), "name": info.get("name"), "version": info.get("version")},
        "commons_initialize": {
            "status": commons.get("status"),
            "name": commons_info.get("name"),
            "version": commons_info.get("version"),
        },
        "tool_count": len(names),
        "tool_names": names,
        "first_party": fp,
        "first_party_count": fp_count,
        "html_bytes": html_bytes,
        "html_registerTool": html_ok,
        "checks": {key: {"ok": row.get("ok"), "pin": row.get("pin")} for key, row in checks.items()},
        "did_not_remint": list(DO_NOT_REMINT),
        "sent": 0,
        "cash": 0,
        "errors": errors,
        "verdict": "MATCH" if not errors else "FINDER-FAILED",
        "note": (
            "Unique 1.4.5 remainder: request_setup need / NEED_REQUIRED, "
            "submit_task argument=task, set_role argument=agent_name, "
            "unknown tool JSON-RPC -32602. Commons /mcp KEEP. Devpost HOLD."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "TITANMCP_SETUP_SCHEMA",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "unknown": flag,
                        "note": f"{flag} FINDER-FAILED, never silent 0.",
                    },
                    sort_keys=True,
                )
            )
            return 1
    packet = measure()
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
