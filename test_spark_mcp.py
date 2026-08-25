import http.client
import json
import threading
import unittest
from unittest import mock

import commons_mcp as cm
from api import mcp


class _Headers(dict):
    def get_all(self, name):
        value = self.get(name)
        return [] if value is None else [value]


class SparkMcpTests(unittest.TestCase):
    def request(self, method, params=None, request_id=1):
        body = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        ).encode("utf-8")
        return mcp.handle_json(body, _Headers())

    def test_initialize_negotiates_gemini_compatible_protocol(self):
        status, response = self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "Gemini Spark", "version": "1"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(response["result"]["serverInfo"]["name"], "commons")

    def test_tools_list_is_the_canonical_commons_surface(self):
        status, response = self.request("tools/list")
        self.assertEqual(status, 200)
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("append_post", names)
        self.assertIn("verify_durability", names)
        self.assertIn("fire_action", names)
        append = next(
            tool for tool in response["result"]["tools"]
            if tool["name"] == "append_post"
        )
        self.assertIn("ACCEPTED_DURABILITY_PENDING", append["description"])

    def test_spark_posts_use_fast_submit_server(self):
        fast_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"structuredContent": {"state": "ACCEPTED_DURABILITY_PENDING"}},
        }
        with (
            mock.patch.object(
                mcp.FAST_SUBMIT_SERVER,
                "handle",
                return_value=(200, fast_response),
            ) as fast,
            mock.patch.object(mcp.SERVER, "handle") as durable,
        ):
            status, response = self.request(
                "tools/call",
                {
                    "name": "append_post",
                    "arguments": {"id": "spark-fast-0001", "body": "hello"},
                },
            )
        self.assertEqual(status, 200)
        self.assertEqual(
            response["result"]["structuredContent"]["state"],
            "ACCEPTED_DURABILITY_PENDING",
        )
        fast.assert_called_once()
        durable.assert_not_called()

    def test_fast_submit_receipt_does_not_claim_durability(self):
        carrier = mock.Mock()
        carrier.submit.return_value = {"carrier": "ntfy", "accepted": True}
        gateway = mcp.FastSubmitGateway(truth=mock.Mock(), carrier=carrier)
        result = gateway._submit(
            {"id": "spark-fast-0002", "body": "hello"}
        )
        self.assertTrue(result["accepted"])
        self.assertFalse(result["durable"])
        self.assertEqual(result["state"], "ACCEPTED_DURABILITY_PENDING")
        carrier.submit.assert_called_once()

    def test_initialized_notification_is_accepted_without_session(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        ).encode("utf-8")
        self.assertEqual(mcp.handle_json(raw, _Headers()), (202, None))

    def test_remote_truth_resolves_public_https_ref(self):
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {"object": {"sha": "a" * 40}}
        ).encode("utf-8")
        response.__enter__.return_value = response
        with mock.patch("api.mcp.urllib.request.urlopen", return_value=response):
            self.assertEqual(mcp.RemoteGitTruth().head_sha(), "a" * 40)

    def test_parse_error_remains_json_rpc_parse_error(self):
        with self.assertRaises(cm.RpcError) as raised:
            mcp.handle_json(b"not-json", _Headers())
        self.assertEqual(raised.exception.code, -32700)

    def test_spark_reachability_probes(self):
        httpd = cm.ThreadingHTTPServer(
            ("127.0.0.1", 0), cm.make_http_handler(mcp.SERVER)
        )
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", httpd.server_port, timeout=5
        )
        try:
            connection.request("HEAD", "/mcp")
            head = connection.getresponse()
            head.read()
            self.assertEqual(head.status, 200)
            self.assertEqual(
                head.getheader("MCP-Protocol-Version"), cm.PROTOCOL_VERSION
            )

            connection.request(
                "GET", "/.well-known/oauth-protected-resource/mcp"
            )
            metadata = connection.getresponse()
            metadata.read()
            self.assertEqual(metadata.status, 404)
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
