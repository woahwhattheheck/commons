#!/usr/bin/env python3
"""GitHub is logged in. Slack CLI leftover is not a freeze."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import harness_already_logged_in as hal  # noqa: E402


class HarnessAlreadyLoggedInTest(unittest.TestCase):
    def test_card_is_not_a_commons_gate(self) -> None:
        card = hal.load_card()
        self.assertEqual(card["id"], "cursor-ack-github-logged-in-20260902-01")
        self.assertEqual(card["source_slack_ts"], "1788325660.929309")
        self.assertEqual(card["github"]["login"], "woahwhattheheck")
        self.assertIs(card["gate"], False)
        self.assertIs(card["commons_admission"], False)
        self.assertIs(card["github"]["ask_github_login"], False)
        self.assertIs(card["github"]["park"], False)
        self.assertEqual(card["slack_cli_svctool"]["status"], "LEFTOVER_NOT_FREEZE")
        self.assertIs(card["slack_cli_svctool"]["freeze"], False)
        self.assertIs(card["slack_cli_svctool"]["post_slackauthticket"], False)
        self.assertIs(card["fire_337"], False)
        self.assertEqual(card["keep_shipping_roads"], ["slack_mcp", "github_mcp"])

    def test_github_identity_logged_in(self) -> None:
        row = hal.github_identity()
        self.assertEqual(row["state"], "LOGGED_IN")
        self.assertEqual(row["login"], "woahwhattheheck")
        self.assertIs(row["ask_github_login"], False)
        self.assertIs(row["park"], False)

    def test_failed_github_call_is_not_no_perms(self) -> None:
        for blob in (
            "403 rate limit",
            "Resource not accessible by integration",
            "HTTP 404",
            "not logged in",
            "requires authentication",
        ):
            row = hal.classify_github_tool_failure(blob)
            self.assertEqual(row["kind"], "CALL_PATH_RATE_LIMIT_OR_SCOPE")
            self.assertEqual(row["not"], "NO_PERMS")
            self.assertIs(row["ask_github_login"], False)
            self.assertIs(row["park"], False)
            self.assertTrue(row["keep_shipping"])

    def test_may_post_slackauthticket_only_unprompted_challenge(self) -> None:
        self.assertFalse(hal.may_post_slackauthticket(""))
        self.assertFalse(hal.may_post_slackauthticket("/slackauthticket abc.def"))
        self.assertFalse(hal.may_post_slackauthticket("N2RhZGE3OTMtY2NlYy00NmJlLWE1NTAtZjhjYmZmNmRlZWQ3"))
        self.assertFalse(hal.may_post_slackauthticket("too many words here"))
        self.assertTrue(hal.may_post_slackauthticket("AB12"))
        self.assertTrue(hal.may_post_slackauthticket("k7m2-qp9"))

    def test_desk_disposition_keeps_shipping(self) -> None:
        row = hal.desk_disposition(github_error="429 secondary rate limit")
        self.assertTrue(row["keep_shipping"])
        self.assertIs(row["park"], False)
        self.assertIs(row["ask_github_login"], False)
        self.assertIs(row["may_post_slackauthticket"], False)
        self.assertIs(row["fire_337"], False)
        self.assertEqual(row["keep_shipping_roads"], ["slack_mcp", "github_mcp"])
        self.assertEqual(row["slack_cli_svctool"]["status"], "LEFTOVER_NOT_FREEZE")

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "harness_already_logged_in.py"), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["github"]["login"], "woahwhattheheck")
        self.assertTrue(data["keep_shipping"])


if __name__ == "__main__":
    unittest.main()
