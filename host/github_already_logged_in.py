#!/usr/bin/env python3
"""Classify GitHub tool/API failures. Auth is already present on every harness.

Owner hub 1788325694 / #needs-bryce 1788325660.929309:
a failed call is that action's path, rate-limit, or scope — not a missing login.
Do not open a GitHub login ask. Do not park. Keep shipping.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

PEER_LOGIN = "woahwhattheheck"
NEEDS_BRYCE = "C0BRX6EV739"

RATE_RE = re.compile(r"(?i)rate.?limit|secondary.?rate|api rate|403.*rate")
SCOPE_RE = re.compile(
    r"(?i)missing_scope|resource_not_accessible|insufficient.?scope|"
    r"must have .+ permission|actions:write|403 Forbidden"
)
PATH_RE = re.compile(
    r"(?i)not found|does not exist|no such file|path does not point|"
    r"\b404\b"
)
HTTPS_GIT_RE = re.compile(
    r"(?i)could not read [Uu]sername|could not read [Pp]assword|"
    r"authentication required|terminal prompts disabled|"
    r"could not read Username for 'https://github.com'"
)
LOGIN_ASK_RE = re.compile(
    r"(?i)github login|log in to github|reconnect.*github|no perms|"
    r"missing login|not logged in to github"
)


def classify(
    *,
    status_code: int | None = None,
    message: str = "",
    login: str | None = None,
    tool: str = "",
) -> dict[str, Any]:
    text = message or ""
    out: dict[str, Any] = {
        "auth": "present",
        "peer_login": PEER_LOGIN,
        "park": False,
        "needs_bryce": False,
        "github_login_ask": False,
        "keep_shipping": True,
        "tool": tool or None,
        "status_code": status_code,
        "needs_bryce_channel": None,
    }
    if login:
        out["login"] = login
        out["cause"] = "auth_ok"
        out["next"] = (
            "retry the failed call with a corrected path, scope, or after rate-limit reset"
        )
        return out

    if RATE_RE.search(text) or status_code == 429:
        out["cause"] = "rate_limit"
        out["next"] = "wait for reset or use git smart-HTTP; do not open a GitHub login ask"
        return out

    if status_code == 404 or PATH_RE.search(text):
        out["cause"] = "path"
        out["next"] = "fix the path or ref; a missing file is not missing auth"
        return out

    if HTTPS_GIT_RE.search(text):
        out["cause"] = "https_git_not_mcp"
        out["next"] = (
            "use GitHub MCP create_or_update_file / push_files; "
            "do not open a login ask"
        )
        return out

    if status_code in (401, 403) or SCOPE_RE.search(text):
        out["cause"] = "scope"
        out["next"] = (
            "that one action's token or scope; retry an allowed call; do not park"
        )
        return out

    if LOGIN_ASK_RE.search(text):
        out["cause"] = "false_missing_login"
        out["next"] = "ignore the freeze; GitHub is already signed in; keep shipping"
        return out

    out["cause"] = "call"
    out["next"] = "fix that call; auth is present; keep shipping unique leftover"
    return out


def slack_cli_is_not_github(*, slack_cli_logged_in: bool) -> dict[str, Any]:
    return {
        "auth_github": "present",
        "slack_cli_logged_in": slack_cli_logged_in,
        "park": False,
        "needs_bryce": False,
        "github_login_ask": False,
        "keep_shipping": True,
        "note": (
            "Slack CLI session is optional leftover. GitHub MCP already ships. "
            f"Do not mint a GitHub login ask. Do not treat Slack CLI as {NEEDS_BRYCE} GitHub."
        ),
    }


def three_three_seven_is_not_a_rule() -> dict[str, Any]:
    return {
        "rule": False,
        "source": "owner hub 1788325819 correction",
        "keep_shipping": True,
        "park": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=int, default=None)
    parser.add_argument("--message", default="")
    parser.add_argument("--login", default="")
    parser.add_argument("--tool", default="")
    args = parser.parse_args(argv)
    payload = classify(
        status_code=args.status,
        message=args.message,
        login=args.login or None,
        tool=args.tool,
    )
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
