#!/usr/bin/env python3
"""One failed GitHub call is that action, not a missing login. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import github_call_not_login as ghnl  # noqa: E402


class GitHubCallNotLoginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = ghnl.load_law()
        self.card = (ROOT / "ground" / "GITHUB_CALL_NOT_LOGIN.md").read_text(
            encoding="utf-8"
        )
        self.helper = (ROOT / "host" / "github_call_not_login.py").read_text(
            encoding="utf-8"
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-github-call-not-login-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertIs(self.law["login_ask"], False)
        self.assertIs(self.law["park_for_owner_login"], False)
        self.assertIs(self.law["freeze"], False)
        self.assertEqual(self.law["harness_github_login"], "already_present")
        self.assertEqual(self.law["source_channel_id"], "C0BU51F1PL3")
        self.assertEqual(self.law["source_slack_ts"], "1788325694.170879")
        self.assertEqual(self.law["also_named_channel_id"], "C0BRX6EV739")
        self.assertEqual(self.law["never_verdict"], "MISSING_LOGIN_FREEZE")
        self.assertNotIn("MISSING_LOGIN_FREEZE", self.law["verdicts"])
        self.assertEqual(self.law["not"], "commons_admission_gate")
        self.assertNotIn("337 NO", json.dumps(self.law))
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.helper)

    def test_card_repeats_owner_prohibition_not_a_login_form(self) -> None:
        self.assertIn("already logged into GitHub", self.card)
        self.assertIn("Do not open another GitHub login ask", self.card)
        self.assertIn("Do not park work waiting for Bryce to log in", self.card)
        self.assertIn("No authentication", self.card)
        self.assertIn("Never a gate", self.card)
        self.assertNotIn("<form", self.card)
        self.assertNotIn('type="password"', self.card)

    def test_workflow_dispatch_403_is_scope_of_action_not_login(self) -> None:
        result = ghnl.classify(
            status=403,
            action="workflow_dispatch",
            message="HTTP 403 on Actions createWorkflowDispatch",
        )
        self.assertEqual(result["verdict"], "SCOPE_OF_ACTION")
        self.assertIs(result["login_ask"], False)
        self.assertIs(result["park_for_owner_login"], False)
        self.assertIs(result["freeze"], False)
        self.assertIs(result["gate"], False)
        self.assertEqual(result["github_login"], "already_present")
        self.assertNotEqual(result["verdict"], "MISSING_LOGIN_FREEZE")
        self.assertIn("unique-push HEAD:main", result["alternate_roads"])
        self.assertIn("contents API PUT", result["alternate_roads"])

    def test_401_is_call_failed_not_a_login_ask(self) -> None:
        result = ghnl.classify(status=401, action="repos.create_or_update_file")
        self.assertEqual(result["verdict"], "CALL_FAILED")
        self.assertIs(result["login_ask"], False)
        self.assertIs(result["keep_shipping"], True)
        self.assertEqual(result["never_verdict"], "MISSING_LOGIN_FREEZE")

    def test_429_is_rate_limited(self) -> None:
        result = ghnl.classify(status=429, action="search_code", message="rate limit")
        self.assertEqual(result["verdict"], "RATE_LIMITED")
        self.assertIs(result["login_ask"], False)

    def test_404_is_path_wrong(self) -> None:
        result = ghnl.classify(status=404, action="repos.get_content", message="Not Found")
        self.assertEqual(result["verdict"], "PATH_WRONG")
        self.assertIs(result["login_ask"], False)

    def test_200_is_ok_with_no_alternate_roads(self) -> None:
        result = ghnl.classify(status=200, action="get_me")
        self.assertEqual(result["verdict"], "OK")
        self.assertEqual(result["alternate_roads"], [])
        self.assertIs(result["login_ask"], False)

    def test_unknown_status_still_not_a_login_ask(self) -> None:
        result = ghnl.classify(status=None, action="mystery_tool")
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertIs(result["login_ask"], False)
        self.assertTrue(result["alternate_roads"])

    def test_classify_never_asks_for_login(self) -> None:
        for status in (None, 200, 401, 403, 404, 409, 422, 429, 500):
            result = ghnl.classify(status=status, action="any")
            self.assertIs(result["login_ask"], False, msg=str(status))
            self.assertNotEqual(result["verdict"], "MISSING_LOGIN_FREEZE")

    def test_owner_prohibition_text_is_not_itself_an_ask(self) -> None:
        text = (
            "EVERY SINGLE HARNESS IS ALREADY LOGGED INTO GITHUB. "
            "Do not open another GitHub login ask. "
            "Do not park work waiting for Bryce to \"log in.\" Keep shipping."
        )
        self.assertFalse(ghnl.opens_github_login_ask(text))

    def test_park_on_missing_github_login_is_an_ask(self) -> None:
        self.assertTrue(
            ghnl.opens_github_login_ask(
                "No GitHub login. Need Bryce to log in before we can push."
            )
        )
        self.assertTrue(
            ghnl.opens_github_login_ask(
                "please log in to github so this harness can keep shipping"
            )
        )

    def test_cli_classifies_workflow_dispatch_403(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "github_call_not_login.py"),
                "--status",
                "403",
                "--action",
                "workflow_dispatch",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "SCOPE_OF_ACTION")
        self.assertIs(payload["login_ask"], False)
        self.assertEqual(payload["law_id"], "cursor-github-call-not-login-20260902-01")

    def test_measured_github_mcp_login_is_woahwhattheheck(self) -> None:
        measured = self.law["measured_this_seat_github_mcp"]
        self.assertEqual(measured["tool"], "get_me")
        self.assertEqual(measured["login"], "woahwhattheheck")
        self.assertEqual(measured["id"], 293286387)

    def test_peer_complement_is_different_paths_clear_to_merge(self) -> None:
        peer = self.law["peer_complement"]
        self.assertEqual(peer["id"], "cursor-github-already-logged-in-20260902-01")
        self.assertEqual(peer["owner"], "bc-31c8ef9a")
        self.assertEqual(peer["claim_slack_ts"], "1788326001.058249")
        self.assertIs(peer["same_paths"], False)
        self.assertEqual(peer["merge"], "CLEAR_TO_MERGE")
        self.assertIs(peer["did_not_steal"], True)
        self.assertIs(peer["did_not_remint"], True)
        self.assertEqual(peer["helper"], "host/github_already_logged_in.py")
        self.assertNotEqual(peer["helper"], self.law["helper"])
        self.assertNotEqual(peer["receipt"], self.law["receipt"])
        self.assertTrue((ROOT / peer["helper"]).is_file())
        self.assertTrue((ROOT / peer["tests"]).is_file())
        self.assertTrue((ROOT / peer["rule"]).is_file())
        self.assertTrue((ROOT / peer["receipt"]).is_file())
        self.assertEqual(
            (ROOT / "p/cursor-github-call-not-login-20260902-01.md").read_text(
                encoding="utf-8"
            ).split("id: ", 1)[1].split("\n", 1)[0],
            "cursor-github-call-not-login-20260902-01",
        )
        self.assertIn("Peer complement", self.card)
        self.assertNotIn("337 NO", json.dumps(peer))


if __name__ == "__main__":
    unittest.main()
