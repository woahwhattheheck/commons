#!/usr/bin/env python3
"""Install Slack custom tools that drive @facebook. Queue sign-in to #needs-bryce."""
from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import needs_bryce_login_queue as nbq  # noqa: E402
import slack_custom_tools_app as app  # noqa: E402
import slack_custom_tools_install as inst  # noqa: E402
import slack_service_tag as sst  # noqa: E402


class NeedsBryceQueueTest(unittest.TestCase):
    def test_spec_is_not_a_commons_gate(self) -> None:
        spec = nbq.load_queue()
        self.assertEqual(spec["id"], "cursor-slack-custom-tools-install-20260902-01")
        self.assertEqual(spec["channel_id"], "C0BRX6EV739")
        self.assertIs(spec["gate"], False)
        self.assertIs(spec["commons_admission"], False)
        self.assertEqual(spec["not"], "commons_admission_gate")
        self.assertEqual(spec["source_slack_ts"], "1788319779.597119")

    def test_facebook_item_has_official_url(self) -> None:
        item = nbq.provider_signin_item("facebook", "post the drop tonight")
        text = nbq.format_item(item)
        self.assertIn("https://developers.facebook.com/apps/", text)
        self.assertIn("NEED:", text)
        self.assertIn("WHY ONLY BRYCE:", text)
        self.assertIn("SMALLEST ACTION:", text)
        self.assertIn("EVIDENCE:", text)
        self.assertIn("AFTER:", text)
        self.assertIn("post the drop tonight", text)
        self.assertNotIn("password", text.lower().split("do not paste a password")[0])
        self.assertIn("Do not paste a password", text)

    def test_rejects_secret_and_vague_gate(self) -> None:
        bad = nbq.provider_signin_item("facebook")
        bad["NEED"] = "owner gate please"
        with self.assertRaises(ValueError) as caught:
            nbq.format_item(bad)
        self.assertIn("vague_owner_gate", str(caught.exception))
        secret = nbq.provider_signin_item("discord")
        secret["SMALLEST ACTION"] = "https://discord.com/developers/applications token=whateversecret"
        with self.assertRaises(ValueError) as caught2:
            nbq.format_item(secret)
        self.assertIn("secrets_forbidden", str(caught2.exception))

    def test_slack_cli_ticket_item(self) -> None:
        item = nbq.slack_cli_ticket_item("/slackauthticket abc.def")
        text = nbq.format_item(item)
        self.assertIn("/slackauthticket abc.def", text)
        self.assertIn("C0BRX6EV739", text)


