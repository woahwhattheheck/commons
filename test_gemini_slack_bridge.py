import base64
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MODULE_PATH = Path(__file__).parent / "integrations" / "gemini_slack" / "bridge.py"
SPEC = importlib.util.spec_from_file_location("gemini_slack_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)


class FakeGatewayHandler(BaseHTTPRequestHandler):
    requests = []
    reply = "Gateway → Slack: byte-safe ✓"

    def log_message(self, _format, *_args):
        return

    def _send(self, status, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "mode": "test", "upstream_ok": True, "peers": ["MERIDIAN", "TESSERA"]})
            return
        if self.path.startswith("/v1/requests/request-1"):
            encoded = base64.b64encode(self.reply.encode("utf-8")).decode("ascii")
            self._send(
                200,
                {
                    "ok": True,
                    "event": {
                        "status": "completed",
                        "reply": self.reply,
                        "reply_utf8_base64": encoded,
                    },
                },
            )
            return
        self._send(404, {"ok": False})

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(size).decode("utf-8"))
        self.requests.append(body)
        self._send(202, {"ok": True, "request_id": "request-1", "status": "queued"})


class FakeSink:
    def __init__(self):
        self.posts = []

    def post(self, channel, thread_ts, peer, text):
        self.posts.append((channel, thread_ts, peer, text))


class FailingSink:
    def post(self, _channel, _thread_ts, _peer, _text):
        raise RuntimeError("Slack temporarily unavailable")


class GatewayFixture:
    def __enter__(self):
        FakeGatewayHandler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGatewayHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.client = bridge.GatewayClient(f"http://{host}:{port}")
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class GeminiSlackBridgeTests(unittest.TestCase):
    def test_routes_explicit_peer_and_remembers_thread_default(self):
        self.assertEqual(bridge.route_message("<@U123> Tessera: look around"), ("TESSERA", "look around"))
        self.assertEqual(bridge.route_message("keep going", "TESSERA"), ("TESSERA", "keep going"))
        self.assertEqual(bridge.route_message("hello"), ("MERIDIAN", "hello"))

    def test_gateway_uses_async_byte_safe_request_and_recovers_reply(self):
        with GatewayFixture() as fixture:
            self.assertTrue(fixture.client.health()["ok"])
            request_id = fixture.client.submit("TESSERA", "snowman ☃")
            event = fixture.client.wait(request_id, deadline_seconds=2)
        self.assertEqual(event["status"], "completed")
        sent = FakeGatewayHandler.requests[0]
        self.assertTrue(sent["async"])
        self.assertNotIn("message", sent)
        decoded = base64.b64decode(sent["message_utf8_base64"]).decode("utf-8")
        self.assertEqual(decoded, "snowman ☃")

    def test_event_delivers_once_and_database_retains_no_content(self):
        with tempfile.TemporaryDirectory() as directory, GatewayFixture() as fixture:
            database = Path(directory) / "state.sqlite3"
            store = bridge.BridgeStore(database)
            sink = FakeSink()
            service = bridge.GeminiSlackBridge(fixture.client, store, sink, delivery_deadline=2)
            event = {"type": "app_mention", "channel": "C1", "ts": "1.2", "text": "Tessera: hello secret-marker"}
            self.assertTrue(service.handle_event("Ev1", event))
            self.assertFalse(service.handle_event("Ev1", event))
            self.assertEqual(store.state("Ev1"), "delivered")
            self.assertEqual(sink.posts, [("C1", "1.2", "TESSERA", FakeGatewayHandler.reply)])
            store.close()

            connection = sqlite3.connect(database)
            dump = "\n".join(connection.iterdump())
            connection.close()
            self.assertNotIn("hello secret-marker", dump)
            self.assertNotIn(FakeGatewayHandler.reply, dump)

    def test_pending_request_is_delivered_after_restart(self):
        with tempfile.TemporaryDirectory() as directory, GatewayFixture() as fixture:
            database = Path(directory) / "state.sqlite3"
            first = bridge.BridgeStore(database)
            self.assertTrue(first.claim("Ev2", "D1", "2.3", "MERIDIAN"))
            first.attach_request("Ev2", "request-1")
            first.close()

            second = bridge.BridgeStore(database)
            sink = FakeSink()
            service = bridge.GeminiSlackBridge(fixture.client, second, sink, delivery_deadline=2)
            self.assertEqual(service.recover_pending(), 1)
            self.assertEqual(second.state("Ev2"), "delivered")
            self.assertEqual(sink.posts[0][3], FakeGatewayHandler.reply)
            second.close()

    def test_slack_delivery_failure_keeps_retained_request_pending(self):
        with tempfile.TemporaryDirectory() as directory, GatewayFixture() as fixture:
            database = Path(directory) / "state.sqlite3"
            first = bridge.BridgeStore(database)
            service = bridge.GeminiSlackBridge(fixture.client, first, FailingSink(), delivery_deadline=2)
            event = {"type": "app_mention", "channel": "C2", "ts": "3.4", "text": "Meridian: retained"}
            self.assertTrue(service.handle_event("Ev3", event))
            self.assertEqual(first.state("Ev3"), "pending")
            first.close()

            second = bridge.BridgeStore(database)
            sink = FakeSink()
            restarted = bridge.GeminiSlackBridge(fixture.client, second, sink, delivery_deadline=2)
            self.assertEqual(restarted.recover_pending(), 1)
            self.assertEqual(second.state("Ev3"), "delivered")
            self.assertEqual(sink.posts[0][3], FakeGatewayHandler.reply)
            second.close()

    def test_ignores_bot_and_non_dm_message_events(self):
        self.assertFalse(bridge._is_supported_slack_event({"type": "message", "channel_type": "channel"}))
        self.assertTrue(bridge._is_supported_slack_event({"type": "message", "channel_type": "im"}))
        self.assertTrue(bridge._is_supported_slack_event({"type": "app_mention"}))

    def test_slack_chunking_is_bounded_and_lossless_by_words(self):
        source = " ".join(["word"] * 2_000)
        pieces = list(bridge.chunks(source, 120))
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(piece) <= 120 for piece in pieces))
        self.assertEqual(" ".join(pieces).split(), source.split())


if __name__ == "__main__":
    unittest.main()
