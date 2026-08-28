import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "plugins" / "commons-grok-cloud"
MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"


class GrokCloudPluginTests(unittest.TestCase):
    def test_marketplace_installs_exact_plugin(self):
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["name"], "commons")
        row = market["plugins"][0]
        self.assertEqual(row["name"], "commons-grok-cloud")
        self.assertEqual(row["source"]["path"], "./plugins/commons-grok-cloud")
        self.assertEqual(row["policy"]["installation"], "AVAILABLE")

    def test_manifest_and_companion_files_are_complete(self):
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertTrue((PLUGIN / "skills" / "commons-grok-cloud" / "SKILL.md").is_file())
        self.assertTrue((PLUGIN / "scripts" / "server.mjs").is_file())
        self.assertNotIn("[TODO:", json.dumps(manifest))

    def test_plugin_composes_shared_mcp_and_cloud_bridge(self):
        config = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
        servers = config["mcpServers"]
        self.assertEqual(servers["commons"]["url"], MCP_URL)
        self.assertEqual(servers["commons"]["type"], "http")
        self.assertEqual(servers["commons-grok-cloud"]["command"], "node")
        self.assertIn("--stdio", servers["commons-grok-cloud"]["args"])

    def test_skill_requires_real_browser_url_and_dedup(self):
        text = (PLUGIN / "skills" / "commons-grok-cloud" / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "control-browser",
            "C0BRGMDQB6G",
            "grok.com/c/...",
            "Do not mint a parallel queue",
            "verify_durability",
            "Gemini remains a distinct client",
        ):
            self.assertIn(marker, text)

    def test_carrier_catalog_keeps_mcp_clients_and_adds_grok_surface(self):
        catalog = json.loads((ROOT / "carriers" / "catalog.json").read_text(encoding="utf-8"))
        carrier_ids = [row["id"] for row in catalog["carriers"]]
        self.assertEqual(carrier_ids[:4], ["gemini-spark", "cursor-grok", "grokcom-revenue", "chatgpt-codex"])
        self.assertIn("grokcom-revenue", carrier_ids)
        self.assertIn("route_grokcom_revenue_work", catalog["shared_tools"])
        self.assertEqual(catalog["plugins"]["grok_cloud"], "plugins/commons-grok-cloud")
        card = json.loads((ROOT / "carriers" / "grokcom-revenue.json").read_text(encoding="utf-8"))
        self.assertEqual(card["mcp_url"], MCP_URL)
        self.assertEqual(card["tool"], "route_grokcom_revenue_work")
        self.assertIn("grok.com/c/...", card["cloud_executor"]["receipt"])
        self.assertIn("build_grok_artifact", card["cloud_executor"]["helper_tools"])

    def test_node_server_syntax_and_self_test(self):
        server = PLUGIN / "scripts" / "server.mjs"
        for command in (["node", "--check", str(server)], ["node", str(server), "--self-test"]):
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
