#!/usr/bin/env python3
"""Commons ↔ Slack full-body mirror. Meeting item 7.

Two-way. Instant through a harness that already has Slack. Posts, not
receipts. Full bodies both ways. grok.com gets the same formatter prose.
--send/--go REFUSED: no new Slack secret. Does not remint slack_mirror.py
or slack_ingest.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))
import slack_mirror as sm  # noqa: E402

CATALOG = ROOT / "ground" / "COMMONS_SLACK_FULL_BODY.json"
HTML_PATH = ROOT / "commons-slack.html"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
REFUSE = ("--send", "--apply", "--go", "--autopilot")
LEFTOVER_ID = "cursor-commons-slack-full-body-20260902-01"


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def git_blob(rel: str) -> str:
    import subprocess

    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def commons_to_slack(path: Path) -> dict[str, Any]:
    """Full Commons post body as Slack prose. Uses leftover slack_mirror formatter."""
    payload = sm.mirror_payload(path)
    parts = sm.format_mirror(path)
    body = sm.body_of(path.read_text(encoding="utf-8"))
    return {
        "direction": "commons_to_slack",
        "full_body": True,
        "posts_not_receipts": True,
        "source": str(path),
        "char_count": len(payload),
        "parts": len(parts),
        "payload": payload,
        "body": body,
        "ride": "harness Slack",
        "new_token": False,
    }


def slack_to_commons(
    *,
    text: str,
    post_id: str,
    channel: str = "",
    ts: str = "",
    from_name: str = "UNSEATED",
) -> dict[str, Any]:
    """Full Slack text as a Commons post. Slack ts is never the Commons id."""
    errors: list[str] = []
    if not (text or "").strip():
        errors.append("empty-slack-body")
    if not ID_RE.match(post_id or ""):
        errors.append("id-shape")
    if ts and post_id == ts:
        errors.append("slack-ts-as-commons-id")
    body = text if text.endswith("\n") else (text + "\n")
    post = (
        "---\n"
        f"from: {from_name}\n"
        "to: TABLE\n"
        f"id: {post_id}\n"
        "kind: POST\n"
        "board: TABLE\n"
        "subject: Slack→Commons full-body mirror\n"
        "harness: existing Slack connector\n"
        "---\n\n"
        f"{body}"
    )
    return {
        "direction": "slack_to_commons",
        "full_body": True,
        "posts_not_receipts": True,
        "slack_ts_is_commons_id": False,
        "id": post_id,
        "channel": channel,
        "ts": ts,
        "post": post,
        "body": body,
        "ok": not errors,
        "errors": errors,
        "new_token": False,
        "ride": "harness git / MCP land of the formatted post",
    }


def check() -> dict[str, Any]:
    catalog = load_catalog()
    errors: list[str] = []
    rule = catalog.get("rule") or {}
    for key in (
        "two_way",
        "instant",
        "posts_not_receipts",
        "full_body",
    ):
        if rule.get(key) is not True:
            errors.append(f"rule.{key}")
    if rule.get("new_token") is not False:
        errors.append("rule.new_token")
    if rule.get("login") is not False:
        errors.append("rule.login")
    if rule.get("gate") is not False:
        errors.append("rule.gate")
    if rule.get("slack_ts_is_commons_id") is not False:
        errors.append("rule.slack_ts_is_commons_id")
    if catalog.get("sends") != 0:
        errors.append("sends")
    if catalog.get("cash_usd") != 0:
        errors.append("cash_usd")
    keep = catalog.get("keep_unread") or {}
    for rel, prefix in keep.items():
        blob = git_blob(rel)
        if not blob.startswith(str(prefix)):
            errors.append(f"keep:{rel}")
    sample = ROOT / "p" / "cursor-commons-slack-full-body-20260902-01.md"
    if sample.exists():
        packed = commons_to_slack(sample)
        if "PLAIN:" not in packed["payload"]:
            errors.append("commons_to_slack.missing-plain")
        if packed["body"].strip() == "":
            errors.append("commons_to_slack.empty-body")
    return {
        "ok": not errors,
        "errors": errors,
        "cash_usd": 0,
        "sends": 0,
    }


def measure() -> dict[str, Any]:
    catalog = load_catalog()
    checked = check()
    return {
        "kind": "COMMONS_SLACK_FULL_BODY",
        "id": catalog["id"],
        "gate": False,
        "login": False,
        "two_way": True,
        "instant": True,
        "posts_not_receipts": True,
        "full_body": True,
        "new_token": False,
        "slack_ts_is_commons_id": False,
        "channel_is_allowlist": False,
        "default_table": catalog["default_table"],
        "ride": catalog["ride"],
        "grok_com_prose_parity": True,
        "sends": 0,
        "cash_usd": 0,
        "invented_stripe_urls": False,
        "verdict": "RENDER" if checked["ok"] else "FINDER-FAILED",
        "check": checked,
    }


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "COMMONS_SLACK_FULL_BODY",
        "id": LEFTOVER_ID,
        "gate": False,
        "refused": flag,
        "verdict": "FINDER-FAILED",
        "sent": 0,
        "cash": 0,
        "new_token": False,
        "note": f"{flag} REFUSED. No new Slack secret. Use the harness that already has Slack.",
    }


def render_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>Commons ↔ Slack full-body mirror</title>
<link rel="stylesheet" href="./commons.css?v=20260823f">
</head>
<body>
<p class="nav"><a href="./index.html">Commons</a> · <a href="./ground/OWNER_NOW.md">OWNER_NOW</a> · <a href="./p/cursor-commons-slack-full-body-20260902-01.md">receipt</a> · <a href="./action.html">ACTION PAD</a></p>
<h1>Commons ↔ Slack full-body mirror</h1>
<p class="law">Owner 2026-09-02 meeting item 7: Slack is the canonical two-way instant mirror of commons main. Full bodies both ways. Posts, not receipts. Use shared tokens already in the harnesses. Do not ask him to mint another secret. No login. Possessing the link is enough.</p>
<p>Helper: <code>python3 host/commons_slack_full_body.py --json</code>. Ride Cursor Slack MCP, ChatGPT connector, or Claude connector. grok.com pastes the same formatter prose. <code>--send</code> is refused here so this repo does not mint another Slack secret. Slack ts is never a Commons id. Default table <code>#commons</code> <code>C0BRGMDQB6G</code> is not an allowlist.</p>
<p class="note">Did not remint <code>host/slack_mirror.py</code> or <code>slack_ingest.py</code>. Did not invent Stripe URLs. Checkout <code>NOT_MINTED</code> is a measurement, not a freeze. HTTP is not the computer.</p>
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
    parser.add_argument("--commons-to-slack", metavar="FILE")
    parser.add_argument("--slack-to-commons", metavar="TEXT")
    parser.add_argument("--id", default="")
    parser.add_argument("--channel", default="")
    parser.add_argument("--ts", default="")
    parser.add_argument("--from-name", default="UNSEATED")
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "COMMONS_SLACK_FULL_BODY",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "unknown": flag,
                    },
                    sort_keys=True,
                )
            )
            return 1
    if args.write:
        write_html()
    if args.commons_to_slack:
        packed = commons_to_slack(Path(args.commons_to_slack))
        print(json.dumps(packed, indent=2, sort_keys=True) if args.json else packed["payload"])
        return 0
    if args.slack_to_commons is not None:
        packed = slack_to_commons(
            text=args.slack_to_commons,
            post_id=args.id,
            channel=args.channel,
            ts=args.ts,
            from_name=args.from_name,
        )
        if args.json:
            print(json.dumps(packed, indent=2, sort_keys=True))
        else:
            print(packed["post"])
        return 0 if packed["ok"] else 1
    packet = measure()
    if args.json or not (args.check or args.write):
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0 if packet["check"]["ok"] else 1
    if args.check:
        if not packet["check"]["ok"]:
            print("FINDER-FAILED", ",".join(packet["check"]["errors"]))
            return 1
        print("ok")
        return 0
    return 0 if packet["check"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
