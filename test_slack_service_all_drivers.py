#!/usr/bin/env python3
"""Catalog-complete Slack @tag drivers. Not a Commons gate."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_all_drivers as all_drivers  # noqa: E402
import slack_service_tag as sst  # noqa: E402


class SlackServiceAllDriversTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = sst.load_catalog()
        self.card = (ROOT / "ground" / "SLACK_SERVICE_ALL_DRIVERS.md").read_text(
            encoding="utf-8"
        )

    def _clear_env(self, *keys: str) -> dict[str, str | None]:
        backup: dict[str, str | None] = {}
        for key in keys:
            backup[key] = os.environ.pop(key, None)
        return backup

    def _restore_env(self, backup: dict[str, str | None]) -> None:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_every_catalog_service_has_a_real_driver(self) -> None:
        services = all_drivers.catalog_services(self.cat)
        self.assertGreaterEqual(len(services), 20)
        empty = {key: "" for key in sum(all_drivers.ENV_KEYS.values(), ())}
        for name in services:
            out = all_drivers.drive(name, "ping", connected=["slack"], environ=empty)
            self.assertNotEqual(out.get("reason"), "driver_queued", name)
            self.assertIn(out.get("road"), {
                "SLACK_CUSTOM_TOOL",
                "OWNER_SIGNIN",
                "IN_HARNESS",
                "UNKNOWN",
            })
            self.assertIs(out.get("gate"), False)
            self.assertIs(out.get("copy_secrets"), False)
            blob = json.dumps(out)
            self.assertNotIn("xoxb-", blob)
            self.assertNotIn("sk-ant-", blob)

    def test_facebook_without_session_stays_owner_signin(self) -> None:
        backup = self._clear_env(*all_drivers.facebook_peer.TOKEN_ENV)
        try:
            out = all_drivers.drive("facebook", "post the drop tonight", connected=["slack"])
        finally:
            self._restore_env(backup)
        self.assertEqual(out["tag"], "facebook")
        self.assertEqual(out["road"], "OWNER_SIGNIN")
        self.assertEqual(out["reason"], "no_facebook_session_in_this_process")
        self.assertFalse(out["ok"])

    def test_magicpath_peer_remainder_does_not_reopen_need(self) -> None:
        out = all_drivers.drive("magicpath", "list projects", connected=["slack"])
        self.assertEqual(out["road"], "SLACK_CUSTOM_TOOL")
        self.assertEqual(out["reason"], "peer_harness_remainder")
        self.assertEqual(out["peer_desk"], "GOAT")
        self.assertIs(out["this_process_tools"], False)
        self.assertIs(out["reopen_need"], False)
        self.assertIn("bc-73365238", out["measured_cloud_seats"])
        self.assertIn(
            "bc-63f55b0a-5b1d-5654-9f33-5c5a8cf245a0",
            out["measured_cloud_seats"],
        )
        self.assertNotEqual(out["road"], "OWNER_SIGNIN")
        payload = all_drivers.drive_text("@magicpath list projects", connected=["slack"])
        posts = all_drivers.format_slack_posts(payload)
        kinds = {row["kind"] for row in posts}
        self.assertIn("SLACK_CUSTOM_TOOL", kinds)
        self.assertNotIn("OWNER_BLOCKER", kinds)
        blob = "\n".join(row["text"] for row in posts)
        self.assertIn("reopen_need=false", blob)
        self.assertIn("peer_desk=GOAT", blob)
        self.assertNotIn("OWNER_BLOCKER", blob)

    def test_notion_peer_remainder_does_not_reopen_need(self) -> None:
        out = all_drivers.drive("notion", "list databases", connected=["slack"])
        self.assertEqual(out["road"], "SLACK_CUSTOM_TOOL")
        self.assertEqual(out["reason"], "peer_harness_remainder")
        self.assertEqual(out["peer_desk"], "GOAT")
        self.assertIs(out["this_process_tools"], False)
        self.assertIs(out["reopen_need"], False)
        self.assertIn("bc-73365238", out["measured_cloud_seats"])
        self.assertIn(
            "bc-f49eebc7-1125-5fd8-82e2-374889f4b17f",
            out["measured_cloud_seats"],
        )
        self.assertNotEqual(out["road"], "OWNER_SIGNIN")
        payload = all_drivers.drive_text("@notion list databases", connected=["slack"])
        posts = all_drivers.format_slack_posts(payload)
        kinds = {row["kind"] for row in posts}
        self.assertIn("SLACK_CUSTOM_TOOL", kinds)
        self.assertNotIn("OWNER_BLOCKER", kinds)
        blob = "\n".join(row["text"] for row in posts)
        self.assertIn("reopen_need=false", blob)
        self.assertIn("peer_desk=GOAT", blob)
        self.assertNotIn("OWNER_BLOCKER", blob)

    def test_heygen_and_roboflow_still_queue_provider_sign_in(self) -> None:
        empty = {key: "" for key in sum(all_drivers.ENV_KEYS.values(), ())}
        for name, url in (
            ("heygen", "https://app.heygen.com/settings"),
            ("roboflow", "https://app.roboflow.com/settings/api"),
        ):
            out = all_drivers.drive(name, "render the sample", connected=["slack"], environ=empty)
            self.assertEqual(out["road"], "OWNER_SIGNIN", name)
            self.assertEqual(out["signin_url"], url)
            self.assertTrue(str(out["signin_url"]).startswith("https://"))
            self.assertEqual(out["channel_id"], "C0BUFA9G23E")

    def test_github_without_session_is_custom_tool_not_need(self) -> None:
        empty = {"GITHUB_TOKEN": "", "GH_TOKEN": ""}
        out = all_drivers.drive("github", "whoami", connected=["slack"], environ=empty)
        self.assertEqual(out["road"], "SLACK_CUSTOM_TOOL")
        self.assertEqual(out["reason"], "no_local_session")
        self.assertNotEqual(out["road"], "OWNER_SIGNIN")

    def test_connected_gmail_stays_in_harness(self) -> None:
        out = all_drivers.drive("gmail", "search bids", connected=["gmail", "slack"])
        self.assertEqual(out["road"], "IN_HARNESS")

    def test_unknown_tag_is_not_rejected(self) -> None:
        out = all_drivers.drive("noisemaker", "bang", connected=["slack"])
        self.assertEqual(out["road"], "UNKNOWN")
        self.assertIs(out["gate"], False)
        self.assertIs(out["commons_admission"], False)

    def test_twitter_alias_drives_x(self) -> None:
        empty = {key: "" for key in all_drivers.ENV_KEYS["x"]}
        payload = all_drivers.drive_text(
            "@twitter draft the drop",
            connected=["slack"],
            environ=empty,
        )
        self.assertEqual(payload["tags"], ["x"])
        roads = {row["road"] for row in payload["outcomes"]}
        self.assertIn("OWNER_SIGNIN", roads)

    def test_ready_dry_run_and_opt_in_http(self) -> None:
        calls: list[dict[str, Any]] = []

        def http_request(**kwargs: object) -> None:
            calls.append(kwargs)

        out = all_drivers.drive(
            "github",
            "whoami",
            connected=["slack"],
            environ={"GITHUB_TOKEN": "ghp_test_not_a_secret"},
        )
        self.assertEqual(out["reason"], "ready_dry_run")
        self.assertFalse(out["http_called"])
        driven = all_drivers.drive(
            "github",
            "whoami",
            connected=["slack"],
            environ={"GITHUB_TOKEN": "ghp_test_not_a_secret"},
            execute=True,
            http_request=http_request,
        )
        self.assertEqual(driven["reason"], "driven")
        self.assertTrue(driven["http_called"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "https://api.github.com/user")
        blob = json.dumps(driven)
        self.assertNotIn("ghp_test_not_a_secret", blob)

    def test_card_stays_open(self) -> None:
        lowered = self.card.lower()
        self.assertIn("every catalog", lowered)
        self.assertIn("@magicpath", lowered)
        self.assertIn("not stolen", lowered)
        self.assertIn("#provider-sign-in", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("login form", lowered)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "slack_service_all_drivers.py"),
                "--text",
                "@magicpath list projects",
                "--connected",
                "slack",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["tags"], ["magicpath"])
        self.assertIs(data["commons_admission"], False)
        self.assertEqual(data["outcomes"][0]["reason"], "peer_harness_remainder")


if __name__ == "__main__":
    unittest.main()
