#!/usr/bin/env python3
"""Slack-side custom-tool worker for @service tags.

Bryce 1788319997.911589: install the tools. This worker is the installed
runtime: read channel history, route @facebook (and the rest) through
slack_service_tag, drive what this process can, queue provider sessions on
#provider-sign-in. Missing tags never reject a Commons post. No secrets in git.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_drivers as drivers  # noqa: E402
import slack_service_tag as sst  # noqa: E402

JOB_MARKER = "service-tag-job"
DEFAULT_CHANNELS = ("C0BU51F1PL3", "C0BRGMDQB6G", "C0BUFA9G23E")
LOGIN_CHANNEL = "C0BUFA9G23E"
API = "https://slack.com/api/"


def load_install(catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    cat = catalog if catalog is not None else sst.load_catalog()
    install = cat.get("install") if isinstance(cat.get("install"), dict) else {}
    return {
        "login_channel_id": str(install.get("login_channel", {}).get("id") or LOGIN_CHANNEL),
        "job_marker": str(install.get("job_marker") or JOB_MARKER),
        "watch_channels": list(install.get("watch_channels") or DEFAULT_CHANNELS),
        "gate": False,
    }


def already_handled(replies: list[dict[str, Any]], marker: str = JOB_MARKER) -> bool:
    needle = str(marker or JOB_MARKER)
    for row in replies or []:
        text = str((row or {}).get("text") or "")
        if needle in text:
            return True
    return False


def connected_from_env(env: dict[str, str] | None = None) -> list[str]:
    src = env if env is not None else os.environ
    found = ["slack"]
    if str(src.get("GITHUB_TOKEN") or src.get("GH_TOKEN") or "").strip():
        found.append("github")
    if str(src.get("FACEBOOK_PAGE_ACCESS_TOKEN") or src.get("FACEBOOK_ACCESS_TOKEN") or "").strip():
        found.append("facebook")
    extra = str(src.get("SLACK_SERVICE_TAG_CONNECTED") or "").strip()
    for part in extra.split(","):
        name = part.strip().lower()
        if name and name not in found:
            found.append(name)
    return found


def posts_for_message(
    text: str,
    *,
    channel: str,
    ts: str,
    connected: list[str] | None = None,
    catalog: dict[str, Any] | None = None,
    drive: Callable[[str, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Turn one Slack message into chat.postMessage payloads. Never a Commons gate."""
    cat = catalog if catalog is not None else sst.load_catalog()
    install = load_install(cat)
    result = sst.route(text, connected=connected or ["slack"], catalog=cat)
    if not result.get("tags"):
        return []
    drive_fn = drive or drivers.drive
    marker = install["job_marker"]
    login = install["login_channel_id"]
    posts: list[dict[str, Any]] = []
    roads = [str(j.get("road")) for j in result.get("jobs") or []]
    posts.append(
        {
            "channel": channel,
            "thread_ts": ts,
            "text": (
                "%s tags=%s roads=%s gate=false\n"
                "Slack custom-tool job — remainder:\n%s"
                % (marker, ",".join(result["tags"]), ",".join(roads), result.get("body") or "")
            ),
        }
    )
    for job in result.get("slack_jobs") or []:
        kind = str(job.get("kind") or "")
        tag = str(job.get("tag") or "")
        body = str(job.get("text") or result.get("body") or "")
        if kind == "OWNER_BLOCKER":
            posts.append(
                {
                    "channel": login,
                    "thread_ts": None,
                    "text": (
                        "%s OWNER_BLOCKER @%s from %s ts=%s\n%s"
                        % (marker, tag, channel, ts, job.get("text") or "")
                    ),
                }
            )
        if kind == "SLACK_CUSTOM_TOOL":
            outcome = drive_fn(tag, body)
            peer_desk = str(job.get("peer_desk") or "")
            extra = (" peer_desk=%s this_process_tools=false" % peer_desk) if peer_desk else ""
            posts.append(
                {
                    "channel": channel,
                    "thread_ts": ts,
                    "text": (
                        "%s drive @%s ok=%s road=%s reason=%s%s"
                        % (
                            marker,
                            tag,
                            outcome.get("ok"),
                            outcome.get("road"),
                            outcome.get("reason") or "ran",
                            extra,
                        )
                    ),
                }
            )
            # Route already queued OWNER_BLOCKER for needs-session tags.
            # Do not double-post that queue when the driver also reports sign-in.
    return posts


def _api(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = urllib.parse.urlencode({k: v for k, v in payload.items() if v is not None}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        API + method,
        data=data,
        method="POST",
        headers={"Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": type(exc).__name__}
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_json"}
    return parsed if isinstance(parsed, dict) else {"ok": False, "error": "not_object"}


def poll_and_dispatch(
    token: str,
    *,
    channels: list[str] | None = None,
    connected: list[str] | None = None,
    catalog: dict[str, Any] | None = None,
    api: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    cat = catalog if catalog is not None else sst.load_catalog()
    install = load_install(cat)
    marker = install["job_marker"]
    watch = channels or install["watch_channels"]
    conn = connected if connected is not None else connected_from_env()
    call = api or _api
    handled = 0
    skipped = 0
    errors: list[str] = []
    for channel in watch:
        hist = call(token, "conversations.history", {"channel": channel, "limit": str(limit)})
        if not hist.get("ok"):
            errors.append("%s:%s" % (channel, hist.get("error") or "history_failed"))
            continue
        for msg in hist.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            ts = str(msg.get("ts") or "")
            text = str(msg.get("text") or "")
            if not ts or JOB_MARKER in text:
                continue
            if not sst.extract_tags(text, cat):
                continue
            replies_pack = call(
                token,
                "conversations.replies",
                {"channel": channel, "ts": ts, "limit": "20"},
            )
            replies = replies_pack.get("messages") or [] if replies_pack.get("ok") else []
            if already_handled(replies if isinstance(replies, list) else [], marker):
                skipped += 1
                continue
            for post in posts_for_message(
                text, channel=channel, ts=ts, connected=conn, catalog=cat
            ):
                sent = call(token, "chat.postMessage", post)
                if not sent.get("ok"):
                    errors.append("post:%s" % (sent.get("error") or "failed"))
            handled += 1
    return {
        "ok": not errors,
        "gate": False,
        "handled": handled,
        "skipped": skipped,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="", help="dispatch one body without polling")
    parser.add_argument("--channel", default="C0BU51F1PL3")
    parser.add_argument("--ts", default="")
    parser.add_argument("--connected", default="")
    parser.add_argument("--poll", action="store_true")
    args = parser.parse_args(argv)
    connected = [p.strip() for p in str(args.connected).split(",") if p.strip()] or connected_from_env()
    if args.poll:
        token = str(os.environ.get("SLACK_BOT_TOKEN") or "").strip()
        if not token:
            print("idle: SLACK_BOT_TOKEN is not configured", flush=True)
            return 0
        result = poll_and_dispatch(token, connected=connected)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") or result.get("handled") is not None else 1
    if args.text:
        posts = posts_for_message(args.text, channel=args.channel, ts=args.ts, connected=connected)
        print(json.dumps({"gate": False, "posts": posts}, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
