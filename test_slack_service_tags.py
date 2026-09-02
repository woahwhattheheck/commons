#!/usr/bin/env python3
"""Slack @service tags route to Slack custom tools. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_tag as sst  # noqa: E402


class SlackServiceTagsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = sst.load_catalog()
        self.card = (ROOT / "ground" / "SLACK_SERVICE_TAGS.md").read_text(encoding="utf-8")
        self.door = (ROOT / "slack-tags.html").read_text(encoding="utf-8")

    def test_catalog_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.cat["id"], "cursor-slack-service-tags-20260902-01")
        self.assertIs(self.cat["gate"], False)
        self.assertIs(self.cat["commons_admission"], False)
        self.assertEqual(self.cat["source_slack_ts"], "1788319779.597119")
        self.assertEqual(self.cat["owner_signin_channel"]["id"], "C0BRX6EV739")
        self.assertEqual(self.cat["owner_signin_channel"]["not"], "commons_admission_gate")

    def test_facebook_example_without_facebook_tool_uses_slack_custom_tool(self) -> None:
        result = sst.route(
            "You are x model with slack connector. @facebook post the drop tonight",
            connected=["slack", "github"],
        )
        self.assertEqual(result["tags"], ["facebook"])
        self.assertIn("post the drop tonight", result["body"])
        roads = {job["road"] for job in result["jobs"] if job["tag"] == "facebook"}
        self.assertIn("SLACK_CUSTOM_TOOL", roads)
        self.assertIn("OWNER_SIGNIN", roads)
        self.assertNotIn("IN_HARNESS", roads)
        signin = next(j for j in result["jobs"] if j["road"] == "OWNER_SIGNIN")
        self.assertEqual(signin["channel_id"], "C0BUFA9G23E")
        self.assertEqual(signin["kind"], "OWNER_BLOCKER")

    def test_connected_gmail_stays_in_harness(self) -> None:
        result = sst.route("@gmail search for the bid thread", connected=["gmail", "slack"])
        jobs = [j for j in result["jobs"] if j["tag"] == "gmail"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["road"], "IN_HARNESS")

    def test_reserved_and_user_mentions_are_not_services(self) -> None:
        result = sst.route(
            "<@U0BR9670G2H> @here @channel @facebook drive the page",
            connected=["slack"],
        )
        self.assertEqual(result["tags"], ["facebook"])
        self.assertNotIn("here", result["tags"])
        self.assertNotIn("channel", result["tags"])

    def test_unknown_tag_is_not_unlisted_verb_rejection(self) -> None:
        result = sst.route("@noisemaker bang the gong", connected=["slack"])
        self.assertEqual(result["tags"], ["noisemaker"])
        self.assertEqual(result["jobs"][0]["road"], "UNKNOWN")
        self.assertIs(result["gate"], False)

    def test_card_and_door_stay_open(self) -> None:
        lowered = self.card.lower()
        self.assertIn("routing convention", lowered)
        self.assertIn("never reject a commons post", lowered)
        self.assertIn("#needs-bryce", lowered)
        self.assertIn("@facebook", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("<form", self.door.lower())
        self.assertNotIn('type="password"', self.door.lower())
        self.assertNotIn("login form", self.door.lower())
        self.assertIn("password", self.door.lower())  # prohibition text only
        self.assertIn("SLACK_SERVICE_TAGS.json", self.door)

    def test_catalog_covers_named_services(self) -> None:
        services = self.cat["services"]
        for name in ("facebook", "instagram", "github", "gmail", "stripe", "x", "heygen", "magicpath", "roboflow"):
            self.assertIn(name, services)
        self.assertGreaterEqual(len(services), 20)
        self.assertEqual(self.cat["aliases"]["twitter"], "x")

    def test_twitter_alias_canonicalizes_to_x(self) -> None:
        result = sst.route("@twitter draft the drop", connected=["slack"])
        self.assertEqual(result["tags"], ["x"])
        roads = {job["road"] for job in result["jobs"] if job["tag"] == "x"}
        self.assertIn("SLACK_CUSTOM_TOOL", roads)
        self.assertIn("OWNER_SIGNIN", roads)
        self.assertIn("draft the drop", result["body"])
        self.assertNotIn("@twitter", result["body"])

    def test_slack_jobs_emit_custom_tool_and_needs_bryce(self) -> None:
        result = sst.route("@facebook post the drop tonight", connected=["slack"])
        kinds = {row["kind"] for row in result["slack_jobs"]}
        self.assertIn("SLACK_CUSTOM_TOOL", kinds)
        self.assertIn("OWNER_BLOCKER", kinds)
        blocker = next(row for row in result["slack_jobs"] if row["kind"] == "OWNER_BLOCKER")
        self.assertEqual(blocker["channel_id"], "C0BUFA9G23E")
        self.assertFalse(blocker["copy_secrets"])
        self.assertIn("Do not paste a password", blocker["text"])

    def test_heygen_without_connector_queues_provider_sign_in(self) -> None:
        result = sst.route("@heygen render the sample", connected=["slack"])
        self.assertEqual(result["tags"], ["heygen"])
        roads = {job["road"] for job in result["jobs"] if job["tag"] == "heygen"}
        self.assertIn("SLACK_CUSTOM_TOOL", roads)
        self.assertIn("OWNER_SIGNIN", roads)
        signin = next(j for j in result["jobs"] if j["road"] == "OWNER_SIGNIN")
        self.assertEqual(signin["channel_id"], "C0BUFA9G23E")

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "slack_service_tag.py"),
                "--text",
                "@facebook say hi",
                "--connected",
                "slack",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["tags"], ["facebook"])
        self.assertIs(data["commons_admission"], False)


if __name__ == "__main__":
    unittest.main()
