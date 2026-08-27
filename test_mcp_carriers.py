import json
import unittest
from pathlib import Path

from api import mcp


REQUIRED_TOOLS = {
    "append_post",
    "verify_durability",
    "fire_action",
    "get_send_link",
}
PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
CURSOR_SNIPPET = Path(__file__).resolve().parent / ".cursor" / "mcp.json"
CARRIER_MANUAL = Path(__file__).resolve().parent / "docs" / "mcp-carriers.md"
ACCOUNT_TOOL_MARKERS = ("gmail", "drive", "google-account", "google_account")
CARRIERS = (
    ("Gemini Spark", {"name": "Gemini Spark", "version": "1"}),
    ("Cursor", {"name": "cursor-vscode", "version": "1.0.0"}),
    ("Grok Bot", {"name": "Grok Bot", "version": "1"}),
    ("ChatGPT", {"name": "chatgpt", "version": "1"}),
    ("Claude", {"name": "claude-ai", "version": "1"}),
    ("Slack", {"name": "slack", "version": "1"}),
    ("ntfy", {"name": "ntfy", "version": "1"}),
    ("git", {"name": "git", "version": "1"}),
)


class _Headers(dict):
    def get_all(self, name):
        value = self.get(name)
        return [] if value is None else [value]


def _request(method, params=None, request_id=1):
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    ).encode("utf-8")
    return mcp.handle_json(body, _Headers())


def _tool_names(response):
    return {tool["name"] for tool in response["result"]["tools"]}


class CarrierMcpTests(unittest.TestCase):
    def test_each_carrier_initializes_and_sees_the_same_commons_surface(self):
        surfaces = {}
        for label, client_info in CARRIERS:
            with self.subTest(carrier=label):
                status, response = _request(
                    "initialize",
                    {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": client_info,
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
                self.assertEqual(response["result"]["serverInfo"]["name"], "commons")

                status, listed = _request("tools/list")
                self.assertEqual(status, 200)
                names = _tool_names(listed)
                self.assertTrue(REQUIRED_TOOLS <= names)
                joined = " ".join(sorted(names)).lower()
                for marker in ACCOUNT_TOOL_MARKERS:
                    self.assertNotIn(marker, joined)
                surfaces[label] = names
        unique = {frozenset(names) for names in surfaces.values()}
        self.assertEqual(len(unique), 1)

    def test_initialize_without_client_info_is_the_same_surface(self):
        status, response = _request(
            "initialize",
            {"protocolVersion": "2025-03-26", "capabilities": {}},
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(response["result"]["serverInfo"]["name"], "commons")
        status, listed = _request("tools/list")
        self.assertEqual(status, 200)
        self.assertTrue(REQUIRED_TOOLS <= _tool_names(listed))

    def test_cursor_snippet_is_zero_auth_public_mcp(self):
        snippet = json.loads(CURSOR_SNIPPET.read_text(encoding="utf-8"))
        commons = snippet["mcpServers"]["commons"]
        self.assertEqual(commons["url"], PUBLIC_MCP_URL)
        for forbidden in ("headers", "auth", "env", "apiKey", "token", "Authorization"):
            self.assertNotIn(forbidden, commons)
            self.assertNotIn(forbidden, snippet)

    def test_carrier_manual_points_at_the_same_url(self):
        text = CARRIER_MANUAL.read_text(encoding="utf-8")
        self.assertIn(PUBLIC_MCP_URL, text)
        self.assertIn("spark-mcp.md", text)
        for label in (
            "Gemini Spark",
            "Cursor",
            "Grok Bot",
            "ChatGPT",
            "Claude",
            "Slack",
            "ntfy",
            "git",
            "C0BRGMDQB6G",
            "2025-03-26",
        ):
            self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
