#!/usr/bin/env python3
"""Installed Slack @service custom-tool worker. Not a Commons gate."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_drivers as drivers  # noqa: E402
import slack_service_tag_worker as worker  # noqa: E402


class SlackServiceTagWorkerTest(unittest.TestCase):
    def test_facebook_without_session_queues_provider_sign_in(self) -> None:
        env_backup = {
            key: os.environ.pop(key, None)
            for key in drivers.TOKEN_ENV
        }
        try:
            posts = worker.posts_for_message(
                "@facebook post the drop tonight",
                channel="C0BU51F1PL3",
                ts="1788319779.597119",
                connected=["slack"],
            )
        finally:
            for key, value in env_backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        channels = {row["channel"] for row in posts}
        self.assertIn("C0BU51F1PL3", channels)
        self.assertIn("C0BUFA9G23E", channels)
        blob = "\n".join(row["text"] for row in posts)
        self.assertIn("service-tag-job", blob)
        self.assertIn("OWNER_SIGNIN", blob)
        self.assertIn("password", blob.lower())
        self.assertNotIn("authentication required", blob.lower())

    def test_already_handled_skips_marker_replies(self) -> None:
        self.assertTrue(
            worker.already_handled(
                [{"text": "service-tag-job tags=facebook roads=SLACK_CUSTOM_TOOL"}]
            )
        )
        self.assertFalse(worker.already_handled([{"text": "@facebook hello"}]))

    def test_poll_dispatches_once(self) -> None:
        calls: list[tuple[str, dict]] = []

        def api(_token: str, method: str, payload: dict) -> dict:
            calls.append((method, payload))
            if method == "conversations.history":
                return {
                    "ok": True,
                    "messages": [
                        {
                            "ts": "111.222",
                            "text": "@facebook post the drop tonight",
                        }
                    ],
                }
            if method == "conversations.replies":
                return {"ok": True, "messages": [{"ts": "111.222", "text": "@facebook post the drop tonight"}]}
            if method == "chat.postMessage":
                return {"ok": True, "ts": "111.333"}
            return {"ok": False, "error": method}

        result = worker.poll_and_dispatch(
            "xoxb-test",
            channels=["C0BU51F1PL3"],
            connected=["slack"],
            api=api,
        )
        self.assertEqual(result["handled"], 1)
        posted = [p for m, p in calls if m == "chat.postMessage"]
        self.assertGreaterEqual(len(posted), 2)
        self.assertTrue(any(p.get("channel") == "C0BUFA9G23E" for p in posted))

    def test_facebook_driver_without_token_is_signin(self) -> None:
        env_backup = {key: os.environ.pop(key, None) for key in drivers.TOKEN_ENV}
        try:
            out = drivers.drive_facebook("hello")
        finally:
            for key, value in env_backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertFalse(out["ok"])
        self.assertEqual(out["road"], "OWNER_SIGNIN")
        self.assertFalse(out["copy_secrets"])

    def test_cli_one_shot_json(self) -> None:
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "slack_service_tag_worker.py"),
                "--text",
                "@facebook say hi",
                "--connected",
                "slack",
                "--channel",
                "C0BU51F1PL3",
                "--ts",
                "1.2",
            ],
            check=True,
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k not in drivers.TOKEN_ENV},
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["gate"], False)
        self.assertTrue(data["posts"])

    def test_catalog_records_live_install(self) -> None:
        import slack_service_tag as sst

        cat = sst.load_catalog()
        install = cat["install"]
        self.assertEqual(install["id"], "cursor-slack-service-tools-install-20260902-01")
        self.assertEqual(install["login_channel"]["id"], "C0BUFA9G23E")
        self.assertEqual(install["slack_list_id"], "F0BU7D9RBL5")
        self.assertEqual(install["slack_canvas_id"], "F0BU5DQEJ2F")
        self.assertEqual(
            install["complementary_cli_install"]["id"],
            "cursor-slack-custom-tools-install-20260902-01",
        )
        self.assertIs(cat["gate"], False)

    def test_magicpath_peer_connected_skips_new_need(self) -> None:
        posts = worker.posts_for_message(
            "@magicpath list projects",
            channel="C0BU51F1PL3",
            ts="1788321949.478239",
            connected=["slack"],
        )
        channels = {row["channel"] for row in posts}
        self.assertIn("C0BU51F1PL3", channels)
        self.assertNotIn("C0BUFA9G23E", channels)
        blob = "\n".join(row["text"] for row in posts)
        self.assertIn("service-tag-job", blob)
        self.assertIn("SLACK_CUSTOM_TOOL", blob)
        self.assertIn("peer_desk=GOAT", blob)
        self.assertNotIn("OWNER_BLOCKER", blob)
        self.assertNotIn("authentication required", blob.lower())


if __name__ == "__main__":
    unittest.main()