class SlackCliInstallTest(unittest.TestCase):
    def test_detect_cli_prefers_standard_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / ".slack" / "bin"
            bindir.mkdir(parents=True)
            cli = bindir / "slack"
            cli.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
            cli.chmod(cli.stat().st_mode | stat.S_IXUSR)
            found = inst.detect_cli(home=tmp, path_env="")
            self.assertEqual(found, str(cli))

    def test_parse_login_ticket(self) -> None:
        sample = (
            "Run the following slash command from any Slack channel\n"
            "\n"
            "   /slackauthticket eyJ0eXAiOiJKV1QiLCJh.example\n"
            "\n"
            "? Slack will then show you a challenge code.\n"
        )
        parsed = inst.parse_login_ticket(sample)
        self.assertEqual(parsed["ok"], "true")
        self.assertEqual(
            parsed["slash_command"],
            "/slackauthticket eyJ0eXAiOiJKV1QiLCJh.example",
        )
        self.assertEqual(parsed["ticket"], "eyJ0eXAiOiJKV1QiLCJh.example")
        self.assertEqual(inst.parse_login_ticket("nope")["error"], "no_ticket")

    def test_status_without_cli_queues_needs_bryce(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            row = inst.status(home=tmp, path_env="")
        self.assertFalse(row["installed"])
        self.assertTrue(row["needs_owner_signin"])
        self.assertEqual(row["signin_channel_id"], "C0BRX6EV739")
        self.assertIs(row["commons_admission"], False)

    def test_manifest_defines_drive_tagged_service(self) -> None:
        manifest = inst.build_manifest()
        fn = manifest["functions"]["drive_tagged_service"]
        self.assertEqual(fn["input_parameters"]["tag"]["name"], "tag")
        self.assertEqual(fn["input_parameters"]["body"]["name"], "body")
        self.assertIn("facebook", manifest["display_information"]["description"])
        commands = manifest["features"]["slash_commands"]
        self.assertEqual(commands[0]["command"], "/svctool")
        self.assertTrue(manifest["settings"]["socket_mode_enabled"])
        self.assertIn("function_executed", manifest["settings"]["event_subscriptions"]["bot_events"])
        disk = json.loads(
            (ROOT / "host" / "slack_custom_tools_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(disk["functions"]["drive_tagged_service"]["title"], fn["title"])


class DriveCustomToolTest(unittest.TestCase):
    def test_facebook_without_session_queues_needs_bryce(self) -> None:
        out = app.drive("facebook", "post the drop tonight", sessions={})
        self.assertEqual(out["state"], "NEEDS_OWNER_SIGNIN")
        self.assertEqual(out["channel_id"], "C0BRX6EV739")
        self.assertIn("https://developers.facebook.com/apps/", out["needs_bryce_text"])
        self.assertIn("post the drop tonight", out["needs_bryce_text"])
        self.assertFalse(out["copy_secrets"])
        self.assertNotIn("Bearer", json.dumps(out))
        self.assertEqual(out["intent"]["url"], "https://graph.facebook.com/v21.0/me/feed")

    def test_facebook_with_session_is_ready_without_http(self) -> None:
        calls: list[dict] = []

        def http_request(**kwargs: object) -> None:
            calls.append(kwargs)

        out = app.drive(
            "facebook",
            "post the drop tonight",
            sessions={"facebook": True},
            execute=False,
            http_request=http_request,
        )
        self.assertEqual(out["state"], "READY")
        self.assertFalse(out["http_called"])
        self.assertEqual(calls, [])
        dumped = json.dumps(out)
        self.assertNotIn("EAA", dumped)
        self.assertIn("graph.facebook.com", dumped)

    def test_facebook_execute_does_not_echo_token(self) -> None:
        seen: dict[str, object] = {}

        def http_request(**kwargs: object) -> None:
            seen.update(kwargs)

        env = {"FACEBOOK_ACCESS_TOKEN": "EAA_TEST_TOKEN_NOT_FOR_GIT"}
        out = app.drive(
            "facebook",
            "post hi",
            sessions={"facebook": True},
            environ=env,
            execute=True,
            http_request=http_request,
        )
        self.assertEqual(out["state"], "DRIVEN")
        self.assertTrue(out["http_called"])
        self.assertEqual(seen["url"], "https://graph.facebook.com/v21.0/me/feed")
        dumped = json.dumps(out)
        self.assertNotIn("EAA_TEST_TOKEN_NOT_FOR_GIT", dumped)
        self.assertIn("EAA_TEST_TOKEN_NOT_FOR_GIT", str(seen["headers"]))

    def test_github_without_token_does_not_queue_owner(self) -> None:
        out = app.drive("github", "list my repos", sessions={})
        self.assertEqual(out["state"], "READY")
        self.assertIsNone(out["needs_bryce_text"])

    def test_handle_channel_text_composes_with_peer_router(self) -> None:
        result = sst.route(
            "@facebook post the drop tonight",
            connected=["slack", "github"],
        )
        self.assertIn("SLACK_CUSTOM_TOOL", {j["road"] for j in result["jobs"]})
        payload = app.handle_channel_text(
            "@facebook post the drop tonight",
            connected=["slack", "github"],
            sessions={},
        )
        states = {row["state"] for row in payload["outcomes"]}
        self.assertIn("NEEDS_OWNER_SIGNIN", states)
        self.assertNotIn("IN_HARNESS", states)
        self.assertIs(payload["commons_admission"], False)

    def test_connected_gmail_stays_in_harness(self) -> None:
        payload = app.handle_channel_text(
            "@gmail search for the bid thread",
            connected=["gmail", "slack"],
            sessions={},
        )
        states = {row["state"] for row in payload["outcomes"]}
        self.assertEqual(states, {"IN_HARNESS"})

    def test_parse_svctool(self) -> None:
        self.assertEqual(
            app.parse_svctool_text("/svctool facebook post the drop"),
            ("facebook", "post the drop"),
        )
        self.assertEqual(
            app.parse_svctool_text("@facebook post the drop"),
            ("facebook", "post the drop"),
        )

    def test_peer_files_untouched_and_unique_paths_present(self) -> None:
        peer = (ROOT / "host" / "slack_service_tag.py").read_text(encoding="utf-8")
        self.assertIn("Route Slack @service tags", peer)
        self.assertTrue((ROOT / "ground" / "SLACK_SERVICE_TAGS.json").is_file())
        self.assertTrue((ROOT / "host" / "slack_custom_tools_install.py").is_file())
        self.assertTrue((ROOT / "host" / "needs_bryce_login_queue.py").is_file())
        self.assertTrue((ROOT / "host" / "slack_custom_tools_app.py").is_file())
        self.assertTrue((ROOT / "ground" / "NEEDS_BRYCE_QUEUE.json").is_file())
        card = (ROOT / "ground" / "SLACK_CUSTOM_TOOLS_INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("#needs-bryce", card)
        self.assertIn("drive_tagged_service", card)
        self.assertNotIn("PLACEHOLDER_WILL", card)


if __name__ == "__main__":
    unittest.main()
