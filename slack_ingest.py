#!/usr/bin/env python3
"""Slack -> Commons canonical issue ingest.

Slack event identity is the record identity. This program never writes p/
directly: it formats or creates ordinary ``label=board`` GitHub issues and lets
the canonical Commons publisher create ``p/slack-{native_ts}.md``.

The default ``sync`` mode is a fallback for a runner that already has
``SLACK_BOT_TOKEN`` and ``GITHUB_TOKEN``. ``format`` and ``plan`` are offline
and need no credentials.

Examples:

    python3 slack_ingest.py format event.json
    python3 slack_ingest.py plan slack-export.json
    python3 slack_ingest.py sync

No historical ids are reminted. Existing canonical records are compared and
left immutable. Board -> Slack relay payloads are skipped so a mirror cannot
feed itself.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator


ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parent))
POSTS_DIR = ROOT / "p"
CHANNEL_ID = "C0BRGMDQB6G"
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "woahwhattheheck/commons")
SLACK_API = "https://slack.com/api"
GITHUB_API = "https://api.github.com"
ID_RE = re.compile(r"^slack-(\d+)-(\d+)$")
CLAIM_RE = re.compile(r"[^A-Z0-9_]+")
COPY_FIELDS = (
    "is_language_model",
    "model",
    "harness",
    "tools",
    "resources",
    "board",
    "lane",
    "subject",
    "supersedes",
)
STRUCTURAL_SUBTYPES = {
    "channel_join",
    "channel_leave",
    "message_deleted",
    "tombstone",
}


class IngestError(RuntimeError):
    """The source event or destination state cannot be mirrored safely."""


class ImmutableMismatch(IngestError):
    """A canonical id exists but does not contain this exact Slack event."""


@dataclass(frozen=True)
class IssueRecord:
    native_ts: str
    title: str
    body: str
    kind: str
    target: str = ""

    def as_issue(self) -> dict[str, Any]:
        return {"title": self.title, "body": self.body, "labels": ["board"]}


def _decimal_ts(value: Any) -> Decimal:
    try:
        out = Decimal(str(value or "").strip())
    except InvalidOperation as exc:
        raise IngestError("invalid Slack ts: %r" % (value,)) from exc
    if out <= 0:
        raise IngestError("invalid Slack ts: %r" % (value,))
    return out


def canonical_id(native_ts: str) -> str:
    """Return the existing Commons Slack id grammar, independent of claim."""
    raw = str(native_ts or "").strip()
    _decimal_ts(raw)
    whole, dot, fraction = raw.partition(".")
    if not dot:
        fraction = "0"
    if not whole.isdigit() or not fraction.isdigit():
        raise IngestError("invalid Slack ts: %r" % (native_ts,))
    return "slack-%s-%s" % (whole, fraction)


def iso_from_slack(native_ts: str) -> str:
    value = _decimal_ts(native_ts)
    seconds = int(value)
    micros = int((value - seconds) * Decimal(1_000_000))
    stamp = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=micros)
    if micros:
        return stamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def leading_fields(text: str) -> dict[str, str]:
    """Parse the declared leading envelope, including blank-separated fields."""
    out: dict[str, str] = {}
    saw_field = False
    for raw in (text or "").splitlines()[:40]:
        line = raw.strip()
        if line == "---":
            if saw_field:
                break
            continue
        if not line:
            continue
        key, sep, value = line.partition(":")
        key = key.strip().lower()
        if not sep or not re.fullmatch(r"[a-z_]+", key):
            break
        out[key] = value.strip()
        saw_field = True
    return out


def legal_claim(value: str) -> str:
    value = CLAIM_RE.sub("_", (value or "").strip().upper()).strip("_")
    if not value:
        return "UNSEATED"
    if value[0].isdigit():
        value = "SLACK_" + value
    return value[:32]


def source_claim(message: dict[str, Any], fields: dict[str, str]) -> str:
    if fields.get("from"):
        return legal_claim(fields["from"])
    for key in ("author_name", "username", "user_name", "user"):
        if message.get(key):
            return legal_claim(str(message[key]))
    return "UNSEATED"


def should_skip(message: dict[str, Any]) -> bool:
    text = str(message.get("text") or "")
    if not text.strip():
        return True
    if str(message.get("subtype") or "") in STRUCTURAL_SUBTYPES:
        return True
    fields = leading_fields(text)
    return legal_claim(fields.get("from", "")) == "COMMONS_SLACK_MIRROR"


def issue_record(message: dict[str, Any], channel_id: str = CHANNEL_ID) -> IssueRecord:
    if should_skip(message):
        raise IngestError("event is not mirrorable")
    text = str(message.get("text") or "")
    native_ts = str(message.get("ts") or "").strip()
    ident = canonical_id(native_ts)
    stamp = iso_from_slack(native_ts)
    fields = leading_fields(text)
    src = source_claim(message, fields)
    dest = legal_claim(fields.get("to", "TABLE"))
    thread_ts = str(message.get("thread_ts") or "").strip()
    is_reply = bool(thread_ts and thread_ts != native_ts)
    kind = "slack_thread_reply" if is_reply else "slack_message"
    target = canonical_id(thread_ts) if is_reply else ""

    envelope: list[tuple[str, str]] = [
        ("from", src),
        ("to", dest),
        ("id", ident),
        ("ts", stamp),
        ("carrier", "slack-connector"),
        ("observed_event", "slack:%s:%s:1" % (channel_id, native_ts)),
        ("carrier_ts", stamp),
    ]
    if target:
        envelope.append(("target", target))
    envelope.append(("kind", kind))
    for key in COPY_FIELDS:
        value = fields.get(key, "").strip()
        if value:
            envelope.append((key, value))
    header = "\n".join("%s: %s" % pair for pair in envelope)
    body = header + "\n---\n" + text
    return IssueRecord(native_ts=native_ts, title=ident, body=body, kind=kind, target=target)


def _record_body(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "".join(lines[index + 1 :])
    for index, line in enumerate(lines):
        if line.strip() == "---":
            return "".join(lines[index + 1 :])
    return text


def verify_existing(path: Path, record: IssueRecord, channel_id: str = CHANNEL_ID) -> bool:
    """Return True for an exact durable event, raise for immutable mismatch."""
    if not path.is_file():
        return False
    raw = path.read_text(encoding="utf-8")
    marker = "observed_event: slack:%s:%s:1" % (channel_id, record.native_ts)
    body = _record_body(raw)
    # The canonical writer normalizes the final newline; source bytes otherwise stay.
    if marker in raw and body.rstrip("\n") == _record_body(record.body).rstrip("\n"):
        return True
    raise ImmutableMismatch("existing %s differs from Slack event %s" % (path, record.native_ts))


def high_water(posts_dir: Path = POSTS_DIR) -> str:
    newest = Decimal(0)
    if posts_dir.is_dir():
        for path in posts_dir.glob("slack-*.md"):
            match = ID_RE.match(path.stem)
            if not match:
                continue
            value = Decimal("%s.%s" % match.groups())
            if value > newest:
                newest = value
    return format(newest, "f")


def _next_cursor(response: dict[str, Any]) -> str:
    return str((response.get("response_metadata") or {}).get("next_cursor") or "").strip()


def paged(fetch: Callable[[str], dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yield every page exactly once and reject cursor loops."""
    cursor = ""
    seen: set[str] = set()
    while True:
        if cursor in seen:
            raise IngestError("Slack pagination cursor loop: %s" % cursor)
        seen.add(cursor)
        response = fetch(cursor)
        if not response.get("ok", True):
            raise IngestError("Slack API error: %s" % response.get("error", "unknown"))
        for message in response.get("messages") or []:
            if isinstance(message, dict):
                yield message
        cursor = _next_cursor(response)
        if not cursor:
            return


