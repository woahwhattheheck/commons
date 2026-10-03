#!/usr/bin/env python3
"""Unique titanmcp list_custom_tooling KEEP remainder.

Live list_custom_tooling with empty arguments is HTTP 200 JSON, MCP
ok:true, first_party_count 3, default_enabled false, detail summary.
First-party ids are titan-hands, harborline-origin, peer-worker.
Closed-schema extra minutes and extra q are MCP isError BAD_ARGUMENT
hint arguments.<name> is not allowed. Wrong-type id is MCP isError
BAD_ARGUMENT hint arguments.id must be string, not JSON-RPC -32602.
id=github is MCP isError OPTIONAL_CAPABILITY_NOT_FOUND, not a catalog
GitHub row. Commons /mcp KEEP has no list_custom_tooling. Isolated
classifier stays green without reminting pad runtime, Latch
titanmcp.html, setup-schema, SAVE/LOAD DRAFT, GET /mcp identity, Origin
pair, list_messages cursor, unknown after=, create_play_token,
consent-attach, get_operator, MESSAGE_CURSOR_NOT_FOUND, get_connector,
check_subscription, list_connectors, or list_research_power batteries.
leftover --bake/--deploy/--go REFUSED sent=0. No competition resubmission.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


ID = "cursor-titanmcp-list-custom-tooling-20261003-01"
PAD_MCP = "https://webmcp-pad.vercel.app/mcp"
COMMONS_MCP = "https://commons-spark-mcp.vercel.app/mcp"
REFUSE = ("--send", "--apply", "--go", "--autopilot", "--live", "--checkout", "--deploy", "--bake")
FIRST_PARTY = ("titan-hands", "harborline-origin", "peer-worker")
BUNDLES = (
    "titan_hands",
    "lda_pfc_instruments",
    "browser_computer_use",
    "desktop_computer_use",
)
DO_NOT_REMINT = (
    "api/mcp.py",
    "commons_mcp.py",
    "titanmcp.html",
    "webmcp.html",
    ".github/workflows/webmcp-pad-production.yml",
    "host/titanmcp_setup_schema.py",
    "host/titanmcp_save_load_draft.py",
    "host/titanmcp_get_mcp_identity.py",
    "host/titanmcp_origin_pair.py",
    "host/titanmcp_list_messages_cursor.py",
    "host/titanmcp_unknown_after.py",
    "host/titanmcp_play_token.py",
    "host/titanmcp_consent_attach.py",
    "host/titanmcp_get_operator.py",
    "host/titanmcp_message_cursor_not_found.py",
    "host/titanmcp_get_connector.py",
    "host/titanmcp_check_subscription.py",
    "host/titanmcp_list_connectors.py",
    "host/titanmcp_list_research_power.py",
    "p/cursor-titanmcp-setup-schema-20260929-01.md",
    "p/cursor-titanmcp-save-load-draft-20260930-01.md",
    "p/cursor-titanmcp-get-mcp-identity-20261001-01.md",
    "p/cursor-titanmcp-origin-pair-20261001-01.md",
    "p/cursor-titanmcp-list-messages-cursor-20261001-01.md",
    "p/cursor-titanmcp-unknown-after-20261001-01.md",
    "p/cursor-titanmcp-play-token-20261002-01.md",
    "p/cursor-titanmcp-consent-attach-20261002-01.md",
    "p/cursor-titanmcp-get-operator-20261002-01.md",
    "p/cursor-titanmcp-message-cursor-not-found-20261003-01.md",
    "p/cursor-titanmcp-get-connector-20261003-01.md",
    "p/cursor-titanmcp-check-subscription-20261003-01.md",
    "p/cursor-titanmcp-list-connectors-20261003-01.md",
    "p/cursor-titanmcp-list-research-power-20261003-01.md",
)


def structured_content(packet: dict[str, Any]) -> dict[str, Any]:
    result = packet.get("result")
    if not isinstance(result, dict):
        return {}
    sc = result.get("structuredContent")
    return sc if isinstance(sc, dict) else {}


def jsonrpc_error(packet: dict[str, Any]) -> dict[str, Any]:
    err = packet.get("error")
    return err if isinstance(err, dict) else {}


def _rpc(url: str, obj: dict[str, Any], *, origin: str = "https://chatgpt.com") -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
        "User-Agent": "titanmcp-list-custom-tooling",
    }
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(
        url,
        data=json.dumps(obj).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "packet": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            packet = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            packet = {"raw": raw[:200].decode("utf-8", "replace")}
        return {"status": exc.code, "packet": packet}


def _call(name: str, arguments: dict[str, Any], request_id: int) -> dict[str, Any]:
    return _rpc(
        PAD_MCP,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )


def classify_empty(packet: dict[str, Any], status: int) -> dict[str, Any]:
    err = jsonrpc_error(packet)
    result = packet.get("result") if isinstance(packet.get("result"), dict) else {}
    sc = structured_content(packet)
    first_party = sc.get("first_party") if isinstance(sc.get("first_party"), list) else []
    first_ids = tuple(
        row.get("id") for row in first_party if isinstance(row, dict)
    )
    tooling = sc.get("custom_tooling") if isinstance(sc.get("custom_tooling"), dict) else {}
    bundles = tooling.get("bundles") if isinstance(tooling.get("bundles"), list) else []
    bundle_ids = tuple(row.get("id") for row in bundles if isinstance(row, dict))
    pointer = sc.get("catalog_pointer") if isinstance(sc.get("catalog_pointer"), dict) else {}
    ok = (
        status == 200
        and not err
        and result.get("isError") is not True
        and sc.get("ok") is True
        and sc.get("first_party_count") == 3
        and sc.get("default_enabled") is False
        and sc.get("detail") == "summary"
        and sc.get("kind") == "optional_capabilities"
        and sc.get("product") == "titanmcp"
        and first_ids == FIRST_PARTY
        and bundle_ids == BUNDLES
        and pointer.get("path") == "connectors/custom_tooling.json"
        and pointer.get("policy") == "CLOSED_DOOR_CONSENT"
        and pointer.get("default_enabled") is False
        and err.get("code") != -32602
    )
    return {
        "ok": ok,
        "status": status,
        "jsonrpc_code": err.get("code"),
        "is_error": result.get("isError"),
        "sc_ok": sc.get("ok"),
        "first_party_count": sc.get("first_party_count"),
        "default_enabled": sc.get("default_enabled"),
        "detail": sc.get("detail"),
        "first_party_ids": list(first_ids),
        "bundle_ids": list(bundle_ids),
        "catalog_path": pointer.get("path"),
        "not_jsonrpc_32602": err.get("code") != -32602,
    }


def classify_github_not_found(packet: dict[str, Any], status: int) -> dict[str, Any]:
    err = jsonrpc_error(packet)
    result = packet.get("result") if isinstance(packet.get("result"), dict) else {}
    sc = structured_content(packet)
    ok = (
        status == 200
        and not err
        and result.get("isError") is True
        and sc.get("ok") is False
        and sc.get("error") == "OPTIONAL_CAPABILITY_NOT_FOUND"
        and sc.get("id") == "github"
        and err.get("code") != -32602
    )
    return {
        "ok": ok,
        "status": status,
        "jsonrpc_code": err.get("code"),
        "is_error": result.get("isError"),
        "error": sc.get("error"),
        "id": sc.get("id"),
        "not_jsonrpc_32602": err.get("code") != -32602,
    }


def classify_must_be_string(packet: dict[str, Any], status: int, argument: str) -> dict[str, Any]:
    err = jsonrpc_error(packet)
    result = packet.get("result") if isinstance(packet.get("result"), dict) else {}
    sc = structured_content(packet)
    hint = str(sc.get("hint") or "")
    ok = (
        status == 200
        and not err
        and result.get("isError") is True
        and sc.get("ok") is False
        and sc.get("error") == "BAD_ARGUMENT"
        and sc.get("argument") == argument
        and f"arguments.{argument} must be string" in hint
        and err.get("code") != -32602
    )
    return {
        "ok": ok,
        "status": status,
        "jsonrpc_code": err.get("code"),
        "is_error": result.get("isError"),
        "error": sc.get("error"),
        "argument": sc.get("argument"),
        "hint": sc.get("hint"),
        "not_jsonrpc_32602": err.get("code") != -32602,
    }


def classify_not_allowed(packet: dict[str, Any], status: int, argument: str) -> dict[str, Any]:
    err = jsonrpc_error(packet)
    result = packet.get("result") if isinstance(packet.get("result"), dict) else {}
    sc = structured_content(packet)
    hint = str(sc.get("hint") or "")
    ok = (
        status == 200
        and not err
        and result.get("isError") is True
        and sc.get("ok") is False
        and sc.get("error") == "BAD_ARGUMENT"
        and sc.get("argument") == argument
        and f"arguments.{argument} is not allowed" in hint
        and err.get("code") != -32602
    )
    return {
        "ok": ok,
        "status": status,
        "jsonrpc_code": err.get("code"),
        "is_error": result.get("isError"),
        "error": sc.get("error"),
        "argument": sc.get("argument"),
        "hint": sc.get("hint"),
        "not_jsonrpc_32602": err.get("code") != -32602,
    }


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "TITANMCP_LIST_CUSTOM_TOOLING",
        "id": ID,
        "refused": flag,
        "sent": 0,
        "cash": 0,
        "invented_stripe_urls": False,
        "verdict": "REFUSED",
        "note": (
            f"{flag} REFUSED. Did not remint pad runtime, titanmcp.html, "
            "setup-schema, SAVE/LOAD DRAFT, GET /mcp identity, Origin pair, "
            "list_messages cursor, unknown after=, create_play_token, "
            "consent-attach, get_operator, MESSAGE_CURSOR_NOT_FOUND, "
            "get_connector, check_subscription, list_connectors, or "
            "list_research_power KEEP. leftover bake/deploy sent=0."
        ),
    }


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
                "clientInfo": {"name": "titanmcp-list-custom-tooling", "version": "1"},
            },
        },
    )
    info = ((init.get("packet") or {}).get("result") or {}).get("serverInfo") or {}
    if info.get("name") != "titanmcp" or info.get("version") != "1.4.5":
        errors.append("pad_mcp")

    listed = _rpc(PAD_MCP, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = [
        row.get("name")
        for row in ((listed.get("packet") or {}).get("result") or {}).get("tools") or []
        if isinstance(row, dict)
    ]
    if "list_custom_tooling" not in names:
        errors.append("pad_tool")

    empty = _call("list_custom_tooling", {}, 3)
    empty_row = classify_empty(empty.get("packet") or {}, empty.get("status") or 0)
    if not empty_row["ok"]:
        errors.append("empty")

    extra_minutes = _call("list_custom_tooling", {"minutes": 1}, 4)
    extra_minutes_row = classify_not_allowed(
        extra_minutes.get("packet") or {}, extra_minutes.get("status") or 0, "minutes"
    )
    if not extra_minutes_row["ok"]:
        errors.append("extra_minutes")

    extra_q = _call("list_custom_tooling", {"q": "github"}, 5)
    extra_q_row = classify_not_allowed(extra_q.get("packet") or {}, extra_q.get("status") or 0, "q")
    if not extra_q_row["ok"]:
        errors.append("extra_q")

    wrong_id = _call("list_custom_tooling", {"id": 1}, 6)
    wrong_id_row = classify_must_be_string(
        wrong_id.get("packet") or {}, wrong_id.get("status") or 0, "id"
    )
    if not wrong_id_row["ok"]:
        errors.append("wrong_type_id")

    github = _call("list_custom_tooling", {"id": "github"}, 7)
    github_row = classify_github_not_found(github.get("packet") or {}, github.get("status") or 0)
    if not github_row["ok"]:
        errors.append("github_not_found")

    commons_init = _rpc(
        COMMONS_MCP,
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "titanmcp-list-custom-tooling", "version": "1"},
            },
        },
        origin="",
    )
    commons_info = ((commons_init.get("packet") or {}).get("result") or {}).get("serverInfo") or {}
    commons_listed = _rpc(
        COMMONS_MCP,
        {"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}},
        origin="",
    )
    commons_names = [
        row.get("name")
        for row in ((commons_listed.get("packet") or {}).get("result") or {}).get("tools") or []
        if isinstance(row, dict)
    ]
    if (
        commons_info.get("name") != "commons"
        or commons_info.get("version") != "1.4.0"
        or "list_custom_tooling" in commons_names
    ):
        errors.append("commons_keep")

    return {
        "kind": "TITANMCP_LIST_CUSTOM_TOOLING",
        "id": ID,
        "pad_initialize": {"name": info.get("name"), "version": info.get("version")},
        "commons_initialize": {
            "name": commons_info.get("name"),
            "version": commons_info.get("version"),
        },
        "pad_has_list_custom_tooling": "list_custom_tooling" in names,
        "commons_has_list_custom_tooling": "list_custom_tooling" in commons_names,
        "empty_arguments": empty_row,
        "extra_minutes": extra_minutes_row,
        "extra_q": extra_q_row,
        "wrong_type_id": wrong_id_row,
        "github_not_found": github_row,
        "did_not_remint": list(DO_NOT_REMINT),
        "sent": 0,
        "cash": 0,
        "errors": errors,
        "verdict": "MATCH" if not errors else "FINDER-FAILED",
        "note": (
            "Unique remainder after list_research_power KEEP: "
            "list_custom_tooling empty arguments is 200 ok:true "
            "first_party_count 3 default_enabled false. Extra minutes and "
            "extra q are MCP isError BAD_ARGUMENT is not allowed. Wrong-type "
            "id is MCP isError BAD_ARGUMENT must be string, not JSON-RPC "
            "-32602. id=github is OPTIONAL_CAPABILITY_NOT_FOUND. Commons "
            "/mcp KEEP has no list_custom_tooling. No competition resubmission."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    del args
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "TITANMCP_LIST_CUSTOM_TOOLING",
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
