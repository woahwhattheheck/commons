import http.client
import json
import threading
import unittest
from pathlib import Path

import commons_mcp as cm
from api import mcp


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "carriers" / "catalog.json"
TELEGRAM_CARD = ROOT / "carriers" / "telegram.json"


class TelegramCatalogPickupTests(unittest.TestCase):
    def test_catalog_points_at_the_existing_telegram_card(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in catalog["carriers"]}
        self.assertIn("telegram", rows)
        self.assertEqual(rows["telegram"]["card"], "carriers/telegram.json")
        self.assertEqual(rows["telegram"]["name"], "Telegram peer group")

    def test_telegram_card_keeps_the_adam_invite(self):
        card = json.loads(TELEGRAM_CARD.read_text(encoding="utf-8"))
        self.assertEqual(card["id"], "telegram")
        self.assertEqual(card["invite"], "https://t.me/+rbbklgtbu7lkYWFh")
        self.assertEqual(card["mcp_url"], mcp.PUBLIC_MCP_URL)
        self.assertTrue(str(card["auth"]).startswith("none"))

    def test_carriers_telegram_http_route(self):
        httpd = cm.ThreadingHTTPServer(("127.0.0.1", 0), mcp.handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", httpd.server_port, timeout=5
        )
        try:
            connection.request("GET", "/carriers/telegram")
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["id"], "telegram")
            self.assertEqual(payload["invite"], "https://t.me/+rbbklgtbu7lkYWFh")
            self.assertEqual(payload["mcp_url"], mcp.PUBLIC_MCP_URL)
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
