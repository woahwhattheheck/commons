#!/usr/bin/env python3
"""Unique titanmcp SAVE DRAFT / LOAD DRAFT KEEP remainder.

Peer webmcp-pad main `41d7167d` shipped live pad buttons. Commons has no pin.
Isolated canary stays green without reminting pad runtime, titanmcp.html,
or this seat's 1.4.5 setup-schema battery. leftover --bake/--deploy/--go
REFUSED sent=0. No competition resubmission.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from typing import Any


ID = "cursor-titanmcp-save-load-draft-20260930-01"
PAD_HTML = "https://webmcp-pad.vercel.app/webmcp"
COMMONS_MCP = "https://commons-spark-mcp.vercel.app/mcp"
PAD_MCP = "https://webmcp-pad.vercel.app/mcp"
REFUSE = ("--send", "--apply", "--go", "--autopilot", "--live", "--checkout", "--deploy", "--bake")
DO_NOT_REMINT = (
    "api/mcp.py",
    "commons_mcp.py",
    "titanmcp.html",
    "webmcp.html",
    ".github/workflows/webmcp-pad-production.yml",
    "host/titanmcp_setup_schema.py",
    "test_titanmcp_gpt_use_setup_schema.py",
    "p/cursor-titanmcp-setup-schema-20260929-01.md",
)

# Live pad.html 2026-09-30 after webmcp-pad `41d7167d`. Not a bake-sha pin.
BUTTON_MARKUP = (
    '<div class="actions">'
    '<button type="button" class="ghost" id="btn-save-draft">SAVE DRAFT</button>'
    '<button type="button" class="ghost" id="btn-load-draft">LOAD DRAFT</button>'
    "</div>"
)
DRAFT_FILE_INPUT = '<input type="file" id="draft-file" accept=".json,application/json" hidden/>'
REQUIRED_SNIPPETS = (
    BUTTON_MARKUP,
    DRAFT_FILE_INPUT,
    "registerTool",
    "titanmcp",
)


def classify_html(text: str) -> dict[str, Any]:
    missing = [row for row in REQUIRED_SNIPPETS if row not in text]
    return {
        "ok": not missing,
        "bytes": len(text.encode("utf-8") if isinstance(text, str) else text),
        "has_save_draft": "id=\"btn-save-draft\">SAVE DRAFT</button>" in text,
        "has_load_draft": "id=\"btn-load-draft\">LOAD DRAFT</button>" in text,
        "has_draft_file": "id=\"draft-file\"" in text,
        "has_register_tool": "registerTool" in text,
        "missing": missing,
    }


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "TITANMCP_SAVE_LOAD_DRAFT",
        "id": ID,
        "refused": flag,
        "sent": 0,
        "cash": 0,
        "invented_stripe_urls": False,
        "verdict": "REFUSED",
        "note": (
            f"{flag} REFUSED. Did not remint pad runtime, titanmcp.html, "
            "or setup-schema KEEP. leftover bake/deploy sent=0."
        ),
    }


def _rpc(url: str, obj: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(obj).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-03-26",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        packet = json.loads(resp.read().decode("utf-8"))
        info = (packet.get("result") or {}).get("serverInfo") or {}
        return {"status": resp.status, "name": info.get("name"), "version": info.get("version")}


def measure() -> dict[str, Any]:
    errors: list[str] = []
    req = urllib.request.Request(PAD_HTML, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        text = raw.decode("utf-8", "replace")
        html = classify_html(text)
        html["http_status"] = resp.status
        html["bytes"] = len(raw)
    if resp.status != 200 or not html["ok"]:
        errors.append("pad_html")
    pad = _rpc(
        PAD_MCP,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "titanmcp-save-load-draft", "version": "1"},
            },
        },
    )
    if pad.get("name") != "titanmcp" or pad.get("version") != "1.4.5":
        errors.append("pad_mcp")
    commons = _rpc(
        COMMONS_MCP,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "titanmcp-save-load-draft", "version": "1"},
            },
        },
    )
    if commons.get("name") != "commons" or commons.get("version") != "1.4.0":
        errors.append("commons_keep")
    return {
        "kind": "TITANMCP_SAVE_LOAD_DRAFT",
        "id": ID,
        "html": html,
        "pad_initialize": pad,
        "commons_initialize": commons,
        "did_not_remint": list(DO_NOT_REMINT),
        "sent": 0,
        "cash": 0,
        "errors": errors,
        "verdict": "MATCH" if not errors else "FINDER-FAILED",
        "note": (
            "Unique remainder: live pad SAVE DRAFT / LOAD DRAFT buttons + hidden "
            "draft-file input. Commons /mcp KEEP. No competition resubmission."
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
                        "kind": "TITANMCP_SAVE_LOAD_DRAFT",
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
