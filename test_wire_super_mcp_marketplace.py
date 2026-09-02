#!/usr/bin/env python3
"""Marketplace fold leftover: commons-network beside commons-grok-cloud."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import host.wire_super_mcp_marketplace as fold


ROOT = Path(__file__).resolve().parent
PUBLIC_MCP = "https://commons-spark-mcp.vercel.app/mcp"


class WireSuperMcpMarketplaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.market = fold.marketplace()

    def test_validate_ok(self) -> None:
        receipt = fold.validate(self.market)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["url"], PUBLIC_MCP)
        self.assertEqual(receipt["cite"], "wire-super-mcp-fold-20260902-01")
        self.assertEqual(receipt["plugins"], ["commons-grok-cloud", "commons-network"])

    def test_grok_cloud_stays_first(self) -> None:
        self.assertEqual(self.market["plugins"][0]["name"], "commons-grok-cloud")
        self.assertEqual(
            self.market["plugins"][0]["source"]["path"],
            "./plugins/commons-grok-cloud",
        )

    def test_network_sits_beside_grok_cloud(self) -> None:
        names = [row["name"] for row in self.market["plugins"]]
        self.assertIn("commons-network", names)
        network = next(row for row in self.market["plugins"] if row["name"] == "commons-network")
        self.assertEqual(network["source"]["path"], "./integrations/commons_network_plugin")
        self.assertEqual(network["policy"]["installation"], "AVAILABLE")
        self.assertNotIn("authentication", network["policy"])
        self.assertTrue((ROOT / "integrations" / "commons_network_plugin" / ".codex-plugin" / "plugin.json").is_file())

    def test_one_public_mcp(self) -> None:
        config = json.loads((ROOT / "plugins" / "commons-grok-cloud" / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(config["mcpServers"]["commons"]["url"], PUBLIC_MCP)
        self.assertEqual(config["mcpServers"]["commons"]["type"], "http")

    def test_does_not_copy_vendor_kits(self) -> None:
        blob = json.dumps(self.market)
        for silo in fold.SILOED:
            self.assertNotIn(silo, blob)

    def test_cites_landed_fold_door(self) -> None:
        card = (ROOT / "ground" / "WIRE_SUPER_MCP.md").read_text(encoding="utf-8")
        self.assertIn("integrations/commons_network_plugin", card)
        self.assertIn("plugins/commons-grok-cloud", card)
        self.assertIn(PUBLIC_MCP, card)
        self.assertTrue((ROOT / "wire.html").is_file())
        self.assertTrue((ROOT / "p" / "wire-super-mcp-fold-20260902-01.md").is_file())

    def test_self_test(self) -> None:
        receipt = fold.self_test()
        self.assertEqual(receipt["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
