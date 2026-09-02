"""Skip ntfy only on Slack-connector issue bursts.

Ordinary GitHub issue ingest must still poll ntfy. Spark append_post returns
ACCEPTED_DURABILITY_PENDING after carrier 2xx; that is mail, not a page.
Measured 2026-09-02 event 2EiiAnFpfde5: issue runs skipped ntfy while
schedule was starved. Slack-connector bursts keep the skip so a connector
flood does not allocate one carrier poll per Slack message.
"""
from __future__ import annotations

import json
import os


def github_issue_event_body(read_text, event_path: str | None = None) -> str:
    path = event_path if event_path is not None else os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.isfile(path):
        return ""
    try:
        ev = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(ev, dict):
        return ""
    issue = ev.get("issue") or {}
    if not isinstance(issue, dict):
        return ""
    return str(issue.get("body") or "")


def skip_ntfy_on_slack_connector_issue(read_text, event_name: str | None = None) -> bool:
    name = event_name if event_name is not None else os.environ.get("GITHUB_EVENT_NAME")
    if name != "issues":
        return False
    return "carrier: slack-connector" in github_issue_event_body(read_text)
