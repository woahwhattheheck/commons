import base64
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MODULE_PATH = Path(__file__).parent / "integrations" / "gemini_slack" / "peer_tool_gateway.py"
SPEC = importlib.util.spec_from_file_location("gemini_peer_tool_gateway", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class UpstreamHandler(BaseHTTPRequestHandler):
    replies = []
    prompts = []

    def log_message(self, _format, *_args):
        return

    def _send(self, value):
        raw = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._send(
            {
                "ok": True,
                "mode": "fake",
                "peers": [{"name": "TESSERA"}, {"name": "MERIDIAN"}],
            }
        )

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(size))
        text = base64.b64decode(payload["message_utf8_base64"]).decode()
        self.prompts.append(text)
        reply = self.replies.pop(0)
        self._send(
            {
                "ok": True,
                "reply": reply,
                "reply_utf8_base64": base64.b64encode(reply.encode()).decode(),
            }
        )


class McpHandler(BaseHTTPRequestHandler):
    calls = []
    tools = [
        {"name": "alpha", "description": "first", "inputSchema": {"type": "object"}},
        {
            "name": "brand_new_dynamic_tool",
            "description": "second",
            "inputSchema": {"type": "object"},
        },
    ]

    def log_message(self, _format, *_args):
        return

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(size))
        if payload["method"] == "tools/list":
            result = {"tools": self.tools}
        else:
            arguments = payload["params"]
            self.calls.append(arguments)
            result = {
                "content": [{"type": "text", "text": "ran " + arguments["name"]}]
            }
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": payload["id"], "result": result}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Fixture:
    def __enter__(self):
        UpstreamHandler.replies = []
        UpstreamHandler.prompts = []
        McpHandler.calls = []
        self.upstream_server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        self.mcp_server = ThreadingHTTPServer(("127.0.0.1", 0), McpHandler)
        self.threads = []
        for server in (self.upstream_server, self.mcp_server):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        upstream_url = "http://%s:%s" % self.upstream_server.server_address
        mcp_url = "http://%s:%s/mcp" % self.mcp_server.server_address
        self.upstream = module.UpstreamClient(upstream_url)
        self.catalog = module.McpCatalog(mcp_url, ttl_seconds=60)
        self.store = module.ToolCallStore(self.root / "calls.sqlite3")
        self.events = module.EventStore(self.root / "events.jsonl")
        self.loop = module.ToolLoop(
            self.upstream, self.catalog, self.store, max_steps=8
        )
        self.gateway = module.ToolGateway(
            ("127.0.0.1", 0),
            self.loop,
            self.events,
            self.upstream,
            self.catalog,
        )
        self.gateway_thread = threading.Thread(
            target=self.gateway.serve_forever, daemon=True
        )
        self.gateway_thread.start()
        self.base_url = "http://%s:%s" % self.gateway.server_address
        return self

    def __exit__(self, *_args):
        self.gateway.shutdown()
        self.gateway.server_close()
        self.gateway_thread.join(timeout=2)
        self.store.close()
        for server, thread in zip(
            (self.upstream_server, self.mcp_server), self.threads
        ):
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.directory.cleanup()

    def post(self, payload):
        request = urllib.request.Request(
            self.base_url + "/v1/message",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())


class ToolGatewayTests(unittest.TestCase):
    def test_plain_reply_passes_through_and_catalog_is_dynamic(self):
        with Fixture() as fixture:
            UpstreamHandler.replies = ["plain final"]
            response = fixture.post(
                {"peer": "TESSERA", "message": "hello secret-input"}
            )
            self.assertTrue(response["ok"])
            self.assertEqual(response["reply"], "plain final")
            self.assertIn("brand_new_dynamic_tool", UpstreamHandler.prompts[0])
            self.assertEqual(McpHandler.calls, [])
            self.assertNotIn(
                "hello secret-input",
                (fixture.root / "events.jsonl").read_text(),
            )

    def test_multiple_arbitrary_tools_feed_results_through_same_upstream(self):
        with Fixture() as fixture:
            UpstreamHandler.replies = [
                '<commons_tool_call>{"call_id":"c1","name":"alpha","arguments":{"x":1}}</commons_tool_call>',
                '<commons_tool_call>{"call_id":"c2","name":"brand_new_dynamic_tool","arguments":{"y":2}}</commons_tool_call>',
                "all done",
            ]
            response = fixture.post({"peer": "MERIDIAN", "message": "use tools"})
            self.assertEqual(response["reply"], "all done")
            self.assertEqual(
                [item["name"] for item in McpHandler.calls],
                ["alpha", "brand_new_dynamic_tool"],
            )
            self.assertIn("ran alpha", UpstreamHandler.prompts[1])
            self.assertIn("ran brand_new_dynamic_tool", UpstreamHandler.prompts[2])

    def test_malformed_envelope_gets_one_correction_turn(self):
        with Fixture() as fixture:
            UpstreamHandler.replies = [
                "<commons_tool_call>{bad}</commons_tool_call>",
                "recovered",
            ]
            response = fixture.post({"peer": "TESSERA", "message": "recover"})
            self.assertEqual(response["reply"], "recovered")
            self.assertIn("malformed", UpstreamHandler.prompts[1])

    def test_async_reply_is_retained_and_byte_safe(self):
        with Fixture() as fixture:
            UpstreamHandler.replies = ["async ✓"]
            accepted = fixture.post(
                {"peer": "MERIDIAN", "message": "later", "async": True}
            )
            request_id = accepted["request_id"]
            event = None
            for _ in range(30):
                with urllib.request.urlopen(
                    fixture.base_url + "/v1/requests/" + request_id,
                    timeout=2,
                ) as response:
                    event = json.loads(response.read())["event"]
                if event["status"] == "completed":
                    break
                time.sleep(0.02)
            self.assertEqual(event["status"], "completed")
            self.assertEqual(
                base64.b64decode(event["reply_utf8_base64"]).decode(),
                "async ✓",
            )
            with urllib.request.urlopen(
                fixture.base_url + "/v1/last?peer=MERIDIAN",
                timeout=2,
            ) as response:
                last = json.loads(response.read())["event"]
            self.assertEqual(last["request_id"], request_id)
            self.assertEqual(last["reply"], "async ✓")

    def test_call_id_deduplicates_without_retaining_arguments(self):
        with Fixture() as fixture:
            first = fixture.store.execute_once(
                "r1",
                "same",
                "alpha",
                {"secret": "do-not-store"},
                fixture.catalog.call,
            )
            second = fixture.store.execute_once(
                "r1",
                "same",
                "alpha",
                {"secret": "do-not-store"},
                fixture.catalog.call,
            )
            self.assertEqual(first, second)
            self.assertEqual(len(McpHandler.calls), 1)
            database = sqlite3.connect(fixture.root / "calls.sqlite3")
            dump = "\n".join(database.iterdump())
            database.close()
            self.assertNotIn("do-not-store", dump)


if __name__ == "__main__":
    unittest.main()
