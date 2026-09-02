#!/usr/bin/env python3
"""Slack CLI project leftover after custom-tools install. Login stays #needs-bryce."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_custom_tools_app as app  # noqa: E402
import slack_custom_tools_cli_project as cli  # noqa: E402
import slack_custom_tools_install as inst  # noqa: E402


PEER_PATHS = (
    "host/slack_custom_tools_install.py",
    "host/slack_custom_tools_app.py",
    "host/slack_custom_tools_manifest.json",
    "host/slack_service_tag_worker.py",
    "integrations/slack_service_tags/app_manifest.yaml",
    "p/cursor-slack-custom-tools-install-20260902-01.md",
    "p/cursor-slack-service-tools-install-20260902-01.md",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class SlackCliProjectTest(unittest.TestCase):
    def test_write_project_has_hooks_and_drive_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "integrations" / "slack_custom_tools"
            cli.write_project(dest)
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("drive_tagged_service", manifest["functions"])
            hooks = json.loads((dest / ".slack" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(hooks["hooks"]["start"], "python3 app.py")
            self.assertEqual(hooks["hooks"]["get-manifest"], "python3 hooks/get_manifest.py")
            slack_json = json.loads((dest / "slack.json").read_text(encoding="utf-8"))
            self.assertEqual(slack_json, hooks)
            proc = subprocess.run(
                [sys.executable, str(dest / "hooks" / "get_manifest.py")],
                check=True,
                capture_output=True,
                text=True,
            )
            printed = json.loads(proc.stdout)
            self.assertEqual(
                printed["functions"]["drive_tagged_service"]["title"],
                manifest["functions"]["drive_tagged_service"]["title"],
            )
            source = (dest / "app.py").read_text(encoding="utf-8")
            self.assertIn("from slack_custom_tools_app import register", source)
            self.assertIn("#needs-bryce", source)
            self.assertNotIn("xoxb-", source)
            self.assertNotIn("xapp-", source)

    def test_checked_in_project_matches_writer(self) -> None:
        dest = cli.PROJECT_DIR
        self.assertTrue(cli.project_written())
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "proj"
            cli.write_project(other)
            for rel in (
                "manifest.json",
                "app.py",
                "slack.json",
                "requirements.txt",
                "README.md",
                ".gitignore",
                ".slackignore",
                ".slack/hooks.json",
                "hooks/get_hooks.py",
                "hooks/get_manifest.py",
            ):
                self.assertEqual(
                    (dest / rel).read_text(encoding="utf-8"),
                    (other / rel).read_text(encoding="utf-8"),
                    rel,
                )

    def test_status_without_login_stays_needs_bryce(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            row = cli.status(home=str(home), path_env="", root=ROOT)
        self.assertTrue(row["project_written"])
        self.assertTrue(row["needs_owner_signin"])
        self.assertEqual(row["signin_channel"], "#needs-bryce")
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")
        self.assertIs(row["commons_admission"], False)
        self.assertEqual(row["peer_not_reminted"], ["0e6ad49f", "8fcc3d36"])
        self.assertEqual(row["manifest_callback_id"], "drive_tagged_service")
        self.assertEqual(row["slash_command"], "/svctool")
        self.assertIn("integrations/slack_custom_tools", row["project_rel"])
        self.assertEqual(row["slack_run_argv"][-1], "--org-workspace-grant=all")

    def test_status_detects_cli_but_still_queues_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / ".slack" / "bin"
            bindir.mkdir(parents=True)
            slack = bindir / "slack"
            slack.write_text("#!/bin/sh\necho not-logged-in\n", encoding="utf-8")
            slack.chmod(slack.stat().st_mode | stat.S_IXUSR)

            def run(argv, **kwargs):  # noqa: ANN001
                class Proc:
                    stdout = "You are not logged in to any team.\n"
                    stderr = ""
                    returncode = 0

                return Proc()

            row = cli.status(home=tmp, path_env="", run=run, root=ROOT)
        self.assertTrue(row["installed"])
        self.assertFalse(row["logged_in"])
        self.assertTrue(row["needs_owner_signin"])
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")

    def test_build_app_delegates_to_host_register(self) -> None:
        sys.path.insert(0, str(cli.PROJECT_DIR))
        import app as project_app  # noqa: E402

        class FakeApp:
            def __init__(self, process_before_response: bool = False) -> None:
                self.process_before_response = process_before_response
                self.functions: list[str] = []
                self.events: list[str] = []
                self.commands: list[str] = []

            def function(self, name: str):
                def deco(fn):
                    self.functions.append(name)
                    return fn

                return deco

            def event(self, name: str):
                def deco(fn):
                    self.events.append(name)
                    return fn

                return deco

            def command(self, name: str):
                def deco(fn):
                    self.commands.append(name)
                    return fn

                return deco

        built = project_app.build_app(FakeApp)
        self.assertIn("drive_tagged_service", built.functions)
        self.assertIn("/svctool", built.commands)
        self.assertIn("app_mention", built.events)

    def test_peer_readback_not_reminted(self) -> None:
        receipt = ROOT / "p" / "cursor-slack-service-tools-install-20260902-01.md"
        self.assertTrue(git_blob_sha(receipt.read_bytes()).startswith("8fcc3d36"))
        for rel in PEER_PATHS:
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
        install = (ROOT / "host" / "slack_custom_tools_install.py").read_text(encoding="utf-8")
        self.assertIn("def detect_cli", install)
        self.assertIn("drive_tagged_service", install)
        self.assertNotIn("PROJECT_REL", install)
        worker = (ROOT / "host" / "slack_service_tag_worker.py").read_text(encoding="utf-8")
        self.assertIn("service-tag-job", worker)
        self.assertEqual(inst.CALLBACK_ID, "drive_tagged_service")

    def test_facebook_still_queues_needs_bryce_through_project_cwd(self) -> None:
        out = app.drive("facebook", "post the drop tonight", sessions={})
        self.assertEqual(out["state"], "NEEDS_OWNER_SIGNIN")
        self.assertEqual(out["channel_id"], "C0BRX6EV739")
        self.assertIn("https://developers.facebook.com/apps/", out["needs_bryce_text"])
        card = (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_CLI_PROJECT.md").read_text(encoding="utf-8")
        self.assertIn("#needs-bryce", card)
        self.assertIn("0e6ad49f", card)
        self.assertIn("8fcc3d36", card)
        self.assertNotIn("PLACEHOLDER_WILL", card)


if __name__ == "__main__":
    unittest.main()
