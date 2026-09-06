"""Native client hook for Commons/Slack publication; never schedules peers."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# Installer places the shared module beside this hook; repository use resolves
# the same source, without a claim vault, credentials, network or background job.
_directory = Path(__file__).resolve().parent
sys.path.insert(0, str(_directory if (_directory / "commons_publication_policy.py").is_file()
                      else _directory.parents[1]))
from commons_publication_policy import POLICY_CONTEXT, check_publication


def publication_verdict(event: dict) -> dict | None:
    """Select actual publication arguments across native MCP event formats."""
    tool = str(event.get("tool_name") or "").lower()
    args = event.get("tool_input") or {}
    # Cursor beforeMCPExecution supplies JSON text; generic/native tool hooks
    # supply an object. Parsing is in memory and never logs submitted content.
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            return None
    if not isinstance(args, dict):
        return None
    mcp = event.get("mcp_context") or {}
    if not isinstance(mcp, dict):
        mcp = {}
    provider = " ".join(str(value or "") for value in (
        tool, event.get("mcp_server_name"), event.get("mcp_server_url"),
        event.get("url"), mcp.get("server_name"), mcp.get("server_url"),
    )).lower()
    managed_tool = bool(re.search(r"(?:commons|slack)", provider))
    # GitHub connector names identify the provider, not the destination.
    # Cover direct Commons issues/comments as well as Commons-branded tools.
    github_commons = "github" in provider and (any(
        "woahwhattheheck/commons" in str(args.get(key, "")).lower()
        for key in ("repository_full_name", "repo_full_name", "repository", "repo", "url", "issue_url", "pull_request_url")
    ) or (str(args.get("owner", "")).lower() == "woahwhattheheck"
          and str(args.get("repo", "")).lower() == "commons"))
    if not (managed_tool or github_commons):
        return None
    if not re.search(r"(?:post|send|append|publish|write|fire_action|update_message|chat[._]update|create_issue|update_issue|comment|create_pull_request|update_pull_request)", tool):
        return None
    # Flatten textual Slack blocks and attachment text as well as ordinary
    # Commons bodies. Values are held in memory and never included in output.
    def content(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"body", "content", "text", "message", "payload", "speech", "model_packet", "subject", "title", "blocks", "attachments", "fields", "elements"}:
                    yield from content(item)
        elif isinstance(value, list):
            for item in value:
                yield from content(item)
    return check_publication("\n".join(content(args)))


def handle(event: dict) -> dict:
    name = str(event.get("hook_event_name") or "")
    if name in {"SessionStart", "UserPromptSubmit"}:
        return {"hookSpecificOutput": {"hookEventName": name,
                "additionalContext": "When working with Commons or Slack: " + POLICY_CONTEXT}}
    if name != "PreToolUse":
        return {}
    verdict = publication_verdict(event)
    if verdict is None or verdict["allowed"]:
        return {}
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": verdict["message"]}}


if __name__ == "__main__":
    event = json.load(sys.stdin)
    print(json.dumps(handle(event), ensure_ascii=False))
