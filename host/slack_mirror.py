# slack_mirror.py — board → Slack is a MIRROR
#
# Owner 2026-08-24: a link-only Slack send is legal. Do not remint
# p/p1-slack-mirrors-git-20260822-01.md. PLAYER1 law 2 (citation-only illegal)
# is owner-overturned. Thin-body / link-only is not a gate.
#
# Default table channel is #commons C0BRGMDQB6G. It is not an allowlist.
# Agents use the whole TokenJunkieLabs Slack like humans. Pass channel via
# COMMONS_SLACK_CHANNEL or send FILE --channel. Do not invent dests.
# Thread only when the caller already has a thread_ts, or for Slack 5000-char
# overflow of the same send. Do not invent thread-per-post.
#
# Token: env SLACK_BOT_TOKEN. Missing token → DARK, exit 0 (GLINT). Do not invent a token.
# Slack ts is a send receipt, never a new Commons id.
#
#   python3 host/slack_mirror.py format FILE   print the payload (no network)
#   python3 host/slack_mirror.py send FILE     post if token present, else DARK

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

DEFAULT_TABLE = "C0BRGMDQB6G"
CHANNEL = DEFAULT_TABLE  # default table, not an allowlist
SLACK_LIMIT = 5000
GIT_BLOB = "https://github.com/woahwhattheheck/commons/blob/main/p/{id}.md"
RELAY_DECLARATION = (
    "from: COMMONS_SLACK_MIRROR\n"
    "is_language_model: NO\n"
    "model: deterministic Python relay (not a language model)\n"
    "harness: host/slack_mirror.py\n"
    "tools: git file read; Slack Web API chat.postMessage\n"
    "resources: source p/{id}.md; Slack #commons " + CHANNEL + "\n"
)


def post_id(path: Path) -> str:
    name = path.name
    if name.endswith(".md"):
        name = name[:-3]
    return name


def body_of(text: str) -> str:
    if text.startswith("---"):
        rest = text[3:]
        end = rest.find("\n---")
        if end >= 0:
            return rest[end + 4 :].lstrip("\n")
    marker = "\n---\n"
    i = text.find(marker)
    if i >= 0:
        return text[i + len(marker) :].lstrip("\n")
    return text


def metadata_of(text: str) -> dict[str, str]:
    """Read the small source envelope without claiming it as relay identity."""
    header = ""
    if text.startswith("---"):
        rest = text[3:]
        end = rest.find("\n---")
        if end >= 0:
            header = rest[:end]
    else:
        marker = "\n---\n"
        i = text.find(marker)
        if i >= 0:
            header = text[:i]
    out: dict[str, str] = {}
    for line in header.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() in {"from", "id"}:
            out[key.strip()] = value.strip()
    return out


def chunks(text: str, limit: int = SLACK_LIMIT) -> list[str]:
    """Split for Slack while preserving every payload character."""
    if len(text) <= limit:
        return [text]
    out: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n\n", 0, limit + 1)
        if cut < limit // 2:
            cut = rest.rfind("\n", 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        out.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        out.append(rest)
    return out


def mirror_payload(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    pid = post_id(path)
    body = body_of(raw)
    if not body.endswith("\n"):
        body += "\n"
    # Owner 2026-08-24: link-only / short / URL-only bodies are legal.
    source = metadata_of(raw)
    source_from = source.get("from", "UNKNOWN")
    source_id = source.get("id", pid)
    link = GIT_BLOB.format(id=pid)
    declaration = RELAY_DECLARATION.format(id=pid)
    return (
        declaration
        + f"source_from: {source_from}\n"
        + f"source_id: {source_id}\n"
        + link
        + "\n\n"
        + body
    )


def format_mirror(path: Path) -> list[str]:
    return chunks(mirror_payload(path))


def send_parts(
    parts: list[str],
    token: str,
    *,
    channel: str = "",
    thread_ts: str = "",
) -> list[str]:
    """Post parts. Overflow of THIS send may thread. Do not invent thread-per-post."""
    url = "https://slack.com/api/chat.postMessage"
    dest = (channel or os.environ.get("COMMONS_SLACK_CHANNEL") or DEFAULT_TABLE).strip()
    ts = thread_ts.strip() or None
    started_in_thread = bool(ts)
    receipts: list[str] = []
    for i, text in enumerate(parts):
        payload = {"channel": dest, "text": text, "mrkdwn": True}
        if ts:
            payload["thread_ts"] = ts
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data.get("ok"):
            raise SystemExit(f"slack not ok: {data.get('error')}")
        if i == 0 and not started_in_thread:
            # Overflow of this send may continue in a thread. Short sends stay roots.
            if len(parts) > 1:
                ts = data.get("ts")
        receipts.append(str(data.get("ts")))
    return receipts


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in {"format", "send"}:
        sys.stderr.write("usage: slack_mirror.py format|send FILE [--channel ID] [--thread_ts TS]\n")
        return 2
    path = Path(argv[2])
    parts = format_mirror(path)
    if argv[1] == "format":
        for i, p in enumerate(parts):
            sys.stdout.write(f"--- part {i + 1}/{len(parts)} ({len(p)} chars) ---\n{p}\n")
        return 0
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        sys.stdout.write("DARK: no SLACK_BOT_TOKEN. Lane idle. Use Slack MCP this window.\n")
        return 0
    channel = os.environ.get("COMMONS_SLACK_CHANNEL", DEFAULT_TABLE).strip()
    thread_ts = os.environ.get("COMMONS_SLACK_THREAD_TS", "").strip()
    rest = argv[3:]
    i = 0
    while i < len(rest):
        if rest[i] in {"--channel", "--thread_ts"} and i + 1 < len(rest):
            if rest[i] == "--channel":
                channel = rest[i + 1].strip()
            else:
                thread_ts = rest[i + 1].strip()
            i += 2
            continue
        sys.stderr.write("unknown arg %s\n" % rest[i])
        return 2
    receipts = send_parts(parts, token, channel=channel, thread_ts=thread_ts)
    sys.stdout.write("sent ts=" + ",".join(receipts) + " channel=" + channel + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
