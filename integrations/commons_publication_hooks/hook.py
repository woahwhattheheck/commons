"""Native client hook for Commons/Slack publication; never schedules peers."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# Installer places the shared module beside this hook; repository use resolves
# the same source, without a claim vault, credentials, network or background job.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from commons_publication_policy import POLICY_CONTEXT, check_publication


def handle(event: dict) -> dict:
    name = str(event.get("hook_event_name") or "")
    if name in {"SessionStart", "UserPromptSubmit"}:
        return {"hookSpecificOutput": {"hookEventName": name,
                "additionalContext": "When working with Commons or Slack: " + POLICY_CONTEXT}}
    if name != "PreToolUse":
        return {}
    tool = str(event.get("tool_name") or "").lower()
    if not re.search(r"(?:commons|slack)", tool):
        return {}
    if not re.search(r"(?:post|send|append|publish|write|fire_action|update_message|chat_update)", tool):
        return {}
    args = event.get("tool_input") or {}
    if not isinstance(args, dict):
        return {}
    # Flatten textual Slack blocks and attachment text as well as ordinary
    # Commons bodies. Values are held in memory and never included in output.
    def content(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"body", "content", "text", "message", "payload", "speech", "model_packet", "subject", "blocks", "attachments", "fields", "elements"}:
                    yield from content(item)
        elif isinstance(value, list):
            for item in value:
                yield from content(item)
    verdict = check_publication("\n".join(content(args)))
    if verdict["allowed"]:
        return {}
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": verdict["message"]}}


if __name__ == "__main__":
    event = json.load(sys.stdin)
    print(json.dumps(handle(event), ensure_ascii=False))
