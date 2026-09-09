#!/usr/bin/env python3
"""GitHub is already signed in. A failed call is not a missing login."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import github_already_logged_in as gal  # noqa: E402


class ClassifyTests(unittest.TestCase):
    def test_get_me_login_is_auth_ok(self) -> None:
        out = gal.classify(login="woahwhattheheck", tool="get_me")
        self.assertEqual(out["auth"], "present")
        self.assertEqual(out["cause"], "auth_ok")
        self.assertFalse(out["park"])
        self.assertFalse(out["needs_bryce"])
        self.assertFalse(out["github_login_ask"])
        self.assertTrue(out["keep_shipping"])
        self.assertEqual(out["peer_login"], "woahwhattheheck")

    def test_rate_limit_is_not_missing_login(self) -> None:
        out = gal.classify(status_code=403, message="API rate limit exceeded")
        self.assertEqual(out["cause"], "rate_limit")
        self.assertFalse(out["park"])
        self.assertFalse(out["github_login_ask"])

    def test_missing_path_is_not_missing_login(self) -> None:
        out = gal.classify(
            status_code=404,
            message="Failed to get file contents. The path does not point to a file",
        )
        self.assertEqual(out["cause"], "path")
        self.assertFalse(out["park"])

    def test_https_git_prompt_is_not_missing_mcp_login(self) -> None:
        out = gal.classify(
            message="could not read Username for 'https://github.com'"
        )
        self.assertEqual(out["cause"], "https_git_not_mcp")
        self.assertIn("push_files", out["next"])
        self.assertFalse(out["github_login_ask"])

    def test_actions_write_403_is_scope(self) -> None:
        out = gal.classify(status_code=403, message="Resource not accessible by integration")
        self.assertEqual(out["cause"], "scope")
        self.assertFalse(out["park"])
        self.assertTrue(out["keep_shipping"])

    def test_false_missing_login_freeze(self) -> None:
        out = gal.classify(message="no perms, reconnect GitHub, not logged in to github")
        self.assertEqual(out["cause"], "false_missing_login")
        self.assertFalse(out["park"])
        self.assertFalse(out["github_login_ask"])

    def test_slack_cli_is_not_github(self) -> None:
        out = gal.slack_cli_is_not_github(slack_cli_logged_in=False)
        self.assertEqual(out["auth_github"], "present")
        self.assertFalse(out["park"])
        self.assertFalse(out["needs_bryce"])
        self.assertFalse(out["github_login_ask"])

    def test_three_three_seven_is_not_a_rule(self) -> None:
        out = gal.three_three_seven_is_not_a_rule()
        self.assertFalse(out["rule"])
        self.assertTrue(out["keep_shipping"])
        self.assertFalse(out["park"])

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "github_already_logged_in.py"),
                "--login",
                "woahwhattheheck",
                "--tool",
                "get_me",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["cause"], "auth_ok")
        self.assertFalse(payload["github_login_ask"])


class OverlayRuleTests(unittest.TestCase):
    def test_cursor_rule_forbids_login_ask(self) -> None:
        text = (
            ROOT / ".cursor" / "rules" / "github-already-logged-in.mdc"
        ).read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", text)
        self.assertIn("woahwhattheheck", text)
        self.assertIn("Do not open another GitHub login ask", text)
        self.assertIn("rate-limit", text)
        self.assertIn("CLAUDE.md", text)


if __name__ == "__main__":
    unittest.main()
