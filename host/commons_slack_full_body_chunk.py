#!/usr/bin/env python3
"""Item 7 complementary remainder: 4000-char channel + thread remainder.

Ride leftover Commons ↔ Slack full-body helper. Do not remint leftover
slack_mirror.py (5000-char split KEEP). First line is id and SHA. Cursor
advances only after a confirmed post. --send/--go REFUSED: no new Slack
secret. 5-minute job rides a harness that already posts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))
import commons_slack_full_body as leftover  # noqa: E402
import slack_mirror as sm  # noqa: E402

CATALOG = ROOT / "ground" / "COMMONS_SLACK_FULL_BODY_CHUNK.json"
HTML_PATH = ROOT / "commons-slack-chunk.html"
ID = "cursor-commons-slack-full-body-chunk-20260902-01"
CHANNEL_LIMIT = 4000
LEFTOVER_SLACK_LIMIT = 5000
REFUSE = ("--send", "--apply", "--go", "--autopilot")


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def header_line(path: Path) -> str:
    blob = subprocess.check_output(
        ["git", "hash-object", str(path)], text=True
    ).strip()
    return f"{path.stem} {blob}"


def format_channel_and_thread(path: Path) -> dict[str, Any]:
    packed = leftover.commons_to_slack(path)
    first = header_line(path)
    payload = first + "\n" + packed["payload"]
    parts = sm.chunks(payload, CHANNEL_LIMIT)
    channel = parts[0] if parts else ""
    thread = parts[1:]
    return {
        "kind": "COMMONS_SLACK_FULL_BODY_CHUNK",
        "id": ID,
        "post_id": path.stem,
        "blob": first.split(" ", 1)[1],
        "first_line": first,
        "channel_limit": CHANNEL_LIMIT,
        "leftover_slack_limit_keep": LEFTOVER_SLACK_LIMIT,
        "channel": channel,
        "thread_replies": thread,
        "channel_chars": len(channel),
        "thread_parts": len(thread),
        "full_body": True,
        "remainder_as_thread": bool(thread),
        "new_token": False,
        "cursor_advanced": False,
        "confirmed_post": False,
        "sends": 0,
    }


def pending_posts(since_sha: str) -> list[str]:
    out = subprocess.check_output(
        [
            "git",
            "log",
            "--diff-filter=A",
            "--name-only",
            "--pretty=format:",
            f"{since_sha}..HEAD",
            "--",
            "p",
        ],
        cwd=ROOT,
        text=True,
    )
    seen: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("p/") and line.endswith(".md") and line not in seen:
            seen.append(line)
    return seen


def measure() -> dict[str, Any]:
    catalog = load_catalog()
    errors: list[str] = []
    rule = catalog.get("rule") or {}
    if rule.get("channel_limit") != CHANNEL_LIMIT:
        errors.append("rule.channel_limit")
    if rule.get("remainder_as_thread") is not True:
        errors.append("rule.remainder_as_thread")
    if rule.get("id_and_sha_first_line") is not True:
        errors.append("rule.id_and_sha_first_line")
    if rule.get("cursor_advances_only_after_confirmed_post") is not True:
        errors.append("rule.cursor")
    if rule.get("five_minute_job") is not True:
        errors.append("rule.five_minute_job")
    if rule.get("login") is not False:
        errors.append("rule.login")
    if rule.get("gate") is not False:
        errors.append("rule.gate")
    if rule.get("new_token") is not False:
        errors.append("rule.new_token")
    if sm.SLACK_LIMIT != LEFTOVER_SLACK_LIMIT:
        errors.append("leftover.slack_limit_reminted")
    keep = catalog.get("keep_unread") or {}
    for rel, prefix in keep.items():
        blob = git_blob(rel)
        if not blob.startswith(str(prefix)):
            errors.append(f"keep:{rel}")
    last = str(catalog.get("last_mirrored_sha") or "")
    pending = pending_posts(last) if last else []
    sample = ROOT / "p" / "cursor-commons-slack-full-body-20260902-01.md"
    formatted = format_channel_and_thread(sample) if sample.exists() else {}
    if formatted:
        if not formatted["channel"].startswith(formatted["first_line"]):
            errors.append("first_line_missing")
        if formatted["channel_chars"] > CHANNEL_LIMIT:
            errors.append("channel_over_limit")
        if formatted["cursor_advanced"]:
            errors.append("cursor_advanced_without_confirm")
    return {
        "kind": "COMMONS_SLACK_FULL_BODY_CHUNK",
        "id": catalog["id"],
        "gate": False,
        "login": False,
        "channel_limit": CHANNEL_LIMIT,
        "leftover_slack_limit_keep": LEFTOVER_SLACK_LIMIT,
        "remainder_as_thread": True,
        "id_and_sha_first_line": True,
        "cursor_advances_only_after_confirmed_post": True,
        "five_minute_job": True,
        "new_token": False,
        "ride": catalog["ride"],
        "default_table": catalog["default_table"],
        "last_mirrored_sha": last,
        "pending_posts": pending,
        "cursor_advanced": False,
        "confirmed_post": False,
        "sends": 0,
        "cash_usd": 0,
        "verdict": "RENDER" if not errors else "FINDER-FAILED",
        "errors": errors,
        "sample": {
            "channel_chars": formatted.get("channel_chars"),
            "thread_parts": formatted.get("thread_parts"),
            "first_line": formatted.get("first_line"),
        },
    }


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "COMMONS_SLACK_FULL_BODY_CHUNK",
        "id": ID,
        "gate": False,
        "refused": flag,
        "verdict": "FINDER-FAILED",
        "sent": 0,
        "cash": 0,
        "cursor_advanced": False,
        "confirmed_post": False,
        "new_token": False,
        "note": f"{flag} REFUSED. Cursor does not advance. No new Slack secret. Use the harness that already posts.",
    }


def render_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>Commons → Slack 4000-char channel + thread remainder</title>
<link rel="stylesheet" href="./commons.css?v=20260823f">
</head>
<body>
<p class="nav"><a href="./index.html">Commons</a> · <a href="./commons-slack.html">full-body leftover</a> · <a href="./p/cursor-commons-slack-full-body-chunk-20260902-01.md">receipt</a> · <a href="./action.html">ACTION PAD</a></p>
<h1>4000-char channel + thread remainder</h1>
<p class="law">Owner 2026-09-02 meeting item 7 restatement: each new <code>p/*.md</code> on main since the last mirrored SHA posts its full body to #commons. First 4,000 characters in channel, remainder as thread replies, id and SHA on the first line. The cursor advances only after a confirmed post. A 5-minute job on a harness that already posts. Nothing new for Bryce to set up. No login. Possessing the link is enough.</p>
<p>Helper: <code>python3 host/commons_slack_full_body_chunk.py --json</code>. Rides leftover <code>host/commons_slack_full_body.py</code>. Leftover <code>slack_mirror.py</code> 5000-char split stays KEEP. 4000 vs 5000 is not a remint of that leftover. <code>--send</code> is refused here so this repo does not mint another Slack secret and the cursor does not advance.</p>
<p class="note">Did not remint leftover item 7. Did not steal Harborline <code>/qualify</code>. Did not steal the PC lane. Checkout <code>NOT_MINTED</code> is a measurement, not a freeze.</p>
</body>
</html>
"""


def write_html() -> None:
    HTML_PATH.write_text(render_html(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--format", metavar="FILE")
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "COMMONS_SLACK_FULL_BODY_CHUNK",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "cursor_advanced": False,
                        "unknown": flag,
                    },
                    sort_keys=True,
                )
            )
            return 1
    if args.write:
        write_html()
    if args.format:
        packed = format_channel_and_thread(Path(args.format))
        print(json.dumps(packed, indent=2, sort_keys=True) if args.json else packed["channel"])
        return 0
    packet = measure()
    if args.json or not (args.check or args.write):
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0 if packet["verdict"] == "RENDER" else 1
    if args.check:
        if packet["verdict"] != "RENDER":
            print("FINDER-FAILED", ",".join(packet["errors"]))
            return 1
        print("ok")
        return 0
    return 0 if packet["verdict"] == "RENDER" else 1


if __name__ == "__main__":
    raise SystemExit(main())
