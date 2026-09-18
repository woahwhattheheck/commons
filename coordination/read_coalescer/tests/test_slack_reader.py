from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from coordination.read_coalescer.core import Broker, InvalidInput, RateLimited, ProviderFailure
from coordination.read_coalescer.slack_reader import NoRedirect, SlackReader, retry_after_ms


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body if type(body) is bytes else json.dumps(body).encode()
        self.status, self.headers = status, headers or {}
        self.closed = False
    def read(self, size):
        return self.body[:size]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True


class AdapterTests(unittest.TestCase):
    def reader(self, body=None, **kwargs):
        self.requests = []
        self.response = Response(body if body is not None else {"ok": True, "channels": [], "response_metadata": {"next_cursor": ""}})
        def transport(req, timeout):
            self.requests.append((req, timeout))
            return self.response
        return SlackReader(token="SYNTHETIC-CREDENTIAL", app="A1", workspace="T1",
                           visibility_epoch="epoch1", transport=transport, **kwargs)

    def test_one_get_no_body_token_only_header(self):
        reader = self.reader()
        page = reader(reader.request("conversations.list", {"limit": 20, "exclude_archived": True, "cursor": "abc=="}))
        self.assertEqual(len(self.requests), 1)
        req, timeout = self.requests[0]
        self.assertEqual(req.method, "GET")
        self.assertIsNone(req.data)
        self.assertNotIn("SYNTHETIC-CREDENTIAL", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer SYNTHETIC-CREDENTIAL")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
        self.assertEqual(query["cursor"], ["abc=="])
        self.assertEqual(query["exclude_archived"], ["true"])
        self.assertEqual(timeout, 10)
        self.assertTrue(self.response.closed)
        self.assertTrue(page.collection_end)

    def test_empty_page_with_cursor_is_not_complete(self):
        reader = self.reader({"ok": True, "channels": [], "response_metadata": {"next_cursor": "next"}})
        page = reader(reader.request("conversations.list", {}))
        self.assertFalse(page.collection_end)
        self.assertEqual(page.next_cursor, "next")

    def test_opaque_cursor_is_not_trimmed_or_reencoded(self):
        for cursor in (" next+== ", "\topaque/=\n", " "):
            with self.subTest(cursor=repr(cursor)):
                reader = self.reader({"ok": True, "channels": [], "response_metadata": {"next_cursor": cursor}})
                page = reader(reader.request("conversations.list", {}))
                self.assertIs(page.collection_end, False)
                self.assertEqual(page.next_cursor, cursor)
                reader(reader.request("conversations.list", {"cursor": page.next_cursor}))
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.requests[-1][0].full_url).query)
                self.assertEqual(query["cursor"], [cursor])

    def test_cursor_survives_independent_time_pagination_flag(self):
        reader = self.reader({"ok": True, "messages": [], "has_more": False, "response_metadata": {"next_cursor": "next"}})
        page = reader(reader.request("conversations.history", {"channel": "C1"}))
        self.assertFalse(page.collection_end)
        self.assertEqual(page.next_cursor, "next")

    def test_more_without_cursor_stays_incomplete(self):
        reader = self.reader({"ok": True, "messages": [], "has_more": True})
        page = reader(reader.request("conversations.history", {"channel": "C1"}))
        self.assertFalse(page.collection_end)
        self.assertIsNone(page.next_cursor)

    def test_metadata_absent_stays_unknown_in_supported_profile(self):
        reader = self.reader({"ok": True, "channels": []})
        page = reader(reader.request("conversations.list", {}))
        self.assertIsNone(page.collection_end)

    def test_info_is_not_a_collection(self):
        reader = self.reader({"ok": True, "user": {"id": "U1"}})
        page = reader(reader.request("users.info", {"user": "U1"}))
        self.assertIsNone(page.collection_end)

    def test_wrong_account_scope_never_reaches_transport(self):
        reader = self.reader()
        other = SlackReader(token="OTHER-CREDENTIAL", app="A1", workspace="T1", visibility_epoch="epoch1")
        foreign = other.request("conversations.list", {})
        with self.assertRaises(InvalidInput):
            reader(foreign)
        self.assertEqual(self.requests, [])

    def test_permission_epoch_changes_cache_identity(self):
        first = self.reader()
        second = SlackReader(token="SYNTHETIC-CREDENTIAL", app="A1", workspace="T1", visibility_epoch="epoch2")
        one, two = first.request("conversations.list", {}), second.request("conversations.list", {})
        self.assertNotEqual(one.key, two.key)
        self.assertEqual(one.bucket, two.bucket)
        self.assertNotIn("SYNTHETIC-CREDENTIAL", repr(one))

    def test_mutating_and_unknown_methods_rejected_before_network(self):
        reader = self.reader()
        for method in ("chat.postMessage", "conversations.join", "files.upload", "admin.users.remove", "search.all"):
            with self.assertRaises(InvalidInput):
                reader.request(method, {})
        self.assertEqual(self.requests, [])

    def test_required_parameters_and_exact_types(self):
        reader = self.reader()
        cases = [("conversations.history", {}), ("conversations.replies", {"channel": "C1"}),
                 ("users.info", {}), ("conversations.list", {"limit": True}),
                 ("conversations.list", {"limit": 0}), ("conversations.list", {"token": "bad"}),
                 ("conversations.history", {"channel": "C1", "latest": 1.25}),
                 ("conversations.history", {"channel": "C1", "inclusive": "true"}),
                 ("conversations.info", {"channel": "bad&token=secret"})]
        for method, params in cases:
            with self.subTest(method=method, params=params), self.assertRaises(InvalidInput):
                reader.request(method, params)
        self.assertEqual(self.requests, [])

    def test_provider_ok_must_be_literal_true(self):
        for body in ({"ok": False, "error": "invalid_auth"}, {"ok": 1, "channels": []},
                     {"channels": []}, ["ok"], {"ok": True, "channels": {}},
                     {"ok": True, "channels": [], "response_metadata": []},
                     {"ok": True, "channels": [], "response_metadata": {"next_cursor": 3}},
                     {"ok": True, "channels": [], "has_more": "true"}):
            reader = self.reader(body)
            with self.subTest(body=body), self.assertRaises(ProviderFailure):
                reader(reader.request("conversations.list", {}))

    def test_bad_provider_json_duplicate_float_or_html_is_failure(self):
        for raw in (b'{"ok":true,"ok":false,"channels":[]}', b'{"ok":true,"n":1.5,"channels":[]}', b'<html>no</html>'):
            reader = self.reader(raw)
            with self.assertRaises(ProviderFailure) as error:
                reader(reader.request("conversations.list", {}))
            self.assertEqual(error.exception.code, "INVALID_PROVIDER_JSON")

    def test_response_size_limit(self):
        reader = self.reader(b'x'*200, max_response_bytes=128)
        with self.assertRaises(ProviderFailure) as error:
            reader(reader.request("conversations.list", {}))
        self.assertEqual(error.exception.code, "RESPONSE_TOO_LARGE")

    def test_http_429_one_attempt_shared_delay(self):
        calls = []
        body = io.BytesIO(b"private error body")
        def transport(req, timeout):
            calls.append(req)
            raise urllib.error.HTTPError(req.full_url, 429, "rate", {"Retry-After": "120"}, body)
        reader = SlackReader(token="SYNTHETIC", app="A1", workspace="T1", visibility_epoch="1", transport=transport)
        with tempfile.TemporaryDirectory() as tmp:
            b = Broker(Path(tmp)/"state.db", clock=lambda: 1000)
            req = reader.request("conversations.list", {})
            result = b.read_once(req, reader)
            self.assertEqual(result.reason, "RATE_LIMITED")
            self.assertEqual(result.retry_at_ms, 121_000)
            self.assertIsNone(result.page)
            second = b.read_once(req, reader)
            self.assertEqual(second.reason, "PROVIDER_COOLDOWN")
            self.assertEqual(len(calls), 1)
            self.assertTrue(body.closed)

    def test_http_200_rate_limited_body_also_cools_down(self):
        reader = self.reader({"ok": False, "error": "ratelimited"})
        self.response.headers = {"Retry-After": "5"}
        with self.assertRaises(RateLimited) as error:
            reader(reader.request("conversations.list", {}))
        self.assertEqual(error.exception.retry_after_ms, 5000)
        self.assertEqual(len(self.requests), 1)

    def test_missing_retry_header_has_explicit_fallback_reason(self):
        reader = self.reader({"ok": False, "error": "ratelimited"})
        with self.assertRaises(RateLimited) as error:
            reader(reader.request("conversations.list", {}))
        self.assertEqual(error.exception.code, "RATE_LIMITED_RETRY_AFTER_UNKNOWN")
        self.assertEqual(error.exception.retry_after_ms, 60_000)

    def test_retry_after_bounds_no_normal_delay_shortening(self):
        for raw, expected in (("0", 0), (" 30 ", 30_000), ("8640000", 8_640_000_000), ("999999999999", 999_999_999_999_000)):
            self.assertEqual(retry_after_ms(raw), (expected, True))
        for bad in (None, "1.5", "+1", "-1", "tomorrow", "١"):
            self.assertEqual(retry_after_ms(bad), (60_000, False))

    def test_huge_numeric_retry_after_never_becomes_short_fallback(self):
        delay, known = retry_after_ms("9"*1000)
        self.assertFalse(known)
        self.assertGreater(delay, 8_000_000_000_000_000)
        error = RateLimited(delay)
        self.assertEqual(error.retry_after_ms, delay)

    def test_non_429_http_error_and_transport_error_are_not_retried(self):
        for exception in (urllib.error.HTTPError("https://slack.com", 503, "bad", {}, io.BytesIO()),
                          urllib.error.URLError("token may be in raw error"), TimeoutError("secret")):
            calls = []
            def broken(req, timeout):
                calls.append(1)
                raise exception
            reader = SlackReader(token="SYNTHETIC", app="A1", workspace="T1", visibility_epoch="1", transport=broken)
            with self.assertRaises(ProviderFailure) as error:
                reader(reader.request("conversations.list", {}))
            self.assertNotIn("secret", str(error.exception))
            self.assertEqual(calls, [1])


