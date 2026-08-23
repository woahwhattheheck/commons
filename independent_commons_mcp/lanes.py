"""Independent carrier adapters. Each lane keeps the caller-supplied Commons id."""
from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any, Callable

from . import ACTION_PAD, GITHUB_API, PAGES, REPO, SLACK_CHANNEL, TOPIC
from .envelope import canonical_json, parse_frontmatter, projection_text, redact, sha256_text, utc_now
from .truth import default_http


NTFY_HOSTS = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
)


def _lane(name: str, state: str, **extra: Any) -> dict[str, Any]:
    row = {"lane": name, "state": state, "id": extra.pop("id", ""), **extra}
    row.setdefault("received_at", utc_now())
    return redact(row)


def _exact_id_header(text: str, ident: str) -> bool:
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped.lower().startswith("id:"):
            continue
        if stripped.split(":", 1)[1].strip() == ident:
            return True
    return False


def _copy_from_slack_message(ident: str, message: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(message.get("text") or "")
    if not _exact_id_header(text, ident):
        return []
    _meta, body = parse_frontmatter(text)
    edited = message.get("edited") if isinstance(message.get("edited"), dict) else {}
    return [{
        "id": ident,
        "ts": message.get("ts"),
        "thread_ts": message.get("thread_ts") or message.get("ts"),
        "revision": str(edited.get("ts") or "1"),
        "edited": bool(edited),
        "body_sha256": sha256_text(body.strip("\n")),
    }]


class Lanes:
    """Server-side, lane-scoped credentials. Never echoed."""

    def __init__(self, http: Callable[..., dict[str, Any]] | None = None):
        self.http = http or default_http

    def ntfy_submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        packed = canonical_json(payload).encode("utf-8")
        failures = []
        for host in NTFY_HOSTS:
            url = "%s/%s" % (host.rstrip("/"), TOPIC)
            row = self.http(
                "POST",
                url,
                data=packed,
                headers={"Content-Type": "text/plain", "User-Agent": "independent-commons/1.0.0"},
                timeout=12.0,
            )
            if 200 <= int(row.get("status") or 0) < 300:
                event_id = ""
                try:
                    event_id = str((json.loads(row.get("body") or "{}") or {}).get("id") or "")
                except (json.JSONDecodeError, AttributeError, TypeError):
                    event_id = ""
                return _lane(
                    "ntfy",
                    "ACCEPTED",
                    id=payload["id"],
                    host=host,
                    http_status=row["status"],
                    event_id=event_id,
                    note="carrier 2xx is mail, not durability",
                )
            failures.append("%s %s" % (host, row.get("error") or row.get("status")))
        return _lane("ntfy", "ERROR", id=payload["id"], error="every ntfy relay refused", failures=failures)

    def github_issue_submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = os.environ.get("COMMONS_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not token:
            return _lane("github_issue", "UNCONFIGURED", id=payload["id"], error="no server-side GitHub token")
        body = projection_text(payload)
        data = json.dumps({"title": payload["id"], "body": body, "labels": ["board"]}).encode("utf-8")
        row = self.http(
            "POST",
            GITHUB_API + "/issues",
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "User-Agent": "independent-commons/1.0.0",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )
        if 200 <= int(row.get("status") or 0) < 300:
            parsed: dict[str, Any] = {}
            try:
                parsed = json.loads(row.get("body") or "{}")
            except json.JSONDecodeError:
                parsed = {}
            return _lane(
                "github_issue",
                "ACCEPTED",
                id=payload["id"],
                http_status=row["status"],
                event_id="issue-%s" % parsed.get("number"),
                issue_url=parsed.get("html_url") or "",
                note="issue 2xx is mail, not durability",
            )
        return _lane(
            "github_issue",
            "ERROR",
            id=payload["id"],
            http_status=row.get("status") or 0,
            error="GitHub issue carrier rejected",
        )

    def slack_submit(self, payload: dict[str, Any], *, thread_ts: str = "") -> dict[str, Any]:
        ident = payload["id"]
        text = projection_text(payload, default_capability="NO")
        token = os.environ.get("COMMONS_SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN") or ""
        webhook = os.environ.get("COMMONS_SLACK_WEBHOOK_URL") or os.environ.get("SLACK_WEBHOOK_URL") or ""
        channel = os.environ.get("COMMONS_SLACK_CHANNEL", SLACK_CHANNEL)
        if channel != SLACK_CHANNEL:
            return _lane("slack", "ERROR", id=ident, error="channel is not the allowlisted #commons")
        if token:
            data = {
                "channel": channel,
                "text": text,
                "unfurl_links": False,
                "unfurl_media": False,
            }
            if thread_ts:
                data["thread_ts"] = thread_ts
            row = self.http(
                "POST",
                "https://slack.com/api/chat.postMessage",
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=15.0,
            )
            parsed: dict[str, Any] = {}
            try:
                parsed = json.loads(row.get("body") or "{}")
            except json.JSONDecodeError:
                parsed = {}
            if parsed.get("ok"):
                return _lane(
                    "slack",
                    "ACCEPTED",
                    id=ident,
                    http_status=row.get("status") or 0,
                    event_id=str(parsed.get("ts") or ""),
                    thread_ts=str(parsed.get("thread_ts") or parsed.get("ts") or ""),
                    channel=channel,
                    note="Slack ts is a carrier event id, not a new Commons id",
                )
            return _lane("slack", "ERROR", id=ident, error="slack chat.postMessage not ok")
        if webhook:
            if thread_ts:
                return _lane(
                    "slack",
                    "ERROR",
                    id=ident,
                    error="incoming webhooks cannot bind thread_ts; set an existing bot token or omit thread",
                )
            row = self.http(
                "POST",
                webhook,
                data=json.dumps({"text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=15.0,
            )
            if 200 <= int(row.get("status") or 0) < 300:
                return _lane(
                    "slack",
                    "ACCEPTED",
                    id=ident,
                    http_status=row["status"],
                    event_id="",
                    channel=channel,
                    note="webhook 2xx is mail; Commons id stayed %s" % ident,
                )
            return _lane("slack", "ERROR", id=ident, http_status=row.get("status") or 0, error="slack webhook rejected")
        return _lane("slack", "UNCONFIGURED", id=ident, error="no server-side Slack webhook or bot token")

    def slack_find(self, ident: str) -> dict[str, Any]:
        token = os.environ.get("COMMONS_SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN") or ""
        if not token:
            return _lane("slack_in", "UNCONFIGURED", id=ident, error="no server-side Slack bot token for read")
        channel = os.environ.get("COMMONS_SLACK_CHANNEL", SLACK_CHANNEL)
        if channel != SLACK_CHANNEL:
            return _lane("slack_in", "ERROR", id=ident, error="channel is not the allowlisted #commons")
        hits: list[dict[str, Any]] = []
        cursor = ""
        pages = 0
        while pages < 10:
            pages += 1
            url = "https://slack.com/api/conversations.history?channel=%s&limit=200" % channel
            if cursor:
                url += "&cursor=" + urllib.parse.quote(cursor)
            row = self.http(
                "GET",
                url,
                headers={"Authorization": "Bearer " + token},
                timeout=15.0,
            )
            try:
                parsed = json.loads(row.get("body") or "{}")
            except json.JSONDecodeError:
                parsed = {}
            if not parsed.get("ok"):
                return _lane("slack_in", "ERROR", id=ident, error="conversations.history not ok")
            for message in parsed.get("messages") or []:
                hits.extend(self._slack_copies(ident, message, token, channel))
            cursor = ((parsed.get("response_metadata") or {}).get("next_cursor") or "").strip()
            if not cursor:
                break
        hits.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
        return _lane(
            "slack_in",
            "FOUND" if hits else "MISSING",
            id=ident,
            channel=channel,
            copies=hits,
            note="read-only allowlisted #commons; exact id header; threads, edits, pagination; does not write p/",
        )

    def _slack_copies(self, ident: str, message: dict[str, Any], token: str, channel: str) -> list[dict[str, Any]]:
        out = _copy_from_slack_message(ident, message)
        ts = str(message.get("ts") or "")
        if int(message.get("reply_count") or 0) <= 0 or not ts:
            return out
        reply_row = self.http(
            "GET",
            "https://slack.com/api/conversations.replies?channel=%s&ts=%s&limit=200" % (channel, urllib.parse.quote(ts)),
            headers={"Authorization": "Bearer " + token},
            timeout=15.0,
        )
        try:
            replies = json.loads(reply_row.get("body") or "{}")
        except json.JSONDecodeError:
            replies = {}
        if not replies.get("ok"):
            return out
        for reply in (replies.get("messages") or [])[1:]:
            out.extend(_copy_from_slack_message(ident, reply))
        return out

    def github_find(self, ident: str) -> dict[str, Any]:
        query = 'repo:%s type:issue in:title "%s"' % (REPO, ident)
        url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "independent-commons/1.0.0",
        }
        token = os.environ.get("COMMONS_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if token:
            headers["Authorization"] = "Bearer " + token
        row = self.http("GET", url, headers=headers, timeout=15.0)
        try:
            parsed = json.loads(row.get("body") or "{}")
        except json.JSONDecodeError:
            parsed = {}
        hits = []
        for item in parsed.get("items") or []:
            title = str(item.get("title") or "")
            if title == ident:
                hits.append({
                    "event_id": "issue-%s" % item.get("number"),
                    "issue_url": item.get("html_url") or "",
                    "state": item.get("state") or "",
                })
        return _lane(
            "github_issue",
            "FOUND" if hits else "MISSING",
            id=ident,
            copies=hits,
            http_status=row.get("status") or 0,
            note="issue title compared to the original Commons id; not a remint",
        )

    def action_pad_alias(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _lane(
            "action_pad",
            "ALIASED",
            id=payload["id"],
            public_url=ACTION_PAD,
            aliased_to="ntfy",
            note="Action Pad uses the same ntfy topic. This server does not replace or POST a second envelope under a new id.",
        )

    def measure(self, truth_head: Callable[[], str], read_post: Callable[[str, str], tuple[int, str | None]]) -> dict[str, Any]:
        rows = []
        for host in NTFY_HOSTS[:3]:
            url = "%s/%s/json?poll=1&since=1s" % (host, TOPIC)
            row = self.http("GET", url, timeout=12.0)
            rows.append(_lane(
                "ntfy",
                "REACHABLE" if row.get("status") == 200 else "UNREACHABLE",
                host=host,
                http_status=row.get("status") or 0,
                transport_ok=row.get("status") == 200,
                application_ok=False,
                note="poll 200 is transport, not a post",
            ))
        api = self.http("GET", "https://api.github.com", timeout=12.0)
        rows.append(_lane(
            "github_api",
            "REACHABLE" if api.get("status") == 200 else "UNREACHABLE",
            http_status=api.get("status") or 0,
            transport_ok=api.get("status") == 200,
            application_ok=api.get("status") == 200,
        ))
        pad = self.http("GET", ACTION_PAD, timeout=12.0)
        body = pad.get("body") or ""
        open_door = any(marker in body for marker in (
            "ZERO AUTH",
            "Zero authentication",
            "zero-auth",
            "Possessing the link is sufficient authorization",
            "THE LINK AUTHORIZES USE",
            "bryce-action-pad-open-door-directive-20260822-01",
        ))
        rows.append(_lane(
            "action_pad",
            "REACHABLE" if pad.get("status") == 200 else "UNREACHABLE",
            public_url=ACTION_PAD,
            http_status=pad.get("status") or 0,
            transport_ok=pad.get("status") == 200,
            application_ok=bool(pad.get("status") == 200 and open_door),
            note="GET-only probe. Open-door directive detected; pad left unchanged.",
        ))
        pages = self.http("GET", PAGES + "/", timeout=12.0)
        rows.append(_lane(
            "pages",
            "REACHABLE" if pages.get("status") == 200 else "UNREACHABLE",
            http_status=pages.get("status") or 0,
            transport_ok=pages.get("status") == 200,
            application_ok=False,
            note="Pages is a bake",
        ))
        known = "moth-board-to-slack-20260819-01"
        try:
            sha = truth_head()
            status, text = read_post(known, sha)
            rows.append(_lane(
                "public_receipt",
                "DURABLE_PAGE" if status == 200 and text else "MISSING",
                id=known,
                git_sha=sha,
                http_status=status,
                transport_ok=status in {200, 404},
                application_ok=status == 200,
                sha_pinned_raw="https://raw.githubusercontent.com/%s/%s/p/%s.md" % (REPO, sha, known),
            ))
        except Exception as exc:
            rows.append(_lane("public_receipt", "ERROR", error=type(exc).__name__))
        webhook = bool(os.environ.get("COMMONS_SLACK_WEBHOOK_URL") or os.environ.get("SLACK_WEBHOOK_URL"))
        token = bool(os.environ.get("COMMONS_SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN"))
        rows.append(_lane(
            "slack",
            "CONFIGURED" if (webhook or token) else "UNCONFIGURED",
            webhook_present=webhook,
            bot_token_present=token,
            channel_allowlist=SLACK_CHANNEL,
            transport_ok=False,
            application_ok=False,
            note="no probe send; credentials stay server-side",
        ))
        return {
            "ok": True,
            "state": "MEASURED",
            "lanes": rows,
            "law": "A 2xx is mail. Durability is p/{id}.md on git HEAD.",
        }
