"""Command center tools shared through every existing equipment carrier."""
import os
from pathlib import Path

class CommandCenterEquipment:
    def __init__(self, center=None):
        self._center = center
    @property
    def center(self):
        if self._center is None:
            from .core import CommandCenter
            state = Path(os.environ.get("COMMONS_COMMAND_CENTER_STATE", str(Path.home() / ".commons" / "command-center")))
            self._center = CommandCenter(state, gateway_url=os.environ.get("COMMONS_COMMAND_CENTER_GATEWAY", "http://127.0.0.1:8878"))
        return self._center
    def tools(self):
        session_schema = {
            "type": "object", "required": ["id"], "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "description": "Stable ID for the existing session."},
                **{key: {"type": ["string", "null"]} for key in (
                    "label", "url", "provider", "model", "workspace", "observed_at",
                    "status", "objective", "resource_id", "expires_at", "notes")},
                "cpu": {"type": ["number", "string", "object", "null"], "description": "Observed CPU capacity, including structured vCPU metadata."},
                **{key: {"type": ["number", "null"]} for key in (
                    "ram_gib", "disk_gib", "disk_free_gib")},
                "gpu": {"type": ["string", "number", "object", "array", "null"]},
                "origin": {"type": ["string", "object", "null"]},
                **{key: {"type": ["string", "array", "object", "null"]} for key in (
                    "capabilities", "tools", "egress", "artifact_transport", "cost_source")},
                "lifetime": {"type": ["string", "number", "object", "null"]},
            },
        }
        budget_schema = {
            "type": "object", "required": ["id"], "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "description": "Stable ID for this budget, balance, or quota observation."},
                **{key: {"type": ["number", "null"], "minimum": 0} for key in (
                    "limit", "used", "balance", "remaining", "committed")},
                **{key: {"type": ["string", "null"]} for key in (
                    "label", "unit", "period", "observed_at", "source_url",
                    "provider", "kind", "currency", "notes")},
            },
        }
        runtime_schema = {
            "type": "object", "required": ["id", "gateway_url"], "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "description": "Stable ID for the existing shared gateway."},
                "label": {"type": "string"},
                "gateway_url": {"type": "string", "description": "Existing HTTP(S) gateway base URL exposing /v1/tools and /v1/tools/call."},
            },
        }
        specs = [
            ("state", "Read the entire operation: canonical resources, service tools, accounts, observed fleet, budgets, focus, and operation outcomes.", {"refresh": {"type": "boolean"}}, []),
            ("focus", "Set the shared objective and next action.", {"objective": {"type": "string"}, "next_action": {"type": "string"}}, ["objective"]),
            ("session", "Record an existing GPT, Claude, or other peer session and observed VM facts. Does not create a provider session.", {"session": session_schema}, ["session"]),
            ("budget", "Record an observed balance, quota, limit, or budget with its source and timestamp.", {"budget": budget_schema}, ["budget"]),
            ("runtime", "Register an existing shared tool gateway.", {"runtime": runtime_schema}, ["runtime"]),
            ("janny", "Assign limited housekeeping responsibility to an existing peer, without changing tool or credential access.", {"peer": {"type": "string"}}, ["peer"]),
            ("note", "Add an operational feed item with its original source link for shared visibility and reversible housekeeping.", {"title": {"type": "string"}, "body": {"type": "string"}, "source_url": {"type": "string"}, "source_ref": {"type": "string"}}, ["title", "body"]),
            ("moderate", "Hide or restore one item in the derived default feed with a reason, retaining its original.", {"event_id": {"type": "string"}, "hidden": {"type": "boolean", "description": "Desired derived-feed visibility: true hides the entry; false restores it."}, "action": {"type": "string", "description": "Legacy hide/restore alias; prefer hidden."}, "reason": {"type": "string"}}, ["event_id", "reason"]),
        ]
        result = []
        for name, description, properties, required in specs:
            if name != "state":
                properties = {"operation_id": {"type": "string", "description": "Stable ID; repeat exact payload on retry."}, **properties}
                required = ["operation_id"] + required
            result.append({"name": "command_center_" + name, "description": description, "inputSchema": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}})
        for tool in result:
            if tool["name"] == "command_center_moderate":
                tool["inputSchema"]["anyOf"] = [
                    {"required": ["hidden"]}, {"required": ["action"]}]
        return result
    def call(self, name, arguments):
        if name == "command_center_state":
            from .telemetry import with_host
            return with_host(self.center, self.center.state(refresh=bool(arguments.get("refresh", False))))
        names = {"focus": "focus", "session": "sessions", "budget": "budgets", "runtime": "runtimes", "janny": "janny", "note": "feed", "moderate": "feed/moderate"}
        suffix = name.removeprefix("command_center_")
        if suffix not in names:
            raise ValueError("unknown command center tool")
        return self.center.mutate(names[suffix], arguments)
