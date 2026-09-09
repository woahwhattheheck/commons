#!/usr/bin/env python3
"""Integrations cwd compose for the Slack CLI leftover. Do not remint the peer."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "integrations" / "slack_custom_tools"
sys.path.insert(0, str(ROOT / "host"))

import slack_custom_tools_app as app  # noqa: E402
import slack_custom_tools_cli_project as peer  # noqa: E402


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class IntegrationsCliComposeTest(unittest.TestCase):
    def test_project_has_hooks_and_drive_function(self) -> None:
        manifest = json.loads((PROJECT / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("drive_tagged_service", manifest["functions"])
        hooks = json.loads((PROJECT / ".slack" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(hooks["hooks"]["start"], "python3 app.py")
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "hooks" / "get_manifest.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        printed = json.loads(proc.stdout)
        self.assertEqual(
            printed["functions"]["drive_tagged_service"]["title"],
            manifest["functions"]["drive_tagged_service"]["title"],
        )
        source = (PROJECT / "app.py").read_text(encoding="utf-8")
        self.assertIn("from slack_custom_tools_app import register", source)
        self.assertIn("#needs-bryce", source)
        self.assertNotIn("xoxb-", source)

    def test_build_app_delegates_to_host_register(self) -> None:
        sys.path.insert(0, str(PROJECT))
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

    def test_peer_leftover_not_reminted(self) -> None:
        receipt = ROOT / "p" / "cursor-slack-custom-tools-cli-project-20260902-01.md"
        self.assertTrue(receipt.is_file())
        body = receipt.read_text(encoding="utf-8")
        self.assertIn("host/slack_custom_tools_cli", body)
        self.assertIn("#needs-bryce", body)
        self.assertNotIn("integrations/slack_custom_tools/", body)
        self.assertEqual(peer.PROJECT_DIR, ROOT / "host" / "slack_custom_tools_cli")
        self.assertTrue((ROOT / "host" / "slack_custom_tools_cli" / "start.py").is_file())
        install_receipt = ROOT / "p" / "cursor-slack-service-tools-install-20260902-01.md"
        self.assertTrue(git_blob_sha(install_receipt.read_bytes()).startswith("8fcc3d36"))

    def test_facebook_still_queues_needs_bryce(self) -> None:
        out = app.drive("facebook", "post the drop tonight", sessions={})
        self.assertEqual(out["state"], "NEEDS_OWNER_SIGNIN")
        self.assertEqual(out["channel_id"], "C0BRX6EV739")
        card = (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_CLI_PROJECT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("host/slack_custom_tools_cli", card)
        self.assertIn("integrations/slack_custom_tools", card)
        self.assertIn("65dc46fa5", card)


if __name__ == "__main__":
    unittest.main()
