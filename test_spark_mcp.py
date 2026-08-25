import json
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


if __name__ == "__main__":
    unittest.main()

