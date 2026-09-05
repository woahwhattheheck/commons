"""Private Slack request/return carrier attached to the existing tool gateway.

Any equipped workspace harness can use the same catalog. No public MCP route
is added, and Slack credentials remain in the existing local service adapter.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from .services import redacted

OPEN = "<commons_equipment_request>"
CLOSE = "</commons_equipment_request>"


def slack_timestamp(value) -> str:
    """Slack accepts microsecond precision; extra digits silently miss replies.

    Preserve received timestamps exactly and truncate any higher precision
    startup clock value instead of floating-point rounding a stored cursor up.
    """
    whole, _, fraction = str(value).partition(".")
    return whole + "." + fraction[:6].ljust(6, "0")


def parse_request(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("&lt;commons_equipment_request&gt;"):
        # Slack's Claude connector escapes its text fallback while rendering
        # literal brackets in rich_text. Decode exactly one transport layer;
        # ampersand last preserves an original literal '&lt;' in an argument.
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    if not text.startswith(OPEN):
        return None
    body, found, _footer = text[len(OPEN):].partition(CLOSE)
    if not found:
        raise ValueError("equipment request envelope is incomplete")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("equipment request must be an object")
    for key in ("request_id", "call_id", "name"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(key + " must be a nonempty string")
    if not isinstance(value.get("arguments", {}), dict):
        raise ValueError("arguments must be an object")
    return value


class SlackEquipmentCarrier:
    def __init__(self, catalog, calls, route: dict, cursor_path: Path):
        self.catalog = catalog
        self.calls = calls
        self.channel = route["channel_id"]
        self.thread_ts = route.get("thread_ts")
        self.interval = max(5, float(route.get("poll_seconds", 15)))
        self.path = cursor_path
        self.cursor = slack_timestamp(time.time())
        if self.path.is_file():
            self.cursor = json.loads(self.path.read_text(encoding="utf-8")).get("cursor", self.cursor)
        self.cursor = slack_timestamp(self.cursor)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self.run, daemon=True, name="shared-equipment-slack-carrier")
        self.status = {"ok": True, "phase": "configured", "channel_id": self.channel,
            "thread_ts": self.thread_ts, "cursor": self.cursor}
        if not self.path.is_file():
            self._save(self.cursor)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=35)

    def _save(self, cursor):
        cursor = slack_timestamp(cursor)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"cursor": cursor, "channel_id": self.channel, "thread_ts": self.thread_ts}), encoding="utf-8")
        temp.replace(self.path)
        self.cursor = cursor

    def process(self, message):
        try:
            request = parse_request(message.get("text", ""))
        except (ValueError, TypeError) as exc:
            # Malformed transport input must not strand later valid requests.
            self.catalog.services.call("slack_post_message", {"channel_id": self.channel,
                "thread_ts": message.get("thread_ts") or message["ts"],
                "text": "Equipment request parse error: " + str(exc)})
            return
        if request is None:
            return
        rid, cid = request["request_id"], request["call_id"]
        if request["name"] == "equipment_catalog":
            runner = lambda _name, _args: {"tools": self.catalog.tools()}
        else:
            runner = self.catalog.call
        result = self.calls.execute_journaled("equipment:" + rid, cid,
            request["name"], request.get("arguments", {}), runner)
        response = json.dumps(redacted({"request_id": rid, "call_id": cid, "result": result}), ensure_ascii=False)
        # Slack text has a finite message size. Multiple parts preserve the full
        # JSON; consumers join content between the per-part wrappers in order.
        parts = [response[i:i + 28000] for i in range(0, len(response), 28000)]
        digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
        for index, part in enumerate(parts, start=1):
            text = (f"<commons_equipment_result request_id={json.dumps(rid)} call_id={json.dumps(cid)} "
                f"part=\"{index}/{len(parts)}\" sha256=\"{digest}\">\n{part}\n</commons_equipment_result>")
            delivery = self.calls.execute_journaled("equipment-return:" + rid,
                cid + ":" + message["ts"] + ":" + str(index), "slack_post_message",
                {"channel_id": self.channel, "thread_ts": message.get("thread_ts") or message["ts"], "text": text},
                self.catalog.services.call)
            if delivery.get("isError") or delivery.get("result", {}).get("ok") is False:
                raise RuntimeError("equipment result delivery failed; inspect journal before retry")

    def once(self):
        args = {"channel": self.channel, "oldest": slack_timestamp(self.cursor), "limit": 100}
        method = "conversations.history"
        if self.thread_ts:
            method = "conversations.replies"
            args["ts"] = self.thread_ts
        messages = []
        while True:
            page = self.catalog.services.slack(method, args)
            if not page.get("ok"):
                raise RuntimeError("Slack carrier read failed: " + str(page.get("error", "unknown")))
            messages.extend(m for m in page.get("messages", []) if float(m["ts"]) > float(self.cursor))
            cursor = page.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            args["cursor"] = cursor
        for message in sorted(messages, key=lambda m: float(m["ts"])):
            self.process(message)
            self._save(message["ts"])

    def run(self):
        while not self._stop.is_set():
            try:
                self.once()
                self.status = {"ok": True, "phase": "polling", "channel_id": self.channel,
                    "thread_ts": self.thread_ts, "cursor": self.cursor, "time": time.time()}
            except Exception as exc:
                self.status = {"ok": False, "phase": "error", "error": type(exc).__name__,
                    "message": redacted(str(exc)), "cursor": self.cursor, "time": time.time()}
            # One redacted diagnostic snapshot; no source message/secret log.
            diagnostic = self.path.with_name("equipment_slack_status.json")
            diagnostic.write_text(json.dumps(self.status), encoding="utf-8")
            self._stop.wait(self.interval)
