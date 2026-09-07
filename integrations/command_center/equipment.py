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
        source_schema = {
            "type": "object", "required": ["id", "provider", "observed_at", "coverage"],
            "description": "Selected source metadata, explicit stable scope and coverage; never raw bodies or credential values.",
            "properties": {
                **{key: {"type": "string"} for key in ("id", "provider", "observed_at")},
                "coverage": {"type": "object", "required": ["complete"], "properties": {
                    "complete": {"type": "boolean"}, "pagination_remaining": {}, "notes": {}}, "additionalProperties": False},
                **{key: {} for key in ("label", "sync_mode", "activity_as_of", "scope", "status", "error", "stale_after_seconds", "metadata", "refs", "url")},
            }, "additionalProperties": False,
        }
        specs = [
            ("state", "Read the entire operation: canonical resources, service tools, accounts, observed fleet, budgets, focus, and operation outcomes.", {"refresh": {"type": "boolean"}}, []),
            ("work_state", "Read connected work, source freshness and coverage, owner next actions, and direct refresh progress.", {"refresh": {"type": "boolean"}}, []),
            ("refresh_work", "Start one bounded read of configured GitHub and Slack sources, retaining previous observations during refresh. No model or new service is started.", {}, []),
            ("ingest", "Share selected work observations from an actual connector or native task road. Preserve provider timestamps, source scope, pagination and failures. Stable operation IDs make exact retries safe.", {"source": source_schema, "items": {"type": "array", "maxItems": 10000, "items": {"type": "object"}}}, ["source", "items"]),
            ("work_item", "Record owner priority, next action, or a prepared job against an exact observed work item. A prepared packet is not provider dispatch.", {"source_id": {"type": "string"}, "item_id": {"type": "string"}, "priority": {"type": ["string", "number", "null"]}, "next_action": {"type": ["string", "null"]}, "job": {"type": ["object", "null"]}}, ["source_id", "item_id"]),
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
            if name not in {"state", "work_state", "refresh_work"}:
                properties = {"operation_id": {"type": "string", "description": "Stable ID; repeat exact payload on retry."}, **properties}
                required = ["operation_id"] + required
            result.append({"name": "command_center_" + name, "description": description, "inputSchema": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}})
        for tool in result:
            if tool["name"] == "command_center_moderate":
                tool["inputSchema"]["anyOf"] = [
                    {"required": ["hidden"]}, {"required": ["action"]}]
        return result
    def call(self, name, arguments):
        if name == "command_center_work_state":
            return self.center.work_state(refresh=bool(arguments.get("refresh", False)))
        if name == "command_center_refresh_work":
            return self.center.refresh_work()
        if name == "command_center_ingest":
            return self.center.ingest_work(arguments)
        if name == "command_center_work_item":
            return {**self.center.update_work(arguments), "status": "completed"}
        if name == "command_center_state":
            from .telemetry import with_host
            return with_host(self.center, self.center.state(refresh=bool(arguments.get("refresh", False))))
        names = {"focus": "focus", "session": "sessions", "budget": "budgets", "runtime": "runtimes", "janny": "janny", "note": "feed", "moderate": "feed/moderate"}
        suffix = name.removeprefix("command_center_")
        if suffix not in names:
            raise ValueError("unknown command center tool")
        return self.center.mutate(names[suffix], arguments)
