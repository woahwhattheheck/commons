#!/usr/bin/env python3
"""Slack CLI project leftover: get-manifest + start, no steal of the peer worker."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_custom_tools_cli_project as proj  # noqa: E402
import slack_custom_tools_install as inst  # noqa: E402


def _load_start():
    path = ROOT / "host" / "slack_custom_tools_cli" / "start.py"
    spec = importlib.util.spec_from_file_location("slack_custom_tools_cli_start", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CliProjectLayoutTest(unittest.TestCase):
    def test_hooks_and_gitignore(self) -> None:
        hooks = json.loads(
            (ROOT / "host" / "slack_custom_tools_cli" / ".slack" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(hooks["hooks"]["get-manifest"], "python3 get_manifest.py")
        self.assertEqual(hooks["hooks"]["start"], "python3 start.py")
        ignore = (
            ROOT / "host" / "slack_custom_tools_cli" / ".slack" / ".gitignore"
        ).read_text(encoding="utf-8")
        self.assertIn("apps.json", ignore)
        self.assertIn("credentials.json", ignore)

    def test_get_manifest_prints_drive_tagged_service(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "slack_custom_tools_cli" / "get_manifest.py")],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT / "host" / "slack_custom_tools_cli"),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("drive_tagged_service", payload["functions"])
        self.assertEqual(
            payload["display_information"]["name"], "Commons Service Tools"
        )
        self.assertNotIn("xoxb-", proc.stdout)
        self.assertNotIn("xapp-", proc.stdout)

    def test_start_without_tokens_does_not_echo_secrets(self) -> None:
        start = _load_start()
        buf = io.StringIO()
        env = {
            "SLACK_BOT_TOKEN": "xoxb-TEST-TOKEN-NOT-FOR-GIT",
            "SLACK_APP_TOKEN": "",
        }
        with contextlib.redirect_stderr(buf):
            code = start.start(environ=env)
            missing = start.start(environ={})
        self.assertEqual(code, 2)
        self.assertEqual(missing, 2)
        text = buf.getvalue()
        self.assertIn("NEEDS_OWNER_SIGNIN", text)
        self.assertNotIn("xoxb-TEST-TOKEN-NOT-FOR-GIT", text)

    def test_argv_wraps_manifest_create_install(self) -> None:
        self.assertEqual(
            proj.manifest_validate_argv("/tmp/slack"),
            ["/tmp/slack", "manifest", "validate", "--source", "local"],
        )
        self.assertEqual(
            proj.app_install_argv("/tmp/slack"),
            ["/tmp/slack", "app", "install", "--org-workspace-grant=all"],
        )
        self.assertEqual(
            proj.run_argv("/tmp/slack"),
            ["/tmp/slack", "run", "--org-workspace-grant=all"],
        )
        chain = proj.after_login_argv("/tmp/slack")
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[1][1], "app")

    def test_write_project_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cli"
            dest.mkdir()
            (dest / "get_manifest.py").write_text("# placeholder\n", encoding="utf-8")
            written = proj.write_project(dest)
            self.assertTrue((written / ".slack" / "hooks.json").is_file())
            self.assertTrue((written / "manifest.json").is_file())
            disk = json.loads((written / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("drive_tagged_service", disk["functions"])
            self.assertTrue(proj.project_ready(dest))

    def test_status_queues_needs_bryce_when_logged_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / ".slack" / "bin"
            bindir.mkdir(parents=True)
            cli = bindir / "slack"
            cli.write_text("#!/bin/sh\necho You are not logged in to any Slack accounts\n", encoding="utf-8")
            cli.chmod(cli.stat().st_mode | stat.S_IXUSR)
            row = proj.status(home=tmp)
        self.assertEqual(row["id"], "cursor-slack-custom-tools-cli-project-20260902-01")
        self.assertTrue(row["project_ready"])
        self.assertTrue(row["needs_owner_signin"])
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")
        self.assertIs(row["commons_admission"], False)
        self.assertEqual(row["wraps"], "apps.manifest.create")
        self.assertIn("host/slack_service_tag_worker.py", row["not_stolen"])

    def test_peer_worker_untouched(self) -> None:
        worker = (ROOT / "host" / "slack_service_tag_worker.py").read_text(encoding="utf-8")
        self.assertIn("Slack-side custom-tool worker", worker)
        self.assertTrue((ROOT / "host" / "slack_custom_tools_install.py").is_file())
        self.assertTrue((ROOT / "p" / "cursor-slack-custom-tools-install-20260902-01.md").is_file())
        card = (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("slack_custom_tools_cli", card)
        self.assertNotIn("PLACEHOLDER_WILL", card)

    def test_original_install_status_still_points_at_needs_bryce(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            row = inst.status(home=tmp, path_env="")
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")


if __name__ == "__main__":
    unittest.main()
