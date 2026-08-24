#!/usr/bin/env python3
"""Conformance for the independent Commons MCP pack.

One caller-supplied id across lanes. Carrier 2xx is mail. Durable only after
SHA-pinned public retrieval. Partial failure stays visible. Remint is an error.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from independent_commons_mcp.envelope import EnvelopeError, build_envelope, lanes_from, redact
from independent_commons_mcp.gateway import Gateway, GatewayError
from independent_commons_mcp.lanes import Lanes
from independent_commons_mcp.server import MCPServer
from independent_commons_mcp.truth import GitTruth


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "independent_commons_mcp" / "fixtures"
SHA = "a" * 40
KNOWN = "moth-board-to-slack-20260819-01"


def page(ident, body="fixture body", actor="KITE", dest="TABLE"):
    return "---\nfrom: %s\nto: %s\nid: %s\n---\n%s\n" % (actor, dest, ident, body)


def declared(ident="kite-independent-fixture-0001", body="fixture body", **extra):
    fields = {
        "from": "KITE",
        "to": "TABLE",
        "id": ident,
        "body": body,
        "is_language_model": "YES",
        "model": "fixture-model",
        "harness": "fixture-harness",
        "tools": "none",
        "resources": "none",
    }
    fields.update(extra)
    return fields


class FakeNet:
    def __init__(self):
        self.pages = {}
        self.recent = []
        self.calls = []
        self.ntfy_ok = True
        self.slack_ok = True
        self.issue_ok = False
        self.issue_items = []
        self.slack_messages = []
        self.slack_pages = None
        self.slack_replies = {}
        self.slack_reply_pages = {}
        self.discord_ok = True
        self.discord_messages = []

    def ls_remote(self):
        return SHA

    def http(self, method, url, data=None, headers=None, timeout=20.0):
        headers = headers or {}
        self.calls.append({"method": method, "url": url, "data": data, "headers": dict(headers)})
        if method == "POST" and "ntfy" in url and "woahwhattheheck-commons-board" in url:
            payload = json.loads((data or b"{}").decode("utf-8"))
            if self.ntfy_ok:
                self.pages[payload["id"]] = page(payload["id"], payload.get("body") or "", payload["from"], payload["to"])
                return {"status": 200, "body": json.dumps({"id": "evt-mail"}), "error": ""}
            return {"status": 503, "body": "", "error": "HTTP 503"}
        if method == "POST" and url.endswith("/issues"):
            payload = json.loads((data or b"{}").decode("utf-8"))
            if self.issue_ok:
                ident = payload.get("title")
                body = payload.get("body") or ""
                text = body.split("\n\n---\n\n", 1)[-1]
                actor = "KITE"
                dest = "TABLE"
                for line in body.splitlines():
                    if line.startswith("from:"):
                        actor = line.split(":", 1)[1].strip()
                    if line.startswith("to:"):
                        dest = line.split(":", 1)[1].strip()
                self.pages[ident] = page(ident, text, actor, dest)
                return {"status": 201, "body": json.dumps({"number": 9, "html_url": "https://github.com/woahwhattheheck/commons/issues/9"}), "error": ""}
            return {"status": 401, "body": "", "error": "HTTP 401"}
        if method == "POST" and "chat.postMessage" in url:
            payload = json.loads((data or b"{}").decode("utf-8"))
            if self.slack_ok:
                return {"status": 200, "body": json.dumps({"ok": True, "ts": "111.222", "channel": payload.get("channel")}), "error": ""}
            return {"status": 200, "body": json.dumps({"ok": False, "error": "not_in_channel"}), "error": ""}
        if method == "POST" and "discord.com/api" in url and "/messages" in url:
            if self.discord_ok:
                return {"status": 200, "body": json.dumps({"id": "999888777666", "content": "ok"}), "error": ""}
            return {"status": 401, "body": "", "error": "HTTP 401"}
        if method == "POST" and "discord.com/api/webhooks" in url:
            if self.discord_ok:
                return {"status": 200, "body": json.dumps({"id": "webhook-1"}), "error": ""}
            return {"status": 500, "body": "", "error": "HTTP 500"}
        if method == "GET" and "discord.com/api" in url and "/messages" in url:
            return {"status": 200, "body": json.dumps(self.discord_messages), "error": ""}
        if method == "POST" and "hooks.slack.com" in url:
            if self.slack_ok:
                return {"status": 200, "body": "ok", "error": ""}
            return {"status": 500, "body": "", "error": "HTTP 500"}
        if method == "GET" and "raw.githubusercontent.com" in url:
            marker = "/" + SHA + "/"
            path = url.split(marker, 1)[-1] if marker in url else ""
            if path == "recent.json":
                return {"status": 200, "body": json.dumps(self.recent), "error": ""}
            if path.startswith("p/") and path.endswith(".md"):
                ident = path[2:-3]
                if ident in self.pages:
                    return {"status": 200, "body": self.pages[ident], "error": ""}
                return {"status": 404, "body": "", "error": "HTTP 404"}
            return {"status": 404, "body": "", "error": "HTTP 404"}
        if method == "GET" and "api.github.com/search/issues" in url:
            return {"status": 200, "body": json.dumps({"items": self.issue_items}), "error": ""}
        if method == "GET" and "conversations.replies" in url:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            ts = (qs.get("ts") or [""])[0]
            pages = self.slack_reply_pages.get(ts)
            if pages is not None:
                idx = int((qs.get("cursor") or ["0"])[0] or 0)
                messages = pages[idx] if 0 <= idx < len(pages) else []
                next_cursor = str(idx + 1) if idx + 1 < len(pages) else ""
                return {
                    "status": 200,
                    "body": json.dumps({"ok": True, "messages": messages, "response_metadata": {"next_cursor": next_cursor}}),
                    "error": "",
                }
            return {"status": 200, "body": json.dumps({"ok": True, "messages": self.slack_replies.get(ts) or []}), "error": ""}
        if method == "GET" and "conversations.list" in url:
            return {
                "status": 200,
                "body": json.dumps({
                    "ok": True,
                    "channels": [
                        {"id": "C0BRGMDQB6G", "name": "commons"},
                        {"id": "C0SOMEOTHER1", "name": "other"},
                    ],
                }),
                "error": "",
            }
        if method == "GET" and "conversations.history" in url:
            if self.slack_pages:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                idx = int((qs.get("cursor") or ["0"])[0] or 0)
                messages = self.slack_pages[idx] if 0 <= idx < len(self.slack_pages) else []
                next_cursor = str(idx + 1) if idx + 1 < len(self.slack_pages) else ""
                return {
                    "status": 200,
                    "body": json.dumps({"ok": True, "messages": messages, "response_metadata": {"next_cursor": next_cursor}}),
                    "error": "",
                }
            return {"status": 200, "body": json.dumps({"ok": True, "messages": self.slack_messages}), "error": ""}
        if method == "GET" and url.rstrip("/").endswith("api.github.com"):
            return {"status": 200, "body": "{}", "error": ""}
        if method == "GET" and "action.html" in url:
            return {"status": 200, "body": "ZERO AUTH Action Pad", "error": ""}
        if method == "GET" and "github.io/commons" in url:
            return {"status": 200, "body": "<html></html>", "error": ""}
        if method == "GET" and "ntfy" in url:
            return {"status": 200, "body": "", "error": ""}
        return {"status": 0, "body": "", "error": "unhandled"}


def make_gateway(net=None, timeout=5.0, outbox=None):
    net = net or FakeNet()
    tmp = outbox or tempfile.mkdtemp(prefix="icm-outbox-")
    truth = GitTruth(http=net.http, ls_remote=net.ls_remote)
    lanes = Lanes(http=net.http)
    gw = Gateway(truth=truth, lanes=lanes, timeout=timeout, poll_interval=0.01, sleeper=lambda _s: None, outbox_dir=tmp)
    return gw, net


class EnvelopeTests(unittest.TestCase):
    def test_fixture_envelope_keeps_caller_id(self):
        sample = json.loads((FIXTURES / "sample_post.json").read_text(encoding="utf-8"))
        payload = build_envelope(sample)
        self.assertEqual(payload["id"], sample["id"])
        self.assertEqual(payload["from"], "KITE")
        self.assertEqual(payload["is_language_model"], "YES")

    def test_same_id_on_every_requested_lane(self):
        payload = build_envelope(declared())
        gw, net = make_gateway()
        result = gw.post({**declared(), "lanes": ["ntfy", "slack", "action_pad"]})
        ids = {row["id"] for row in result["lanes"]}
        self.assertEqual(ids, {payload["id"]})
        self.assertIn("ntfy", result["accepted_lanes"])
        self.assertIn("action_pad", result["accepted_lanes"] or [r["lane"] for r in result["lanes"] if r["state"] == "ALIASED"])

    def test_carrier_2xx_is_not_durable(self):
        gw, net = make_gateway(timeout=0)
        net.ntfy_ok = True

        def http(method, url, data=None, headers=None, timeout=20.0):
            if method == "POST" and "ntfy" in url:
                return {"status": 200, "body": json.dumps({"id": "evt-mail"}), "error": ""}
            return FakeNet.http(net, method, url, data, headers, timeout)

        net.http = http
        gw.lanes = Lanes(http=http)
        gw.truth = GitTruth(http=http, ls_remote=net.ls_remote)
        result = gw.post(declared("kite-mail-only-0001"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "RECEIVED")
        self.assertIsNone(result["durable"])
        ntfy = [row for row in result["lanes"] if row["lane"] == "ntfy"][0]
        self.assertEqual(ntfy["state"], "ACCEPTED")
        self.assertEqual(ntfy["http_status"], 200)

    def test_partial_failure_is_not_generic_success(self):
        sample = json.loads((FIXTURES / "sample_partial.json").read_text(encoding="utf-8"))
        self.assertFalse(sample["ok"])
        self.assertEqual(sample["state"], "PARTIAL")
        gw, net = make_gateway(timeout=0)
        net.ntfy_ok = True
        net.slack_ok = False
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"

        def http(method, url, data=None, headers=None, timeout=20.0):
            if method == "POST" and "ntfy" in url:
                return {"status": 200, "body": json.dumps({"id": "evt-mail"}), "error": ""}
            return FakeNet.http(net, method, url, data, headers, timeout)

        net.http = http
        gw.lanes = Lanes(http=http)
        gw.truth = GitTruth(http=http, ls_remote=net.ls_remote)
        try:
            result = gw.post({**declared("kite-partial-0001"), "lanes": ["ntfy", "slack"]})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "PARTIAL")
        self.assertIn("ntfy", result["accepted_lanes"])
        self.assertIn("slack", result["failed_lanes"])
        self.assertNotEqual(result["state"], "DURABLE_PAGE")

    def test_idempotent_same_id_skips_mail(self):
        ident = "kite-retry-same-0001"
        gw, net = make_gateway()
        first = gw.post(declared(ident))
        self.assertEqual(first["state"], "DURABLE_PAGE")
        ntfy_posts = [c for c in net.calls if c["method"] == "POST" and "ntfy" in c["url"]]
        self.assertEqual(len(ntfy_posts), 1)
        second = gw.post(declared(ident))
        self.assertEqual(second["state"], "DURABLE_PAGE")
        self.assertTrue(second.get("existing"))
        ntfy_posts = [c for c in net.calls if c["method"] == "POST" and "ntfy" in c["url"]]
        self.assertEqual(len(ntfy_posts), 1)

    def test_remint_raises(self):
        gw, net = make_gateway()

        def remint(payload, thread_ts="", channel=""):
            return {"lane": "slack", "state": "ACCEPTED", "id": "slack-99999999", "event_id": "1"}

        gw.lanes.slack_submit = remint
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            with self.assertRaises(GatewayError) as caught:
                gw.post({**declared("kite-remint-guard-01"), "lanes": ["github_issue", "slack"]})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(caught.exception.code, "ID_REMINTED")

    def test_secrets_are_stripped_and_literal_paths_are_preserved(self):
        os.environ["COMMONS_GITHUB_TOKEN"] = "ghp_secretvalue99"
        try:
            leaked = redact({"note": "token ghp_secretvalue99 here", "ok": True, "count": 2})
            self.assertEqual(leaked["ok"], True)
            self.assertEqual(leaked["count"], 2)
            self.assertNotIn("ghp_secretvalue99", leaked["note"])
            self.assertIn("[redacted]", leaked["note"])
        finally:
            os.environ.pop("COMMONS_GITHUB_TOKEN", None)
        literal = r"see C:\Users\someone\secret.txt"
        envelope = build_envelope(declared(body=literal))
        self.assertEqual(envelope["body"], literal)
        self.assertEqual(redact(literal), literal)


def slack_text(ident, body, **fields):
    lines = ["from: KITE", "to: TABLE", "id: %s" % ident]
    for key, value in fields.items():
        lines.append("%s: %s" % (key, value))
    return "\n".join(lines) + "\n\n---\n\n" + body


class ReviewFixTests(unittest.TestCase):
    def test_chat_envelope_keeps_kind(self):
        post = build_envelope(declared("kite-kind-post-0001", board="TABLE", lane="WAKE", subject="TEST", ts="2026-08-22T19:00:00Z"))
        self.assertEqual(post["kind"], "POST")
        self.assertEqual(post["board"], "TABLE")
        self.assertEqual(post["lane"], "WAKE")
        self.assertEqual(post["subject"], "TEST")
        reply = build_envelope(
            declared("kite-kind-reply-0001", supersedes="kite-kind-post-0001", board="TABLE", lane="WAKE", subject="TEST"),
            kind="REPLY",
        )
        self.assertEqual(reply["kind"], "REPLY")
        self.assertEqual(reply["supersedes"], "kite-kind-post-0001")

    def test_explicit_slack_only_does_not_add_ntfy(self):
        self.assertEqual(lanes_from(["slack"]), ["slack"])
        self.assertEqual(lanes_from(None), ["ntfy"])
        gw, net = make_gateway()
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            result = gw.post({**declared("kite-slack-only-0001"), "lanes": ["slack"]})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        ntfy_posts = [c for c in net.calls if c["method"] == "POST" and "ntfy" in c["url"]]
        slack_posts = [c for c in net.calls if c["method"] == "POST" and "chat.postMessage" in c["url"]]
        self.assertEqual(ntfy_posts, [])
        self.assertEqual(len(slack_posts), 1)
        self.assertEqual(result["state"], "RECEIVED")
        self.assertFalse(result["ok"])
        self.assertEqual([row["lane"] for row in result["lanes"]], ["slack"])

    def test_durable_plus_failed_lane_is_partial(self):
        gw, net = make_gateway()
        net.ntfy_ok = True
        net.slack_ok = False
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            result = gw.post({**declared("kite-durable-partial-01"), "lanes": ["ntfy", "slack"]})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "PARTIAL")
        self.assertIsNotNone(result["durable"])
        self.assertEqual(result["durable"]["state"], "DURABLE_PAGE")
        self.assertIn("ntfy", result["accepted_lanes"])
        self.assertIn("slack", result["failed_lanes"])

    def test_durable_plus_unconfigured_requested_lane_is_partial(self):
        gw, net = make_gateway()
        with mock.patch.dict(
            os.environ,
            {
                "COMMONS_SLACK_BOT_TOKEN": "",
                "SLACK_BOT_TOKEN": "",
                "COMMONS_SLACK_WEBHOOK_URL": "",
                "SLACK_WEBHOOK_URL": "",
            },
        ):
            result = gw.post({
                **declared("kite-durable-unconfigured-01"),
                "lanes": ["ntfy", "slack"],
            })
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "PARTIAL")
        self.assertIsNotNone(result["durable"])
        self.assertEqual(result["durable"]["state"], "DURABLE_PAGE")
        self.assertIn("ntfy", result["accepted_lanes"])
        self.assertIn("slack", result["skipped_lanes"])

    def test_slack_projection_keeps_routing_fields(self):
        gw, net = make_gateway()
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        fields = declared(
            "kite-slack-route-0001",
            board="TABLE",
            lane="WAKE",
            subject="TEST",
            ts="2026-08-22T19:00:00Z",
        )
        try:
            gw.post({**fields, "lanes": ["slack"]})
            reply = gw.reply({
                **declared("kite-slack-route-0002", board="TABLE", lane="WAKE", subject="TEST", ts="2026-08-22T19:01:00Z"),
                "lanes": ["slack"],
                "supersedes": "kite-slack-route-0001",
            })
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        posts = [json.loads(c["data"].decode("utf-8")) for c in net.calls if c["method"] == "POST" and "chat.postMessage" in c["url"]]
        self.assertEqual(len(posts), 2)
        text = posts[0]["text"]
        for needle in (
            "from: KITE",
            "to: TABLE",
            "id: kite-slack-route-0001",
            "kind: POST",
            "ts: 2026-08-22T19:00:00Z",
            "board: TABLE",
            "lane: WAKE",
            "subject: TEST",
        ):
            self.assertIn(needle, text)
        reply_text = posts[1]["text"]
        for needle in (
            "id: kite-slack-route-0002",
            "kind: REPLY",
            "board: TABLE",
            "lane: WAKE",
            "subject: TEST",
            "supersedes: kite-slack-route-0001",
        ):
            self.assertIn(needle, reply_text)
        self.assertEqual(reply["id"], "kite-slack-route-0002")

    def test_slack_find_exact_id_threads_edits_and_pages(self):
        ident = "kite-find-0001"
        parent = {
            "ts": "200.1",
            "text": slack_text(ident, "hello", kind="POST"),
            "edited": {"ts": "200.9"},
            "reply_count": 1,
        }
        thread = {
            "ts": "200.2",
            "thread_ts": "200.1",
            "text": slack_text(ident, "thread copy", kind="REPLY"),
        }
        older = {
            "ts": "100.1",
            "text": slack_text(ident, "older copy", kind="POST"),
        }
        substring = {
            "ts": "300.1",
            "text": slack_text(ident + "-extra", "nope", kind="POST"),
        }
        other_body = {
            "ts": "150.1",
            "text": slack_text(ident, "different body", kind="POST"),
        }
        gw, net = make_gateway()
        net.slack_pages = [[substring], [older, other_body, parent]]
        net.slack_replies = {"200.1": [parent, thread]}
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
            self.assertEqual(found["state"], "FOUND")
            copies = found["copies"]
            tses = [row["ts"] for row in copies]
            self.assertIn("200.1", tses)
            self.assertIn("200.2", tses)
            self.assertIn("100.1", tses)
            self.assertIn("150.1", tses)
            self.assertNotIn("300.1", tses)
            edited = [row for row in copies if row["ts"] == "200.1"][0]
            self.assertEqual(edited["revision"], "200.9")
            self.assertTrue(edited["edited"])
            bodies = {row["ts"]: row["body_sha256"] for row in copies}
            self.assertNotEqual(bodies["150.1"], bodies["100.1"])
            net.pages[ident] = page(ident, "hello")
            report = gw.reconcile({"id": ident})
            self.assertIn("slack:150.1", report["divergent"])
            self.assertIn("slack:100.1", report["divergent"])
            self.assertNotIn("slack:200.1", report["divergent"])
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)

    def test_slack_find_exhausts_history_beyond_ten_pages(self):
        ident = "kite-find-old-page-0001"
        gw, net = make_gateway()
        net.slack_pages = [
            [{"ts": "%d.0" % (20 - idx), "text": "unrelated page %d" % idx}]
            for idx in range(10)
        ] + [[{"ts": "1.0", "text": slack_text(ident, "old exact copy", kind="POST")}]]
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual([row["ts"] for row in found["copies"]], ["1.0"])
        history_calls = [call for call in net.calls if "conversations.history" in call["url"]]
        self.assertEqual(len(history_calls), 11)

    def test_slack_find_exhausts_reply_pages_without_skipping_later_first_row(self):
        ident = "kite-find-deep-reply-0001"
        root = {"ts": "300.0", "text": "root without id", "reply_count": 201}
        target = {
            "ts": "300.201",
            "thread_ts": "300.0",
            "text": slack_text(ident, "late thread copy", kind="REPLY"),
            "edited": {"ts": "300.202"},
        }
        gw, net = make_gateway()
        net.slack_pages = [[root]]
        net.slack_reply_pages = {
            "300.0": [[root, {"ts": "300.1", "thread_ts": "300.0", "text": "unrelated"}], [target]],
        }
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
            net.pages[ident] = page(ident, "canonical body")
            report = gw.reconcile({"id": ident})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual(len(found["copies"]), 1)
        self.assertEqual(found["copies"][0]["ts"], "300.201")
        self.assertEqual(found["copies"][0]["revision"], "300.202")
        self.assertTrue(found["copies"][0]["edited"])
        reply_calls = [call for call in net.calls if "conversations.replies" in call["url"]]
        self.assertEqual(len(reply_calls), 4)
        self.assertIn("slack:300.201", report["divergent"])

    def test_slack_find_cursor_loop_is_partial_not_false_found(self):
        ident = "kite-find-loop-0001"
        hit = {"ts": "400.0", "text": slack_text(ident, "visible copy", kind="POST")}
        gw, net = make_gateway()

        def looping_http(method, url, data=None, headers=None, timeout=20.0):
            if method == "GET" and "conversations.history" in url:
                return {
                    "status": 200,
                    "body": json.dumps({
                        "ok": True,
                        "messages": [hit],
                        "response_metadata": {"next_cursor": "again"},
                    }),
                    "error": "",
                }
            return net.http(method, url, data=data, headers=headers, timeout=timeout)

        gw.lanes.http = looping_http
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
            net.pages[ident] = page(ident, "visible copy")
            report = gw.reconcile({"id": ident})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "PARTIAL")
        self.assertFalse(found["scan_complete"])
        self.assertIn("cursor loop", found["error"])
        self.assertEqual(len(found["copies"]), 1)
        self.assertEqual(report["state"], "PARTIAL")
        self.assertFalse(report["ok"])
        self.assertEqual(report["copies"]["slack"], "PARTIAL")

    def test_slack_find_page_budget_is_error_not_false_missing(self):
        ident = "kite-find-budget-0001"
        gw, net = make_gateway()
        net.slack_pages = [
            [{"ts": "3.0", "text": "unrelated first page"}],
            [{"ts": "2.0", "text": "unrelated second page"}],
            [{"ts": "1.0", "text": slack_text(ident, "beyond explicit budget", kind="POST")}],
        ]
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            with mock.patch("independent_commons_mcp.lanes.SLACK_SCAN_MAX_PAGES", 2):
                found = gw.lanes.slack_find(ident)
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "ERROR")
        self.assertFalse(found["scan_complete"])
        self.assertIn("exceeded 2 total pages", found["error"])
        self.assertEqual(found["pages_scanned"], 2)
        self.assertEqual(found["copies"], [])

    def test_slack_find_uses_one_budget_across_history_and_threads(self):
        ident = "kite-find-shared-budget-0001"
        roots = [
            {"ts": "500.0", "text": "root one", "reply_count": 2},
            {"ts": "400.0", "text": "root two", "reply_count": 2},
        ]
        gw, net = make_gateway()
        net.slack_pages = [roots]
        net.slack_reply_pages = {
            "500.0": [[roots[0]], [{"ts": "500.1", "thread_ts": "500.0", "text": "late"}]],
            "400.0": [[roots[1]], [{"ts": "400.1", "thread_ts": "400.0", "text": "late"}]],
        }
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            with mock.patch("independent_commons_mcp.lanes.SLACK_SCAN_MAX_PAGES", 2):
                found = gw.lanes.slack_find(ident)
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        scan_calls = [
            call for call in net.calls
            if "conversations.history" in call["url"] or "conversations.replies" in call["url"]
        ]
        self.assertEqual(len(scan_calls), 2)
        self.assertEqual(found["state"], "ERROR")
        self.assertFalse(found["scan_complete"])
        self.assertEqual(found["pages_scanned"], 2)
        self.assertIn("exceeded 2 total pages", found["error"])

    def test_slack_find_folds_newer_edited_reply_root(self):
        ident = "kite-find-edited-root-0001"
        stale_root = {"ts": "600.0", "text": "stale root", "reply_count": 1}
        edited_root = {
            "ts": "600.0",
            "text": slack_text(ident, "edited root copy", kind="POST"),
            "edited": {"ts": "600.2"},
        }
        gw, net = make_gateway()
        net.slack_pages = [[stale_root]]
        net.slack_reply_pages = {"600.0": [[edited_root]]}
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "FOUND")
        self.assertTrue(found["scan_complete"])
        self.assertEqual(len(found["copies"]), 1)
        self.assertEqual(found["copies"][0]["ts"], "600.0")
        self.assertEqual(found["copies"][0]["revision"], "600.2")

    def test_slack_find_keeps_only_latest_revision_per_message_ts(self):
        ident = "kite-find-latest-revision-0001"
        root = {"ts": "700.0", "text": "root", "reply_count": 2}
        old = {
            "ts": "700.1",
            "thread_ts": "700.0",
            "text": slack_text(ident, "superseded body", kind="REPLY"),
            "edited": {"ts": "700.2"},
        }
        current = {
            "ts": "700.1",
            "thread_ts": "700.0",
            "text": slack_text(ident, "canonical body", kind="REPLY"),
            "edited": {"ts": "700.3"},
        }
        gw, net = make_gateway()
        net.slack_pages = [[root]]
        net.slack_reply_pages = {"700.0": [[root, old], [current]]}
        net.pages[ident] = page(ident, "canonical body")
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            found = gw.lanes.slack_find(ident)
            report = gw.reconcile({"id": ident})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual(len(found["copies"]), 1)
        self.assertEqual(found["copies"][0]["revision"], "700.3")
        self.assertNotIn("slack:700.1", report["divergent"])

    def test_repair_refused_without_outbox(self):
        gw, net = make_gateway()
        report = gw.reconcile({"id": "missing-id-xxxx", "repair": True})
        self.assertEqual(report["state"], "REPAIR_REFUSED")
        self.assertFalse(report["repair_attempted"])

    def test_repair_flag_replays_exact_outbox_without_permission_token(self):
        ident = "missing-open-repair-0001"
        with tempfile.TemporaryDirectory(prefix="icm-open-repair-") as outbox:
            payload = build_envelope({"id": ident, "body": "repair me"})
            Path(outbox, ident + ".json").write_text(
                json.dumps({"id": ident, "full": payload}), encoding="utf-8"
            )
            gw, net = make_gateway(outbox=outbox)
            report = gw.reconcile({"id": ident, "repair": True})
            self.assertTrue(report["repair_attempted"])
            self.assertEqual(report["state"], "DURABLE_PAGE")
            self.assertEqual(report["repair"]["id"], ident)

    def test_slack_send_link_only_and_other_channel_are_legal(self):
        gw, net = make_gateway()
        os.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture-token-value"
        try:
            sent = gw.slack_send({
                "channel": "C0SOMEOTHER1",
                "text": "https://github.com/woahwhattheheck/commons/blob/main/p/x.md",
            })
            listed = gw.slack_read({})
        finally:
            os.environ.pop("COMMONS_SLACK_BOT_TOKEN", None)
        self.assertEqual(sent["state"], "ACCEPTED")
        self.assertEqual(sent["channel"], "C0SOMEOTHER1")
        self.assertNotEqual(sent["state"], "ERROR")
        slack_posts = [c for c in net.calls if c["method"] == "POST" and "chat.postMessage" in c["url"]]
        self.assertEqual(len(slack_posts), 1)
        payload = json.loads(slack_posts[0]["data"].decode("utf-8"))
        self.assertEqual(payload["channel"], "C0SOMEOTHER1")
        self.assertEqual(payload["text"], "https://github.com/woahwhattheheck/commons/blob/main/p/x.md")
        self.assertEqual(listed["state"], "FOUND")
        self.assertEqual([row["id"] for row in listed["channels"]], ["C0BRGMDQB6G", "C0SOMEOTHER1"])

    def test_discord_lane_and_human_send(self):
        gw, net = make_gateway()
        os.environ["COMMONS_DISCORD_BOT_TOKEN"] = "fixture-discord-token"
        os.environ["COMMONS_DISCORD_CHANNEL"] = "111222333"
        try:
            result = gw.post({**declared("kite-discord-only-0001"), "lanes": ["discord"]})
            sent = gw.discord_send({"channel": "444555666", "text": "https://example.com/p/x.md"})
        finally:
            os.environ.pop("COMMONS_DISCORD_BOT_TOKEN", None)
            os.environ.pop("COMMONS_DISCORD_CHANNEL", None)
        self.assertEqual(result["state"], "RECEIVED")
        self.assertEqual([row["lane"] for row in result["lanes"]], ["discord"])
        self.assertEqual(sent["state"], "ACCEPTED")
        self.assertEqual(sent["channel"], "444555666")

    def test_capability_declaration_is_optional(self):
        payload = build_envelope({"id": "kite-nodecl-0001", "body": "hi"})
        self.assertEqual(payload["from"], "UNSEATED")
        self.assertEqual(payload["to"], "TABLE")
        self.assertNotIn("is_language_model", payload)


class ServerTests(unittest.TestCase):
    def test_http_console_has_no_origin_or_bearer_admission_gate(self):
        source = (HERE / "independent_commons_mcp" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("forbidden origin", source)
        self.assertNotIn("unauthorized", source)
        self.assertNotIn("COMMONS_INDEPENDENT_BEARER", source)

    def test_manifest_names(self):
        tools = json.loads((FIXTURES / "tools.json").read_text(encoding="utf-8"))
        names = [row["name"] for row in tools["tools"]]
        self.assertEqual(names, [
            "post_to_commons",
            "reply_to_post",
            "verify_receipt",
            "read_post",
            "read_recent",
            "measure_roads",
            "create_memory_board",
            "append_memory",
            "reconcile",
            "slack_send",
            "slack_read",
            "discord_send",
            "discord_read",
            "upsert_job",
            "get_job",
            "tick_job",
            "checkpoint_job",
            "complete_job",
        ])
        schema = json.loads((FIXTURES / "envelope.schema.json").read_text(encoding="utf-8"))
        self.assertIn("id", schema["required"])

    def test_initialize_list_and_call(self):
        gw, net = make_gateway()
        net.pages[KNOWN] = page(KNOWN, "moth", "MOTH", "TABLE")
        server = MCPServer(gw)
        init = server.dispatch("initialize", {"protocolVersion": "2025-03-26"})
        self.assertEqual(init["protocolVersion"], "2025-03-26")
        self.assertEqual(init["serverInfo"]["name"], "independent-commons")
        listed = server.dispatch("tools/list", {})
        self.assertEqual(len(listed["tools"]), 18)
        rpc = server.handle({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "verify_receipt", "arguments": {"id": KNOWN}},
        })
        data = rpc["result"]["structuredContent"]
        self.assertEqual(data["state"], "DURABLE_PAGE")
        self.assertTrue(data["ok"])
        self.assertIn(SHA, data["sha_pinned_raw"])
        self.assertEqual(data["id"], KNOWN)
        fallback = server.dispatch("initialize", {"protocolVersion": "1999-01-01"})
        self.assertEqual(fallback["protocolVersion"], "2025-03-26")
        old = server.dispatch("initialize", {"protocolVersion": "2026-07-28"})
        self.assertEqual(old["protocolVersion"], "2026-07-28")

    def test_read_recent_is_bake(self):
        gw, net = make_gateway()
        net.recent = [{"id": "bake-item-0001"}]
        result = gw.read_recent({})
        self.assertEqual(result["state"], "BAKE")
        self.assertIn("bake", result["note"].lower())

    def test_action_pad_is_alias_not_second_post(self):
        gw, net = make_gateway()
        result = gw.post({**declared("kite-alias-pad-0001"), "lanes": ["ntfy", "action_pad"]})
        ntfy_posts = [c for c in net.calls if c["method"] == "POST" and "ntfy" in c["url"]]
        self.assertEqual(len(ntfy_posts), 1)
        alias = [row for row in result["lanes"] if row["lane"] == "action_pad"][0]
        self.assertEqual(alias["state"], "ALIASED")
        self.assertEqual(alias["id"], "kite-alias-pad-0001")

    def test_console_has_public_links(self):
        html = (HERE / "independent_commons_mcp" / "console.html").read_text(encoding="utf-8")
        self.assertIn("sha-pinned raw", html)
        self.assertIn("head.html", html)
        self.assertIn("action.html", html)
        self.assertIn("post_to_commons", html)
        self.assertIn("measure_roads", html)


class LiveProbeTests(unittest.TestCase):
    """GET-only. Failure here is a measured miss, not a skip."""

    def test_known_receipt_on_live_head(self):
        gw = Gateway(timeout=8.0, poll_interval=0.2)
        result = gw.verify_receipt({"id": KNOWN})
        self.assertEqual(result.get("state"), "DURABLE_PAGE", result)
        self.assertTrue(result.get("ok"))
        self.assertIn("/p/%s.md" % KNOWN, result.get("sha_pinned_raw") or "")
        self.assertEqual(len(result.get("git_sha") or ""), 40)

    def test_measure_roads_distinguishes_transport(self):
        gw = Gateway(timeout=8.0, poll_interval=0.2)
        result = gw.measure_roads({})
        self.assertEqual(result["state"], "MEASURED")
        by_lane = {}
        for row in result["lanes"]:
            by_lane.setdefault(row["lane"], []).append(row)
        self.assertIn("ntfy", by_lane)
        self.assertIn("action_pad", by_lane)
        self.assertIn("public_receipt", by_lane)
        pad = by_lane["action_pad"][0]
        self.assertEqual(pad["http_status"], 200)
        self.assertTrue(pad["application_ok"])
        receipt = by_lane["public_receipt"][0]
        self.assertEqual(receipt["state"], "DURABLE_PAGE")
        self.assertTrue(receipt["application_ok"])
        slack = by_lane["slack"][0]
        self.assertIn(slack["state"], {"CONFIGURED", "UNCONFIGURED"})
        self.assertFalse(slack["transport_ok"])
        self.assertIn("discord", by_lane)
        discord = by_lane["discord"][0]
        self.assertIn(discord["state"], {"CONFIGURED", "UNCONFIGURED"})


if __name__ == "__main__":
    raise SystemExit(unittest.main())
