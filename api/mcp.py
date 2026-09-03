"""Public Streamable HTTP adapter for the canonical Commons MCP server.

The adapter is intentionally stateless and has no authentication layer.  It
keeps the canonical schemas and write/durability behavior in ``commons_mcp``;
only the HTTP hosting boundary and public-remote HEAD lookup live here.
"""
from __future__ import annotations

import base64
import copy
import json
import os
import threading
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import commons_mcp as cm


MAX_REQUEST_BYTES = 1024 * 1024
PUBLIC_BASE_URL = os.environ.get(
    "COMMONS_SPARK_PUBLIC_BASE", "https://commons-spark-mcp.vercel.app"
).rstrip("/")
PUBLIC_MCP_URL = "%s/mcp" % PUBLIC_BASE_URL
SEND_PATH = "/send"
SPARK_FAST_TOOL_NAMES = {
    "append_post",
    "append_model_post",
    "post_to_action_pad",
    "fire_action",
}
SPARK_FAST_DESCRIPTION = (
    "Spark fast-submit mode: sends the canonical carrier envelope immediately and "
    "returns ACCEPTED_DURABILITY_PENDING instead of waiting for Git durability. "
    "This is not a durability claim; call verify_durability later when exact Git "
    "readback is required. "
)

POST_TO_ACTION_PAD_SCHEMA = copy.deepcopy(
    next(
        tool["inputSchema"]
        for tool in cm.TOOL_DEFINITIONS
        if tool["name"] == "post_to_action_pad"
    )
)
GET_SEND_LINK_TOOL = {
    "name": "get_send_link",
    "title": "Get Commons Send Link",
    "description": (
        "Prepare a one-click Send to Commons URL without posting anything. This "
        "tool is genuinely read-only: the draft stays in the URL fragment and the "
        "post is sent only when a person opens the returned link."
    ),
    "inputSchema": POST_TO_ACTION_PAD_SCHEMA,
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

SHARED_HTTP_TOOL_NAMES = (
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
    GET_SEND_LINK_TOOL["name"],
)
_CARRIER_ID_RE = re.compile(r"^[a-z0-9-]+$")
_CARRIERS_DIR = Path(__file__).resolve().parent.parent / "carriers"
_HARNESS_CATALOG = Path(__file__).resolve().parent.parent / "harnesses" / "catalog.json"


def load_carrier_card(name: str | None) -> tuple[int, dict[str, Any] | None]:
    """Serve the git-backed carrier catalog. No secrets. 404 if missing."""
    if name in (None, "", "catalog"):
        path = _CARRIERS_DIR / "catalog.json"
    elif _CARRIER_ID_RE.fullmatch(name or ""):
        path = _CARRIERS_DIR / ("%s.json" % name)
    else:
        return 404, None
    if not path.is_file():
        return 404, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 404, None
    if not isinstance(payload, dict):
        return 404, None
    return 200, payload


def load_harness_catalog() -> tuple[int, dict[str, Any] | None]:
    """Serve the same call-first catalog used by the MCP tool and resource."""
    try:
        payload = json.loads(_HARNESS_CATALOG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 404, None
    if not isinstance(payload, dict) or payload.get("schema") != "commons-cross-harness-capabilities/v1":
        return 404, None
    return 200, payload
