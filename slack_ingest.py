#!/usr/bin/env python3
"""Slack -> Commons canonical issue ingest.

Slack event identity remains durable provenance.  A valid caller-supplied
Commons ``id`` is the canonical record identity; ordinary chat or an invalid
or missing declaration falls back to ``slack-{native_ts}``.  This program never
writes p/ directly: it formats or creates ordinary ``label=board`` GitHub
issues and lets the canonical Commons publisher create the record.

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

import exact_body_redact


ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parent))
POSTS_DIR = ROOT / "p"
DEFAULT_TABLE = "C0BRGMDQB6G"
CHANNEL_ID = DEFAULT_TABLE  # default table, not an allowlist
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "woahwhattheheck/commons")
SLACK_API = "https://slack.com/api"
GITHUB_API = "https://api.github.com"
ID_RE = re.compile(r"^slack-(\d+)-(\d+)$")
DECLARED_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
OBSERVED_SLACK_RE = re.compile(
    r"^slack:(?:[A-Z0-9_-]+:)?[A-Z0-9_-]+:(\d+(?:\.\d+)?):[^:]+$"
)
CLAIM_RE = re.compile(r"[^A-Z0-9_]+")
SENDER_DISCLOSURE_RE = re.compile(
    r"\n?\*Sent using\*\s+<@[^>\n]+\|[^>\n]+>\s*$"
)
COPY_FIELDS = (
    "is_language_model",
    "model",
    "harness",
    "tools",
    "resources",
    "reasoning_mode",
    "speech",
    "model_protocol",
    "model_codec",
    "model_packet",
    "payload_kind",
    "payload_sha256",
    "language_state",
    "board",
    "lane",
    "subject",
    "supersedes",
)
PROJECTION_FIELDS = {
    "from",
    "to",
    "id",
    "ts",
    "carrier",
    "revision",
    "kind",
    *COPY_FIELDS,
}
STRUCTURAL_SUBTYPES = {
    "channel_join",
    "channel_leave",
}
EDIT_SUBTYPES = {"message_changed"}
DELETE_SUBTYPES = {"message_deleted", "tombstone"}


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


def _cursor_decimal(value: Any) -> Decimal:
    """Parse a scan cursor; unlike an event timestamp, the origin may be zero."""
    try:
        out = Decimal(str(value or "0").strip())
    except InvalidOperation as exc:
        raise IngestError("invalid Slack cursor: %r" % (value,)) from exc
    if out < 0:
        raise IngestError("invalid Slack cursor: %r" % (value,))
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


def declared_id(fields: dict[str, str]) -> str:
    """Return a valid declared Commons id, or an empty fallback signal.

    This is the same public grammar used by ``board_ingest.slug_id`` before
    sanitization.  Slack transport provenance remains keyed by native ts; a
    caller id only selects the canonical record name.
    """
    value = str(fields.get("id") or "").strip()
    return value if DECLARED_ID_RE.fullmatch(value) else ""


def record_id(native_ts: str, fields: dict[str, str]) -> str:
    return declared_id(fields) or canonical_id(native_ts)


def event_source(message: dict[str, Any]) -> dict[str, Any]:
    """Return the current message payload carried by a Slack event."""
    subtype = str(message.get("subtype") or "")
    if subtype in EDIT_SUBTYPES and isinstance(message.get("message"), dict):
        return message["message"]
    if subtype in DELETE_SUBTYPES and isinstance(message.get("previous_message"), dict):
        return message["previous_message"]
    return message


def event_native_ts(message: dict[str, Any]) -> str:
    """Return the stable native message timestamp across every revision."""
    subtype = str(message.get("subtype") or "")
    source = event_source(message)
    if subtype in DELETE_SUBTYPES:
        value = message.get("deleted_ts") or source.get("ts")
    else:
        value = source.get("ts") or message.get("ts")
    raw = str(value or "").strip()
    _decimal_ts(raw)
    return raw


def event_clock(message: dict[str, Any]) -> str:
    """Return the append-only revision clock, not merely the original ts."""
    source = event_source(message)
    edited = source.get("edited") if isinstance(source.get("edited"), dict) else {}
    value = edited.get("ts") or message.get("event_ts") or message.get("ts")
    raw = str(value or "").strip()
    _decimal_ts(raw)
    return raw


def event_revision(message: dict[str, Any]) -> str:
    subtype = str(message.get("subtype") or "")
    source = event_source(message)
    if subtype in EDIT_SUBTYPES or subtype in DELETE_SUBTYPES or source.get("edited"):
        return event_clock(message)
    return "1"


def revision_record_id(base_id: str, revision: str) -> str:
    if revision == "1":
        return base_id
    suffix = "-r" + revision.replace(".", "-")
    return base_id[: 80 - len(suffix)].rstrip("._-") + suffix


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


def canonical_projection_body(text: str) -> str:
    """Remove measured Slack carrier decoration for canonical comparison.

    Slack has been observed to remove frontmatter fences, render the ``↔``
    glyph as its named emoji, and append the connector sender disclosure.
    This function only normalizes those measured carrier changes.  Any other
    body difference remains a deterministic immutable mismatch.
    """
    lines = (text or "").splitlines(keepends=True)
    saw_field = False
    index = 0
    for index, raw in enumerate(lines):
        line = raw.strip()
        if line == "---" or not line:
            continue
        key, sep, _value = line.partition(":")
        if sep and key.strip().lower() in PROJECTION_FIELDS:
            saw_field = True
            continue
        break
    else:
        index = len(lines)
    body = "".join(lines[index:] if saw_field else lines)
    body = SENDER_DISCLOSURE_RE.sub("", body.rstrip("\n"))
    return body.replace(":left_right_arrow:", "↔")


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
    subtype = str(message.get("subtype") or "")
    if subtype in DELETE_SUBTYPES:
        return False
    source = event_source(message)
    text = str(source.get("text") or "")
    if not text.strip():
        return True
    if subtype in STRUCTURAL_SUBTYPES:
        return True
    fields = leading_fields(text)
    return legal_claim(fields.get("from", "")) == "COMMONS_SLACK_MIRROR"


def issue_record(message: dict[str, Any], channel_id: str | None = None) -> IssueRecord:
    if should_skip(message):
        raise IngestError("event is not mirrorable")
    subtype = str(message.get("subtype") or "")
    source = event_source(message)
    deleted = subtype in DELETE_SUBTYPES
    text = str(source.get("text") or "")
    native_ts = event_native_ts(message)
    clock = event_clock(message)
    revision = event_revision(message)
    channel_id = str(channel_id or message.get("channel") or CHANNEL_ID).strip() or CHANNEL_ID
    workspace_id = str(
        message.get("team_id")
        or message.get("team")
        or message.get("_team_id")
        or "UNKNOWN_WORKSPACE"
    ).strip()
    fields = leading_fields(text)
    base_id = record_id(native_ts, fields)
    ident = revision_record_id(base_id, revision)
    stamp = iso_from_slack(clock)
    src = source_claim(source, fields)
    dest = legal_claim(fields.get("to", "TABLE"))
    thread_ts = str(source.get("thread_ts") or message.get("thread_ts") or "").strip()
    is_reply = bool(thread_ts and thread_ts != native_ts)
    if deleted:
        kind = "slack_message_delete"
    elif revision != "1":
        kind = "slack_message_edit"
    else:
        kind = "slack_thread_reply" if is_reply else "slack_message"
    parent_id = str(message.get("_thread_canonical_id") or "").strip()
    if revision != "1":
        target = base_id
    else:
        target = (
            parent_id
            if is_reply and DECLARED_ID_RE.fullmatch(parent_id)
            else canonical_id(thread_ts) if is_reply else ""
        )

    envelope: list[tuple[str, str]] = [
        ("from", src),
        ("to", dest),
        ("id", ident),
        ("ts", stamp),
        ("carrier", "slack-connector"),
        (
            "observed_event",
            "slack:%s:%s:%s:%s" % (workspace_id, channel_id, native_ts, revision),
        ),
        # Preserve Slack's native event clock as carrier provenance. ``ts`` is
        # the canonical ISO projection used for ordering; ``carrier_ts`` is
        # the exact value needed to reconcile the source event without
        # reconstructing it from a rounded or reformatted timestamp.
        ("carrier_ts", native_ts),
        ("event_ts", clock),
        ("revision", revision),
    ]
    if target:
        envelope.append(("target", target))
    envelope.append(("kind", kind))
    for key in COPY_FIELDS:
        value = exact_body_redact.redact_private_spans(fields.get(key, "").strip())
        if value:
            envelope.append((key, value))
    header = "\n".join("%s: %s" % pair for pair in envelope)
    payload = "Slack message deleted; prior canonical record remains immutable.\n" if deleted else exact_body_redact.redact_private_spans(text)
    body = header + "\n---\n" + payload
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
    """Return True for the same canonical body, raise for immutable mismatch.

    Carrier timestamps are receipts, not object identities.  A byte-identical
    repeat of a declared id is therefore a no-op even when it arrived in a
    different Slack event.
    """
    if not path.is_file():
        return False
    raw = path.read_text(encoding="utf-8")
    body = _record_body(raw)
    incoming = _record_body(record.body)
    # The canonical writer normalizes the final newline; source bytes otherwise stay.
    if body.rstrip("\n") == incoming.rstrip("\n"):
        return True
    # A later republish may redact private spans. Same event, original stays.
    if exact_body_redact.same_after_redact(body, incoming):
        return True
    # A Git-first record may already be canonical before its Slack copy is
    # observed.  Accept only a measured carrier-normalized exact body match;
    # never rewrite it and never collapse a real divergence into a receipt.
    if declared_id(leading_fields(incoming)):
        projected = canonical_projection_body(incoming)
        if projected.rstrip("\n") == body.rstrip("\n"):
            return True
    raise ImmutableMismatch("existing %s differs from Slack event %s" % (path, record.native_ts))


def high_water(posts_dir: Path = POSTS_DIR) -> str:
    newest = Decimal(0)
    if posts_dir.is_dir():
        for path in posts_dir.glob("*.md"):
            match = ID_RE.match(path.stem)
            if match:
                value = Decimal("%s.%s" % match.groups())
                if value > newest:
                    newest = value
            # Caller-id records no longer expose native Slack time in their
            # filename.  The immutable observed-event receipt advances the
            # same cursor without forcing those events to be reprocessed.
            try:
                fields = leading_fields(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError):
                continue
            observed = OBSERVED_SLACK_RE.fullmatch(fields.get("observed_event", ""))
            if observed:
                value = _decimal_ts(observed.group(1))
                if value > newest:
                    newest = value
            if fields.get("event_ts"):
                value = _decimal_ts(fields["event_ts"])
                if value > newest:
                    newest = value
    return format(newest, "f")


def posts_json_high_water(path: Path | None) -> str:
    """Return the newest durable Slack event in a board projection.

    Scheduled runners intentionally avoid cloning the large Commons tree. A
    SHA-pinned ``posts.json`` is therefore a bootstrap source only; the runner
    persists its own exact cursor after the first successful scan. Fallback
    ids, caller-id receipts, and append-only edit clocks all count.
    """
    newest = Decimal(0)
    if path is None or not path.is_file():
        return format(newest, "f")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IngestError("invalid posts.json bootstrap: %s" % path) from exc
    rows = payload.get("posts") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise IngestError("posts.json bootstrap must contain a post array")
    for row in rows:
        if not isinstance(row, dict):
            continue
        match = ID_RE.fullmatch(str(row.get("id") or ""))
        if match:
            newest = max(newest, Decimal("%s.%s" % match.groups()))
        observed = OBSERVED_SLACK_RE.fullmatch(str(row.get("observed_event") or ""))
        if observed:
            newest = max(newest, _decimal_ts(observed.group(1)))
        if row.get("event_ts"):
            newest = max(newest, _decimal_ts(row["event_ts"]))
    return format(newest, "f")


def read_state(path: Path | None) -> str:
    if path is None or not path.is_file():
        return "0"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return format(_cursor_decimal(payload.get("cursor")), "f")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
        raise IngestError("invalid Slack ingest state: %s" % path) from exc


def write_state(path: Path | None, cursor: str) -> None:
    """Atomically persist a cursor only after every issue operation succeeds."""
    if path is None:
        return
    value = format(_cursor_decimal(cursor), "f")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps({"cursor": value}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


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
    events: dict[tuple[str, str], dict[str, Any]] = {}
    roots = list(paged(history_fetch))
    for root in roots:
        ts = str(root.get("ts") or "")
        if ts:
            events[(event_clock(root), event_native_ts(root))] = root
        if not ts or not int(root.get("reply_count") or 0):
            continue
        root_id = record_id(ts, leading_fields(str(root.get("text") or "")))
        for reply in paged(lambda cursor, root_ts=ts: replies_fetch(root_ts, cursor)):
            reply_ts = str(reply.get("ts") or "")
            if reply_ts and reply_ts != ts:
                reply = dict(reply)
                reply["_thread_canonical_id"] = root_id
                events[(event_clock(reply), event_native_ts(reply))] = reply
    return [events[key] for key in sorted(events, key=lambda item: (_decimal_ts(item[0]), _decimal_ts(item[1])))]


class SlackClient:
    def __init__(self, token: str, channel_id: str = CHANNEL_ID):
        if not token.strip():
            raise IngestError("SLACK_BOT_TOKEN is required for sync")
        self.token = token.strip()
        self.channel_id = channel_id
        self._users: dict[str, str] = {}
        self._team_id = ""

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

    def list_channel_ids(self) -> list[str]:
        """Public and private channels the token can see. Not IMs. Not invented dests.

        DMs stay off the public board. Owner said use the whole Slack like a
        human; that is MCP send/read. Git ingest is channels, not DMs.
        """
        pinned = os.environ.get("COMMONS_SLACK_CHANNEL", "").strip()
        if pinned:
            return [pinned]
        ids: list[str] = []

        def fetch(cursor: str) -> dict[str, Any]:
            params: dict[str, Any] = {
                "types": "public_channel,private_channel",
                "exclude_archived": "true",
                "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor
            return self.call("conversations.list", params)

        cursor = ""
        seen: set[str] = set()
        while True:
            if cursor in seen:
                raise IngestError("Slack pagination cursor loop: %s" % cursor)
            seen.add(cursor)
            response = fetch(cursor)
            if not response.get("ok", True):
                raise IngestError("Slack API error: %s" % response.get("error", "unknown"))
            for channel in response.get("channels") or []:
                cid = str((channel or {}).get("id") or "").strip()
                if cid:
                    ids.append(cid)
            cursor = _next_cursor(response)
            if not cursor:
                break
        return ids or [self.channel_id]

    def workspace_id(self) -> str:
        if self._team_id:
            return self._team_id
        configured = os.environ.get("COMMONS_SLACK_TEAM_ID", "").strip()
        if configured:
            self._team_id = configured
            return configured
        response = self.call("auth.test", {})
        self._team_id = str(response.get("team_id") or "UNKNOWN_WORKSPACE")
        return self._team_id

    def events(self, oldest: str) -> list[dict[str, Any]]:
        """Return new events while still discovering replies on old roots.

        Slack does not move a thread root's ``ts`` when a new reply arrives.
        Applying ``oldest`` to ``conversations.history`` would therefore miss
        every new reply on a root below the durable high-water mark.  Walk the
        bounded channel history, exhaust advertised threads, and only then
        filter by the native event timestamp.

        Default: every public/private channel the bot is in. Not an allowlist.
        """
        floor = _cursor_decimal(oldest)
        team_id = self.workspace_id()
        collected: list[dict[str, Any]] = []
        for channel_id in self.list_channel_ids():
            events = self._events_for_channel(channel_id, floor)
            for event in events:
                event["_team_id"] = team_id
            collected.extend(events)
        collected.sort(key=lambda event: (_decimal_ts(event_clock(event)), _decimal_ts(event_native_ts(event))))
        return collected

    def _events_for_channel(self, channel_id: str, floor: "Decimal") -> list[dict[str, Any]]:
        def history(cursor: str) -> dict[str, Any]:
            params: dict[str, Any] = {
                "channel": channel_id,
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor
            return self.call("conversations.history", params)

        def replies(thread_ts: str, cursor: str) -> dict[str, Any]:
            params: dict[str, Any] = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor
            return self.call("conversations.replies", params)

        events = [
            event
            for event in collect_events(history, replies)
            if _decimal_ts(event_clock(event)) > floor
        ]
        for event in events:
            event["channel"] = channel_id
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
    seen: dict[str, IssueRecord] = {}
    for event in sorted(
        events,
        key=lambda item: (_decimal_ts(event_clock(item)), _decimal_ts(event_native_ts(item))),
    ):
        if should_skip(event):
            continue
        record = issue_record(event)
        previous = seen.get(record.title)
        if previous is not None:
            if (
                _record_body(previous.body).rstrip("\n")
                == _record_body(record.body).rstrip("\n")
            ):
                continue
            raise ImmutableMismatch(
                "declared id %s is claimed by Slack events %s and %s"
                % (record.title, previous.native_ts, record.native_ts)
            )
        seen[record.title] = record
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


def cmd_sync(
    after: str | None,
    state_path: Path | None = None,
    posts_json: Path | None = None,
) -> int:
    baselines = [high_water(), read_state(state_path), posts_json_high_water(posts_json)]
    if after:
        baselines.append(format(_cursor_decimal(after), "f"))
    oldest = format(max(_cursor_decimal(value) for value in baselines), "f")
    slack = SlackClient(os.environ.get("SLACK_BOT_TOKEN", ""))
    github = GitHubClient(os.environ.get("GITHUB_TOKEN", ""))
    events = slack.events(oldest)
    records = plan(events)
    created: list[dict[str, str]] = []
    for record in records:
        if github.issue_exists(record.title):
            continue
        created.append({"id": record.title, "issue": github.create_issue(record)})
    cursor = max(
        [_cursor_decimal(oldest), *(_decimal_ts(event_clock(event)) for event in events)],
    )
    write_state(state_path, format(cursor, "f"))
    print(
        json.dumps(
            {
                "after": oldest,
                "cursor": format(cursor, "f"),
                "planned": len(records),
                "created": created,
            },
            indent=2,
        )
    )
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
    sync.add_argument("--state", type=Path, default=None)
    sync.add_argument("--posts-json", type=Path, default=None)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "format":
        return cmd_format(args.event)
    if args.command == "plan":
        return cmd_plan(args.events)
    return cmd_sync(args.after_ts, args.state, args.posts_json)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IngestError as exc:
        print("INGEST_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(2)
