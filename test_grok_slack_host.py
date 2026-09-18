#!/usr/bin/env python3
"""Host pack, secret injection, health, and canary for grok_slack."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

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

    def test_dockerfile_copies_named_files_not_env(self) -> None:
        text = (bridge.integration_root() / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotIn("COPY integrations/grok_slack /opt/commons/integrations/grok_slack", text)
        self.assertIn("integrations/grok_slack/bridge.py", text)
        self.assertIn("integrations/grok_slack/handoff.py", text)
        self.assertIn("integrations/grokcom_revenue/orchestrator.py", text)
        self.assertNotIn(".env.local", text)
        self.assertIsNone(bridge.TOKEN_VALUE_RE.search(text))

    def test_compose_optional_env_file_without_tokens(self) -> None:
        text = (bridge.integration_root() / "compose.yml").read_text(encoding="utf-8")
        self.assertIn("env_file:", text)
        self.assertIn(".env.local", text)
        self.assertIn("required: false", text)
        self.assertIsNone(bridge.TOKEN_VALUE_RE.search(text))

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

    def test_github_readback_falls_back_without_token(self) -> None:
        def opener(request: object, timeout: float | None = None) -> object:
            del timeout
            url = str(getattr(request, "full_url", ""))
            raise HTTPError(url, 403, "rate limit", hdrs=None, fp=io.BytesIO(b""))

        reader = bridge.GitHubReadback(
            opener=opener,
            token="",
            public_sha=lambda: "b" * 40,
            public_read=lambda path, sha: b'{"ok":true}',
        )
        sha = reader.current_main_sha()
        self.assertEqual(sha, "b" * 40)
        self.assertEqual(reader.road, "git_ls_remote")
        blob = reader.read_path("carriers/catalog.json", sha)
        self.assertEqual(blob, b'{"ok":true}')
        self.assertEqual(reader.road, "sha_pinned_raw")

    def test_ls_remote_public_main_sha(self) -> None:
        sha = bridge.GitHubReadback(token="")._ls_remote_main()
        self.assertRegex(sha, r"^[0-9a-f]{40}$")

    def test_table_proof_is_redacted_and_callable(self) -> None:
        bot = "xoxb-table-proof-bot-aaaaaaaa"
        app = "xapp-table-proof-app-bbbbbbbb"
        calls: list[str] = []

        class _Resp:
            def __init__(self, payload: dict) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def opener(request: object, timeout: float | None = None) -> object:
            del timeout
            url = str(getattr(request, "full_url", ""))
            calls.append(url.rsplit("/", 1)[-1])
            auth = ""
            headers = getattr(request, "headers", {}) or {}
            if hasattr(headers, "items"):
                for key, value in headers.items():
                    if str(key).lower() == "authorization":
                        auth = str(value)
            self.assertTrue(auth.startswith("Bearer "))
            self.assertIn(bot, auth)
            if url.endswith("auth.test"):
                return _Resp({"ok": True, "team_id": "T123", "user_id": "U123"})
            if url.endswith("conversations.history"):
                return _Resp({"ok": True, "messages": [{"ts": "1.2", "text": "hello table"}]})
            if url.endswith("chat.postMessage"):
                return _Resp({"ok": True, "ts": "3.4"})
            raise AssertionError(url)

        args = type("Args", (), {
            "state_db": Path(tempfile.gettempdir()) / "unused-grok-slack-proof.sqlite3",
            "probe": "",
            "health_bind": "127.0.0.1:8788",
            "post_receipt": True,
        })()
        with tempfile.TemporaryDirectory() as directory:
            args.state_db = Path(directory) / "db.sqlite3"
            code, report = bridge.table_proof(
                args,
                env={"SLACK_BOT_TOKEN": bot, "SLACK_APP_TOKEN": app},
                opener=opener,
                post_receipt=True,
            )
        encoded = json.dumps(report)
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertTrue(report["read_only_history"])
        self.assertTrue(report["receipt_posted"])
        self.assertEqual(report["channel"], "C0BRGMDQB6G")
        self.assertEqual(report["slack_app_id"], "A0BTJMFPTT6")
        self.assertTrue(report["gemini_isolated"])
        self.assertEqual(report["gemini_handoff_bind"], "127.0.0.1:8780")
        self.assertNotIn(bot, encoded)
        self.assertNotIn(app, encoded)
        self.assertEqual(calls, ["auth.test", "conversations.history", "chat.postMessage"])
        self.assertIn("table-proof", Path("integrations/grok_slack/bridge.py").read_text(encoding="utf-8"))



if __name__ == "__main__":
    unittest.main()
