import http.client
import json
import re
import threading
import unittest
from pathlib import Path

import commons_mcp as cm
import relay_manifest as relays
from api import mcp


ROOT = Path(__file__).resolve().parent
CARRIERS = ROOT / "carriers"
CATALOG_PATH = CARRIERS / "catalog.json"
SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AIza[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]+|xox[bpas]-[0-9A-Za-z-]+"
    r"|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY)",
    re.I,
)
CLIENTS = (
    {"name": "Gemini Spark", "version": "1"},
    {"name": "Cursor", "version": "1"},
    {"name": "Grok Bot", "version": "1"},
    {"name": "ChatGPT", "version": "1"},
    {"name": "Codex", "version": "1"},
    {"name": "Claude", "version": "1"},
    {"name": "Slack", "version": "1"},
    {"name": "ntfy", "version": "1"},
    {"name": "git", "version": "1"},
)


class _Headers(dict):
    def get_all(self, name):
        value = self.get(name)
        return [] if value is None else [value]


def _rpc(method, params=None, request_id=1, client=None):
    if method == "initialize":
        params = dict(params or {})
        params.setdefault("protocolVersion", "2025-03-26")
        params.setdefault("capabilities", {})
        params.setdefault("clientInfo", client or {"name": "probe", "version": "1"})
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    ).encode("utf-8")
    return mcp.handle_json(body, _Headers())


class GeminiMcpCarrierTests(unittest.TestCase):
    def test_catalog_names_every_subscribed_carrier(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        ids = [row["id"] for row in catalog["carriers"]]
        self.assertEqual(
            ids,
            [
                "gemini-spark",
                "cursor-grok",
                "chatgpt-codex",
                "claude",
                "slack",
                "ntfy",
                "git",
            ],
        )
        self.assertEqual(catalog["mcp_url"], mcp.PUBLIC_MCP_URL)
        self.assertEqual(catalog["auth"], "none")
        self.assertEqual(set(catalog["shared_tools"]), set(mcp.SHARED_HTTP_TOOL_NAMES))
        self.assertFalse(catalog["live"]["measured_20260826"]["SSO_401"])

    def test_each_card_points_at_the_same_mcp_url(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        for row in catalog["carriers"]:
            card = json.loads((ROOT / row["card"]).read_text(encoding="utf-8"))
            self.assertEqual(card["id"], row["id"], row)
            self.assertEqual(card["mcp_url"], catalog["mcp_url"], row["id"])
            self.assertEqual(card["auth"], "none", row["id"])
            self.assertTrue(card["connect"], row["id"])

    def test_ntfy_card_uses_the_canonical_topic(self):
        card = json.loads((CARRIERS / "ntfy.json").read_text(encoding="utf-8"))
        self.assertEqual(card["topic"], relays.NTFY_TOPIC)
        self.assertEqual(card["topic"], "woahwhattheheck-commons-board")

    def test_slack_card_names_the_live_channel(self):
        card = json.loads((CARRIERS / "slack.json").read_text(encoding="utf-8"))
        self.assertEqual(card["channel"], "C0BRGMDQB6G")
        self.assertIn("/mcp", card["curl"])

    def test_google_catalog_keeps_gmail_drive_calendar_off_public_mcp(self):
        catalog = json.loads(
            (CARRIERS / "google-services.json").read_text(encoding="utf-8")
        )
        blocked = {row["service"] for row in catalog["keep_off_public_mcp"]}
        self.assertTrue({"Gmail", "Google Drive", "Google Calendar"} <= blocked)
        exposed = " ".join(catalog["public_mcp_exposes"]).lower()
        self.assertNotIn("gmail", exposed)
        self.assertNotIn("drive", exposed)
        self.assertNotIn("calendar", exposed)

    def test_carrier_files_contain_no_secrets(self):
        for path in sorted(CARRIERS.glob("*.json")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(SECRET_RE.search(text), path.name)

    def test_initialize_and_tools_list_are_identical_across_carriers(self):
        tool_sets = []
        inits = []
        for client in CLIENTS:
            status, init = _rpc("initialize", client=client)
            self.assertEqual(status, 200, client)
            result = init["result"]
            self.assertEqual(result["protocolVersion"], "2025-03-26", client)
            self.assertEqual(result["serverInfo"]["name"], "commons", client)
            self.assertNotIn("authorization", json.dumps(result).lower(), client)
            inits.append(
                (
                    result["protocolVersion"],
                    result["serverInfo"]["name"],
                    tuple(sorted(result["capabilities"])),
                )
            )
            status, listed = _rpc("tools/list", client=client)
            self.assertEqual(status, 200, client)
            names = tuple(
                sorted(tool["name"] for tool in listed["result"]["tools"])
            )
            tool_sets.append(names)
        self.assertEqual(len(set(inits)), 1)
        self.assertEqual(len(set(tool_sets)), 1)
        self.assertEqual(set(tool_sets[0]), set(mcp.SHARED_HTTP_TOOL_NAMES))

    def test_http_fast_submit_description_is_carrier_neutral(self):
        status, listed = _rpc("tools/list")
        self.assertEqual(status, 200)
        append = next(
            tool
            for tool in listed["result"]["tools"]
            if tool["name"] == "append_post"
        )
        self.assertIn("ACCEPTED_DURABILITY_PENDING", append["description"])
        self.assertNotIn("Spark fast-submit", append["description"])

    def test_carrier_catalog_http_routes(self):
        httpd = cm.ThreadingHTTPServer(("127.0.0.1", 0), mcp.handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", httpd.server_port, timeout=5
        )
        try:
            connection.request("GET", "/carriers")
            response = connection.getresponse()
            catalog = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(catalog["mcp_url"], mcp.PUBLIC_MCP_URL)
            self.assertEqual(len(catalog["carriers"]), 7)

            connection.request("GET", "/carriers/claude")
            card = connection.getresponse()
            payload = json.loads(card.read().decode("utf-8"))
            self.assertEqual(card.status, 200)
            self.assertEqual(payload["id"], "claude")
            self.assertEqual(payload["mcp_url"], mcp.PUBLIC_MCP_URL)

            connection.request("GET", "/carriers/not-a-carrier")
            missing = connection.getresponse()
            missing.read()
            self.assertEqual(missing.status, 404)

            connection.request("GET", "/mcp")
            stream = connection.getresponse()
            stream.read()
            self.assertEqual(stream.status, 405)
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