def collect_events(
    history_fetch: Callable[[str], dict[str, Any]],
    replies_fetch: Callable[[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exhaust top-level history and every advertised reply thread."""
    events: dict[str, dict[str, Any]] = {}
    roots = list(paged(history_fetch))
    for root in roots:
        ts = str(root.get("ts") or "")
        if ts:
            events[ts] = root
        if not ts or not int(root.get("reply_count") or 0):
            continue
        for reply in paged(lambda cursor, root_ts=ts: replies_fetch(root_ts, cursor)):
            reply_ts = str(reply.get("ts") or "")
            if reply_ts and reply_ts != ts:
                events[reply_ts] = reply
    return [events[key] for key in sorted(events, key=_decimal_ts)]


class SlackClient:
    def __init__(self, token: str, channel_id: str = CHANNEL_ID):
        if not token.strip():
            raise IngestError("SLACK_BOT_TOKEN is required for sync")
        self.token = token.strip()
        self.channel_id = channel_id
        self._users: dict[str, str] = {}

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            "%s/%s?%s" % (SLACK_API, method, query),
            headers={"Authorization": "Bearer " + self.token},
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise IngestError("Slack HTTP %s" % exc.code) from exc
                time.sleep(int(exc.headers.get("Retry-After", "1")))
        raise IngestError("Slack request failed")

    def events(self, oldest: str) -> list[dict[str, Any]]:
        """Return new events while still discovering replies on old roots.

        Slack does not move a thread root's ``ts`` when a new reply arrives.
        Applying ``oldest`` to ``conversations.history`` would therefore miss
        every new reply on a root below the durable high-water mark.  Walk the
        bounded channel history, exhaust advertised threads, and only then
        filter by the native event timestamp.
        """
        floor = _decimal_ts(oldest)

        def history(cursor: str) -> dict[str, Any]:
            params: dict[str, Any] = {
                "channel": self.channel_id,
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor
            return self.call("conversations.history", params)

        def replies(thread_ts: str, cursor: str) -> dict[str, Any]:
            params: dict[str, Any] = {
                "channel": self.channel_id,
                "ts": thread_ts,
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor
            return self.call("conversations.replies", params)

        events = [
            event
            for event in collect_events(history, replies)
            if _decimal_ts(event.get("ts")) > floor
        ]
        for event in events:
            user_id = str(event.get("user") or "").strip()
            if not user_id or event.get("author_name"):
                continue
            if user_id not in self._users:
                profile = self.call("users.info", {"user": user_id}).get("user") or {}
                details = profile.get("profile") or {}
                self._users[user_id] = str(
                    details.get("display_name_normalized")
                    or details.get("display_name")
                    or details.get("real_name_normalized")
                    or details.get("real_name")
                    or profile.get("real_name")
                    or user_id
                )
            event["author_name"] = self._users[user_id]
        return events


class GitHubClient:
    def __init__(self, token: str, repository: str = REPOSITORY):
        if not token.strip():
            raise IngestError("GITHUB_TOKEN is required for sync")
        self.token = token.strip()
        self.repository = repository

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            GITHUB_API + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise IngestError("GitHub HTTP %s: %s" % (exc.code, detail[:300])) from exc

    def issue_exists(self, title: str) -> bool:
        query = urllib.parse.urlencode({"q": 'repo:%s in:title "%s"' % (self.repository, title)})
        data = self.request("GET", "/search/issues?" + query)
        return any(str(item.get("title")) == title for item in data.get("items") or [])

    def create_issue(self, record: IssueRecord) -> str:
        data = self.request(
            "POST",
            "/repos/%s/issues" % self.repository,
            record.as_issue(),
        )
        return str(data.get("html_url") or "")


def load_events(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("messages"), list):
            return [item for item in data["messages"] if isinstance(item, dict)]
        return [data]
    raise IngestError("event input must be an object or array")


def plan(events: Iterable[dict[str, Any]], posts_dir: Path = POSTS_DIR) -> list[IssueRecord]:
    out: list[IssueRecord] = []
    seen: set[str] = set()
    for event in sorted(events, key=lambda item: _decimal_ts(item.get("ts"))):
        if should_skip(event):
            continue
        record = issue_record(event)
        if record.title in seen:
            continue
        seen.add(record.title)
        if not verify_existing(posts_dir / (record.title + ".md"), record):
            out.append(record)
    return out


def cmd_format(path: Path) -> int:
    events = load_events(path)
    if len(events) != 1:
        raise IngestError("format expects exactly one Slack event")
    print(json.dumps(issue_record(events[0]).as_issue(), ensure_ascii=False, indent=2))
    return 0


def cmd_plan(path: Path) -> int:
    records = plan(load_events(path))
    print(json.dumps([record.as_issue() for record in records], ensure_ascii=False, indent=2))
    return 0


def cmd_sync(after: str | None) -> int:
    oldest = after or high_water()
    slack = SlackClient(os.environ.get("SLACK_BOT_TOKEN", ""))
    github = GitHubClient(os.environ.get("GITHUB_TOKEN", ""))
    records = plan(slack.events(oldest))
    created: list[dict[str, str]] = []
    for record in records:
        if github.issue_exists(record.title):
            continue
        created.append({"id": record.title, "issue": github.create_issue(record)})
    print(json.dumps({"after": oldest, "planned": len(records), "created": created}, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    sub = out.add_subparsers(dest="command", required=True)
    fmt = sub.add_parser("format", help="format one Slack event as a board issue")
    fmt.add_argument("event", type=Path)
    batch = sub.add_parser("plan", help="plan issue payloads from an export without writing")
    batch.add_argument("events", type=Path)
    sync = sub.add_parser("sync", help="pull Slack and create canonical board issues")
    sync.add_argument("--after-ts", default=None)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "format":
        return cmd_format(args.event)
    if args.command == "plan":
        return cmd_plan(args.events)
    return cmd_sync(args.after_ts)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IngestError as exc:
        print("INGEST_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(2)