class LoopbackHTTPTests(unittest.TestCase):
    def test_redirect_not_followed_with_credentials(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.path)
                if self.path == "/start":
                    self.send_response(302)
                    self.send_header("Location", "/must-not-be-requested")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/start",
                headers={"Authorization": "Bearer SYNTHETIC-NO-REAL-CREDENTIAL"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.build_opener(NoRedirect()).open(req, timeout=2)
            error.exception.close()
            self.assertEqual(error.exception.code, 302)
            self.assertEqual(seen, ["/start"])
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()


class CLITests(unittest.TestCase):
    def test_demo_stats_maintenance_and_missing_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = [sys.executable, "-m", "coordination.read_coalescer", "--db", str(Path(tmp)/"s.db")]
            demo = subprocess.run(base + ["demo"], capture_output=True, text=True, timeout=10)
            self.assertEqual(demo.returncode, 0, demo.stderr)
            output = json.loads(demo.stdout)
            self.assertEqual(output["scenario"], "OFFLINE_SYNTHETIC")
            self.assertEqual(output["provider_callback_calls_this_process"], 1)
            self.assertEqual(output["second"]["status"], "CACHE")
            stats = subprocess.run(base + ["stats"], capture_output=True, text=True, timeout=10)
            self.assertEqual(stats.returncode, 0, stats.stderr)
            self.assertEqual(json.loads(stats.stdout)["counters"]["provider_dispatches"], 1)
            maintenance = subprocess.run(base + ["maintain"], capture_output=True, text=True, timeout=10)
            self.assertEqual(maintenance.returncode, 0)
            params = Path(tmp)/"params.json"
            params.write_text('{}')
            env = dict(os.environ)
            env.pop("COALESCER_TEST_ABSENT_TOKEN", None)
            result = subprocess.run(base + ["slack-read", "--app", "A1", "--workspace", "T1",
                "--visibility-epoch", "1", "--method", "conversations.list", "--params", str(params),
                "--token-env", "COALESCER_TEST_ABSENT_TOKEN"], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(json.loads(result.stderr)["reason"], "LOCAL_CONFIGURATION_OR_STORAGE_ERROR")
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
