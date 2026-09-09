#!/usr/bin/env python3
"""Shared super MCP catalog leftover — fold, do not remint."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import host.super_mcp as sm


ROOT = Path(__file__).resolve().parent
PUBLIC_MCP = "https://commons-spark-mcp.vercel.app/mcp"


class SuperMcpCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = sm.catalog()

    def test_validate_ok(self) -> None:
        receipt = sm.validate(self.catalog)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["url"], PUBLIC_MCP)
        self.assertEqual(receipt["cite"], "wire-super-mcp-fold-20260902-01")
        self.assertEqual(receipt["tools"], 17)

    def test_does_not_remint_live_mcp(self) -> None:
        trio = self.catalog["trio"]["super_mcp"]
        self.assertEqual(trio["url"], PUBLIC_MCP)
        self.assertEqual(trio["adapter"], "api/mcp.py")
        self.assertIn("not a second server", trio["note"])
        self.assertTrue((ROOT / "api" / "mcp.py").is_file())
        self.assertTrue((ROOT / "wire.html").is_file())
        self.assertTrue((ROOT / "p" / "wire-super-mcp-fold-20260902-01.md").is_file())

    def test_folds_live_roads(self) -> None:
        fold = self.catalog["fold_do_not_remint"]
        self.assertEqual(fold["public_mcp"]["url"], PUBLIC_MCP)
        self.assertEqual(fold["gemini_carriers"]["catalog"], "carriers/catalog.json")
        self.assertTrue((ROOT / fold["hall_pass"]["skill"]).is_file())
        self.assertEqual(fold["tools_manual_job"]["door"], "tools.html")
        self.assertEqual(fold["tools_manual_job"]["inbox"], "TOOLS")

    def test_public_tools_match_carrier_catalog(self) -> None:
        carriers = json.loads((ROOT / "carriers" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(self.catalog["tools"]["public_mcp"], carriers["shared_tools"])
        self.assertIn("fire_action", self.catalog["tools"]["public_mcp"])
        self.assertIn("discover_commons_capabilities", self.catalog["tools"]["public_mcp"])
        self.assertEqual(self.catalog["tools"]["local_stdio"], ["hands"])
        for target in ("files", "slack", "browser", "shell"):
            self.assertIn(target, self.catalog["tools"]["hands_targets"])

    def test_who_connects_has_thin_and_desktop_peers(self) -> None:
        ids = {row["id"] for row in sm.connectors(self.catalog)}
        for needed in ("claude", "chatgpt-codex", "gemini-spark", "cursor-grok", "slack", "git"):
            self.assertIn(needed, ids)
        for row in sm.connectors(self.catalog):
            self.assertTrue(row["connect"])
            card = ROOT / row["card"]
            self.assertTrue(card.is_file(), row["card"])

    def test_thin_harness_routes(self) -> None:
        for need in sm.RESIDUALS:
            row = sm.route(need, self.catalog)
            self.assertEqual(row["need"], need)
            self.assertEqual(row["mcp"], PUBLIC_MCP)
            self.assertEqual(row["call_first"], "discover_commons_capabilities")
            self.assertTrue(row["preferred"])
            self.assertTrue(row["thin"])
            self.assertTrue(row["local_when_stdio"])

    def test_browser_hall_pass_is_no_login(self) -> None:
        row = sm.route("browser", self.catalog)
        self.assertIn("google.com", row["thin"])
        self.assertIn("no login", row["thin"])
        self.assertIn("hall-pass", row["preferred"])

    def test_stripe_does_not_invent_urls(self) -> None:
        row = sm.route("stripe", self.catalog)
        self.assertIn("payment-capability.html", row["preferred"])
        self.assertIn("Do not invent", row["do_not"])

    def test_rejects_siloed_packs(self) -> None:
        rejected = self.catalog["siloed_packs_rejected"]
        for name in sm.SILOED:
            self.assertIn(name, rejected)
        blob = json.dumps(self.catalog)
        self.assertNotIn("api-key", blob.lower())
        self.assertNotIn("oauth", blob.lower())

    def test_open_door(self) -> None:
        self.assertTrue(self.catalog["open_door"])
        self.assertEqual(self.catalog["authentication"], "none")

    def test_door_cites_catalog_and_live_url(self) -> None:
        door = (ROOT / "super-mcp.html").read_text(encoding="utf-8")
        self.assertIn(PUBLIC_MCP, door)
        self.assertIn("super-mcp/catalog.json", door)
        self.assertIn("wire.html", door)
        self.assertIn("discover_commons_capabilities", door)

    def test_self_test(self) -> None:
        receipt = sm.self_test()
        self.assertEqual(receipt["self_test"], "PASS")

    def test_bad_need(self) -> None:
        with self.assertRaises(sm.SuperMcpError):
            sm.route("sales")

    def test_token_file_passes_open_door_guard(self) -> None:
        import open_door_guard as guard

        path = ROOT / "ground" / "tokens" / "super-mcp.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("never a gate", text)
        self.assertNotIn("permission gate", text)
        lines = [
            guard.AddedLine(path.as_posix(), n, line)
            for n, line in enumerate(text.splitlines(), 1)
        ]
        self.assertEqual(guard.scan_added(lines), [])


if __name__ == "__main__":
    unittest.main()
