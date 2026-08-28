#!/usr/bin/env python3
"""Host pack, secret injection, health, and canary for grok_slack."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from integrations.grok_slack.canary import run as run_canary
from integrations.grok_slack import bridge


class GrokSlackHostTests(unittest.TestCase):
    def test_canary_passes_offline(self) -> None:
        report = run_canary()
        self.assertTrue(report["ok"], report.get("failed"))
        encoded = json.dumps(report)
        self.assertNotRegex(encoded, r"(?:xox[baprs]|xapp)-[A-Za-z0-9-]{8,}")
        self.assertEqual(report["final_delivery_owner"], "grok_slack_bridge")
        self.assertEqual(report["runtime_state"], "CODE_LANDED_RUNTIME_UNCONFIGURED")

    def test_load_runtime_env_does_not_override_or_print(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            path.write_text("SLACK_BOT_TOKEN=xoxb-file-value-xxxxx\nKEEP=from-file\n", encoding="utf-8")
            env = {"SLACK_BOT_TOKEN": "already", "KEEP": ""}
            loaded = bridge.load_runtime_env(env, files=[path])
            self.assertEqual(env["SLACK_BOT_TOKEN"], "already")
            self.assertEqual(env["KEEP"], "from-file")
            self.assertNotIn("xoxb-file-value-xxxxx", json.dumps(loaded))
            self.assertFalse(loaded["secrets_printed"])

    def test_scan_secrets_in_config_reports_names_not_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("leak xoxb-not-a-real-token-value\n", encoding="utf-8")
            scan = bridge.scan_secrets_in_config(root)
            self.assertTrue(scan["secrets_in_config"])
            self.assertEqual(scan["files"], ["README.md"])
            self.assertNotIn("xoxb-not-a-real-token-value", json.dumps(scan))

    def test_health_http_and_health_command_omit_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = {"live": True, "state": "SERVING", "secret": "present"}
            server = bridge.HealthServer("127.0.0.1:0", lambda: snapshot)
            server.start()
            self.addCleanup(server.stop)
            live = bridge.probe_health_url(server.url)
            self.assertTrue(live["live"])
            args = type("Args", (), {
                "state_db": Path(directory) / "db.sqlite3",
                "probe": server.url,
                "health_bind": "127.0.0.1:0",
            })()
            code, report = bridge.health(args, env={"SLACK_BOT_TOKEN": "BOT_TOKEN_SHOULD_NOT_LEAK", "SLACK_APP_TOKEN": "APP_TOKEN_SHOULD_NOT_LEAK"}, root=bridge.integration_root())
            encoded = json.dumps(report)
            self.assertNotIn("BOT_TOKEN_SHOULD_NOT_LEAK", encoded)
            self.assertNotIn("APP_TOKEN_SHOULD_NOT_LEAK", encoded)
            self.assertEqual(report["slack_bot_token"], "present")
            self.assertTrue(report.get("live"))
            self.assertEqual(code, 0)

    def test_host_files_exist_without_token_prefixes(self) -> None:
        root = bridge.integration_root()
        pack = bridge.host_pack_presence(root)
        self.assertTrue(all(pack.values()), pack)
        for name in pack:
            text = (root / name).read_text(encoding="utf-8")
            self.assertIsNone(bridge.TOKEN_VALUE_RE.search(text), name)
        example = (root / "env.example").read_text(encoding="utf-8")
        self.assertIn("SLACK_BOT_TOKEN=\n", example.replace("\r\n", "\n"))
        self.assertIn("SLACK_APP_TOKEN=\n", example.replace("\r\n", "\n"))

    def test_tests_yml_watches_integrations(self) -> None:
        text = Path("tests.yml" if Path("tests.yml").is_file() else ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("integrations/**", text)

    def test_doctor_marks_secrets_in_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bridge.py").write_text("xoxb-should-fail-scan-here\n", encoding="utf-8")
            github = type("G", (), {"current_main_sha": lambda self: "a" * 40, "read_path": lambda self, p, s: b"{}"})()
            mcp = type("M", (), {
                "url": "https://commons-spark-mcp.vercel.app/mcp",
                "initialize": lambda self: {},
                "tools_list": lambda self: ["route_grokcom_revenue_work", "fire_action"],
            })()
            args = type("Args", (), {"state_db": Path(directory) / "db.sqlite3", "mcp_url": mcp.url})()
            _code, report = bridge.doctor(
                args,
                env={"SLACK_BOT_TOKEN": "present-token", "SLACK_APP_TOKEN": "present-token"},
                mcp=mcp,
                github=github,
                root=root,
            )
            self.assertTrue(report["secrets_in_config"])
            self.assertFalse(report["ready"])
            self.assertNotIn("xoxb-should-fail-scan-here", json.dumps(report))
            self.assertNotIn("present-token", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
