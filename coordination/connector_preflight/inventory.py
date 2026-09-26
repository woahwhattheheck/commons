"""Adapt a complete harness tool registry to the existing preflight contract.

This records exposure only. It performs no provider calls and invents no
authentication, permission, policy, or write-attempt result.
"""
from __future__ import annotations

from typing import Any

from .core import INPUT_SCHEMA, PreflightError, normalize_input, parse_utc, sha256_json

INVENTORY_SCHEMA = "commons.connector-tool-inventory/v1"
REQUIRED_WRITES = {
    "GitHub": ["create_blob", "create_tree", "create_commit", "create_branch",
               "update_ref", "create_file", "update_file", "create_pull_request",
               "merge_pull_request"],
    "Slack": ["slack_send_message", "slack_create_conversation", "slack_edit_message"],
}
PREFIXES = {
    "mcp__codex_apps__github_": "GitHub",
    "mcp__codex_apps__slack_": "Slack",
}
READ_VERBS = {"compare", "download", "fetch", "get", "list", "read", "search"}
WRITE_VERBS = {
    "add", "complete", "convert", "create", "delete", "dismiss", "edit", "enable",
    "invite", "join", "label", "leave", "lock", "mark", "merge", "remove", "reply",
    "request", "rerun", "resolve", "schedule", "send", "unlock", "unresolve", "update",
}


def snapshot_from_inventory(raw: Any) -> dict[str, Any]:
    """Preserve the capture's timestamp and completeness in a v1 snapshot.

    Tools can be full names or metadata objects with ``name``. For a new verb,
    a metadata row must provide READ/WRITE ``access`` from its actual schema;
    unknown verbs never silently become reads or disappear. Other providers'
    tools remain in the source digest but do not become GitHub/Slack actions.
    """
    if not isinstance(raw, dict) or raw.get("schema") != INVENTORY_SCHEMA:
        raise PreflightError(f"inventory schema must be {INVENTORY_SCHEMA}")
    observed_at = raw.get("observed_at")
    observed = parse_utc(observed_at, "inventory.observed_at")
    if type(raw.get("complete")) is not bool:
        raise PreflightError("inventory.complete must be an explicit boolean")
    # Do not silently upgrade a filtered tool search to complete discovery.
    if "query" not in raw:
        raise PreflightError("inventory.query must be null for an unfiltered registry or the search text")
    if raw["query"] is not None and (not isinstance(raw["query"], str) or not raw["query"].strip()):
        raise PreflightError("inventory.query must be null or nonempty search text")
    entries = raw.get("tools")
    if not isinstance(entries, list) or not entries:
        raise PreflightError("inventory.tools must be a nonempty complete registry array")
    actions = []
    names = set()
    for index, entry in enumerate(entries):
        name = entry if isinstance(entry, str) else entry.get("name") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name:
            raise PreflightError(f"inventory.tools[{index}] requires a nonempty tool name")
        if name in names:
            raise PreflightError(f"duplicate tool name: {name}")
        names.add(name)
        prefix = next((p for p in PREFIXES if name.startswith(p)), None)
        if prefix is None:
            continue
        action = name[len(prefix):]
        connector = PREFIXES[prefix]
        verb = action.removeprefix("slack_").split("_", 1)[0]
        inferred = "READ" if verb in READ_VERBS else "WRITE" if verb in WRITE_VERBS else None
        declared = entry.get("access") if isinstance(entry, dict) else None
        if declared is not None and (not isinstance(declared, str) or declared not in {"READ", "WRITE"}):
            raise PreflightError(f"{name}: access must be READ or WRITE")
        if declared is not None and inferred is not None and declared != inferred:
            raise PreflightError(f"{name}: access conflicts with the known operation")
        access = declared or inferred
        if access is None:
            raise PreflightError(f"{name}: inspect its schema and provide explicit READ/WRITE access")
        actions.append({"connector": connector, "name": action, "access": access})
    digest = sha256_json(raw)
    snapshot = {
        "schema": INPUT_SCHEMA,
        "snapshot_id": f"inventory-{digest[:24]}",
        "claim": "CAPABILITY_REPORT",
        "captured_at": observed_at,
        "policy": {"max_age_seconds": 3600, "required_actions": REQUIRED_WRITES},
        "discoveries": [{
            "request_id": f"discovery-{digest[:24]}",
            "requested_at": observed_at,
            "completed_at": observed_at,
            "paths": ["GitHub", "Slack"],
            "query": raw["query"],
            "complete": raw["complete"],
            "actions": actions,
            "evidence_sha256": digest,
        }],
        "attempts": [],
    }
    # Validate shape at capture time. CURRENT compilation remains responsible
    # for freshness; importing a retained inventory never re-dates its evidence.
    return normalize_input(snapshot, observed)
