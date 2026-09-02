#!/usr/bin/env python3
"""Classify one GitHub HTTP/MCP failure as that call, not a missing login.

Hub 1788325694.170879: every harness is already logged into GitHub.
A failed tool call is the call/path/rate-limit/scope of that one action.
Do not open another GitHub login ask. Do not park waiting for Bryce
to log in. Keep shipping. Not a Commons gate.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LAW = ROOT / "ground" / "GITHUB_CALL_NOT_LOGIN.json"

VERDICTS = (
    "OK",
    "CALL_FAILED",
    "RATE_LIMITED",
    "PATH_WRONG",
    "SCOPE_OF_ACTION",
    "UNKNOWN",
)
NEVER_VERDICT = "MISSING_LOGIN_FREEZE"
SCOPE_ACTION_MARKERS = (
    "workflow_dispatch",
    "createworkflowdispatch",
    "actions.createworkflowdispatch",
)
ALTERNATE_ROADS = (
    "unique-push HEAD:main",
    "contents API PUT",
    "git data API",
    "current-main git",
)

_PROHIBITION_CLAUSE = re.compile(
    r"\b(?:do not|don't|never|stop)\b(?:\s+\w+){0,16}\s+"
    r"(?:open another github login ask|"
    r"park work waiting for bryce to (?:['\"]log in['\"]|log in)|"
    r"open a github login ask)",
    re.IGNORECASE,
)
_ASK_NEEDLES = (
    "please log in to github",
    "need bryce to log in",
    "waiting for bryce to log in",
    "no github login",
    "no github perms",
    "open a github login ask",
    "park waiting for github login",
)


def load_law(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_LAW
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("law is not an object")
    return data


def opens_github_login_ask(text: str) -> bool:
    """True when a draft asks for a GitHub login or parks on a missing login.

    Owner prohibition text that repeats 'do not open another GitHub login ask'
    is not itself an ask.
    """
    compact = " ".join((text or "").lower().split())
    stripped = _PROHIBITION_CLAUSE.sub(" ", compact)
    stripped = " ".join(stripped.split())
    return any(needle in stripped for needle in _ASK_NEEDLES)


def _status_int(status: int | str | None) -> int | None:
    if status is None or status == "":
        return None
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def classify(
    status: int | str | None = None,
    action: str = "",
    message: str = "",
) -> dict[str, Any]:
    """One GitHub failure is that action. login_ask stays false."""
    law = load_law()
    code = _status_int(status)
    action_l = str(action or "").strip().lower()
    message_l = str(message or "").lower()
    blob = f"{action_l} {message_l}".strip()
    scoped = any(marker in blob for marker in SCOPE_ACTION_MARKERS)

    verdict = "UNKNOWN"
    if code is not None:
        if 200 <= code < 300:
            verdict = "OK"
        elif code == 429 or "rate limit" in blob:
            verdict = "RATE_LIMITED"
        elif code == 404:
            verdict = "PATH_WRONG"
        elif scoped and code in (401, 403, 422):
            verdict = "SCOPE_OF_ACTION"
        elif code >= 400:
            verdict = "CALL_FAILED"
        else:
            verdict = "UNKNOWN"
    elif "rate limit" in blob:
        verdict = "RATE_LIMITED"

    roads = list(law.get("alternate_roads") or ALTERNATE_ROADS)
    if verdict == "OK":
        roads = []

    return {
        "verdict": verdict,
        "status": code,
        "action": str(action or ""),
        "gate": False,
        "commons_admission": False,
        "login_ask": False,
        "park_for_owner_login": False,
        "freeze": False,
        "github_login": str(law.get("harness_github_login") or "already_present"),
        "never_verdict": NEVER_VERDICT,
        "one_failed_call": str(
            law.get("one_failed_call") or "that_action_not_missing_login"
        ),
        "alternate_roads": roads,
        "keep_shipping": True,
        "law_id": str(law.get("id") or ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", default="", help="HTTP status from the failed call")
    parser.add_argument("--action", default="", help="tool or endpoint name")
    parser.add_argument("--message", default="", help="error body or tool message")
    parser.add_argument("--draft", default="", help="draft Slack/post text to scan")
    parser.add_argument("--law", default="", help="override law path")
    args = parser.parse_args(argv)
    if args.law:
        load_law(Path(args.law))
    result: dict[str, Any]
    if args.draft and not args.status and not args.action:
        result = {
            "opens_github_login_ask": opens_github_login_ask(args.draft),
            "login_ask": False,
            "gate": False,
        }
    else:
        result = classify(
            status=args.status or None,
            action=args.action,
            message=args.message,
        )
        if args.draft:
            result["opens_github_login_ask"] = opens_github_login_ask(args.draft)
    print(json.dumps(result, indent=2))
    print("", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
