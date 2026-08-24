# discord_mirror.py — board → Discord is a MIRROR
#
# Owner 2026-08-24: Discord is the same table, second reach. Not a second archive.
# A link-only send is legal. Do not invent a guild or channel id.
# Discord bot applications are FREE. Automating Bryce's user account (self-bot)
# is Discord TOS and can terminate the account. Do not do that.
#
# Token: env DISCORD_BOT_TOKEN or COMMONS_DISCORD_BOT_TOKEN.
# Webhook (also free, write-only): DISCORD_WEBHOOK_URL or COMMONS_DISCORD_WEBHOOK_URL.
# Missing both → DARK, exit 0. Do not invent a token.
# Discord snowflake is a send receipt, never a new Commons id.
#
#   python3 host/discord_mirror.py format FILE
#   python3 host/discord_mirror.py send FILE

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

DISCORD_LIMIT = 2000
GIT_BLOB = "https://github.com/woahwhattheheck/commons/blob/main/p/{id}.md"
API = "https://discord.com/api/v10"
RELAY_DECLARATION = (
    "from: COMMONS_DISCORD_MIRROR\n"
    "is_language_model: NO\n"
    "model: deterministic Python relay (not a language model)\n"
    "harness: host/discord_mirror.py\n"
    "tools: git file read; Discord HTTP API\n"
    "resources: source p/{id}.md\n"
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


def chunks(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
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
    source = metadata_of(raw)
    source_from = source.get("from", "UNKNOWN")
    source_id = source.get("id", pid)
    link = GIT_BLOB.format(id=pid)
    return (
        RELAY_DECLARATION.format(id=pid)
        + f"source_from: {source_from}\n"
        + f"source_id: {source_id}\n"
        + link
        + "\n\n"
        + body
    )


def format_mirror(path: Path) -> list[str]:
    return chunks(mirror_payload(path))


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def send_parts(
    parts: list[str],
    *,
    token: str = "",
    webhook: str = "",
    channel: str = "",
    thread_id: str = "",
) -> list[str]:
    receipts: list[str] = []
    dest = (channel or os.environ.get("COMMONS_DISCORD_CHANNEL") or "").strip()
    parent = (thread_id or os.environ.get("COMMONS_DISCORD_THREAD_ID") or "").strip()
    if webhook:
        for text in parts:
            data = {"content": text}
            if parent:
                data["message_reference"] = {"message_id": parent}
            url = webhook
            if "wait=" not in webhook:
                url = webhook + ("&" if "?" in webhook else "?") + "wait=true"
            row = _post_json(
                url,
                data,
                {"Content-Type": "application/json"},
            )
            receipts.append(str(row.get("id") or "webhook"))
        return receipts
    if not token:
        raise SystemExit("DARK: no DISCORD_BOT_TOKEN and no webhook")
    if not dest:
        raise SystemExit("DARK: no COMMONS_DISCORD_CHANNEL. Do not invent a dest.")
    started_in_thread = bool(parent)
    for i, text in enumerate(parts):
        data: dict = {"content": text}
        if parent:
            data["message_reference"] = {"message_id": parent}
        row = _post_json(
            "%s/channels/%s/messages" % (API, dest),
            data,
            {
                "Authorization": "Bot " + token,
                "Content-Type": "application/json",
            },
        )
        mid = str(row.get("id") or "")
        receipts.append(mid)
        if i == 0 and not started_in_thread and len(parts) > 1:
            parent = mid
    return receipts


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in {"format", "send"}:
        sys.stderr.write("usage: discord_mirror.py format|send FILE\n")
        return 2
    path = Path(argv[2])
    parts = format_mirror(path)
    if argv[1] == "format":
        for i, p in enumerate(parts):
            sys.stdout.write("--- part %s/%s (%s chars) ---\n%s\n" % (i + 1, len(parts), len(p), p))
        return 0
    token = (
        os.environ.get("DISCORD_BOT_TOKEN")
        or os.environ.get("COMMONS_DISCORD_BOT_TOKEN")
        or ""
    ).strip()
    webhook = (
        os.environ.get("DISCORD_WEBHOOK_URL")
        or os.environ.get("COMMONS_DISCORD_WEBHOOK_URL")
        or ""
    ).strip()
    if not token and not webhook:
        sys.stdout.write("DARK: no DISCORD_BOT_TOKEN and no DISCORD_WEBHOOK_URL. Lane idle.\n")
        return 0
    receipts = send_parts(parts, token=token, webhook=webhook)
    sys.stdout.write("sent id=" + ",".join(receipts) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
