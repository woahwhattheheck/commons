#!/usr/bin/env python3
"""Fresh Slack CLI #needs-bryce challenge leftover. Does not remint the project."""
from __future__ import annotations

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
import slack_custom_tools_cli_ticket as ticket  # noqa: E402


class SlackCliChallengeTest(unittest.TestCase):
    def test_status_does_not_remint_project_or_peer_ticket(self) -> None:
        row = ticket.status()
        self.assertEqual(row["id"], "cursor-slack-custom-tools-cli-challenge-20260902-01")
        self.assertEqual(row["project_receipt"], "cursor-slack-custom-tools-cli-project-20260902-01")
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")
        self.assertEqual(row["this_ticket_ts"], "1788325362.867019")
        self.assertEqual(row["peer_ticket_ts"], "1788321773.338029")
        self.assertEqual(row["peer_ticket"], "do_not_consume")
        self.assertIs(row["commons_admission"], False)
        self.assertIs(row["gate"], False)
        self.assertIn("8fcc3d36", row["do_not_remint"])
        self.assertIn("0e6ad49f", row["do_not_remint"])

    def test_emit_login_ticket_formats_needs_bryce(self) -> None:
        sample = (
            "Run the following slash command from any Slack channel\n"
            "   /slackauthticket eyJ0eXAiOiJKV1QiLCJh.cli-challenge\n"
        )

        def run(argv, **kwargs):  # noqa: ANN001
            return subprocess.CompletedProcess(argv, 0, stdout=sample, stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / ".slack" / "bin"
            bindir.mkdir(parents=True)
            cli = bindir / "slack"
            cli.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
            cli.chmod(cli.stat().st_mode | stat.S_IXUSR)
            out = ticket.emit_login_ticket(cli=str(cli), run=run)
        self.assertTrue(out["ok"])
        self.assertIn(
            "/slackauthticket eyJ0eXAiOiJKV1QiLCJh.cli-challenge",
            out["needs_bryce_text"],
        )
        self.assertIn("C0BRX6EV739", out["needs_bryce_text"])
        self.assertIn("bc-ebe2e1f5", out["needs_bryce_text"])
        self.assertEqual(out["peer_ticket"], "do_not_consume")
        self.assertFalse(out["copy_secrets"])
        self.assertIs(out["commons_admission"], False)

    def test_slack_json_is_additive_official_hooks(self) -> None:
        slack = json.loads(
            (ROOT / "host" / "slack_custom_tools_cli" / "slack.json").read_text(
                encoding="utf-8"
            )
        )
        hooks = json.loads(
            (ROOT / "host" / "slack_custom_tools_cli" / ".slack" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(slack["hooks"]["get-manifest"], hooks["hooks"]["get-manifest"])
        self.assertEqual(slack["hooks"]["start"], hooks["hooks"]["start"])
        self.assertEqual(
            slack["hooks"]["get-hooks"],
            "python3 -m slack_cli_hooks.hooks.get_hooks",
        )
        self.assertIs(slack["commons_admission"], False)

    def test_does_not_remint_landed_project_or_readback(self) -> None:
        receipt = (
            ROOT / "p" / "cursor-slack-custom-tools-cli-project-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn("id: cursor-slack-custom-tools-cli-project-20260902-01", receipt)
        self.assertTrue((ROOT / "host" / "slack_custom_tools_cli_project.py").is_file())
        self.assertTrue((ROOT / "host" / "slack_custom_tools_cli" / "start.py").is_file())
        self.assertTrue(proj.project_ready())
        spec = json.loads(
            (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_CLI_CHALLENGE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(spec["id"], "cursor-slack-custom-tools-cli-challenge-20260902-01")
        self.assertEqual(spec["this_ticket_ts"], "1788325362.867019")
        self.assertEqual(spec["peer_ticket"], "do_not_consume")
        card = (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_CLI_CHALLENGE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("1788325362.867019", card)
        self.assertIn("do not consume", card.lower())


if __name__ == "__main__":
    unittest.main()
