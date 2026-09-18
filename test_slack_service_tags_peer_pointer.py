#!/usr/bin/env python3
"""Catalog pointer to peer Slack CLI install stays findable. Did not steal."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class SlackServiceTagsPeerPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = json.loads(
            (ROOT / "ground" / "SLACK_SERVICE_TAGS.json").read_text(encoding="utf-8")
        )
        self.pointer = (self.cat.get("install") or {}).get("complementary_cli_install") or {}
        self.receipt = (
            ROOT / "p" / "cursor-slack-service-tags-peer-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.card = (ROOT / "ground" / "SLACK_SERVICE_TAGS.md").read_text(encoding="utf-8")

    def test_catalog_id_not_reminted(self) -> None:
        self.assertEqual(self.cat["id"], "cursor-slack-service-tags-20260902-01")
        self.assertIs(self.cat["gate"], False)
        self.assertIs(self.cat["commons_admission"], False)

    def test_pointer_names_peer_cli_install(self) -> None:
        self.assertEqual(self.pointer["id"], "cursor-slack-custom-tools-install-20260902-01")
        self.assertEqual(self.pointer["pr"], 7452)
        self.assertEqual(self.pointer["main_squash"], "d646ba323")
        self.assertIs(self.pointer["not_stolen"], True)
        self.assertEqual(self.pointer["cli_challenge_channel"], "C0BRX6EV739")
        self.assertEqual(
            self.pointer["receipt"],
            "p/cursor-slack-custom-tools-install-20260902-01.md",
        )

    def test_peer_unique_paths_still_present(self) -> None:
        for rel in (
            self.pointer["install"],
            self.pointer["app"],
            self.pointer["manifest"],
            self.pointer["login_queue"],
            self.pointer["queue_card"],
            self.pointer["card"],
            self.pointer["receipt"],
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_receipt_and_card_name_the_pointer(self) -> None:
        self.assertIn("install.complementary_cli_install", self.receipt)
        self.assertIn("7452", self.receipt)
        self.assertIn("Did not steal", self.receipt)
        self.assertIn("cursor-slack-custom-tools-install-20260902-01", self.card)
        self.assertIn("PR 7452", self.card)
        self.assertIn("does not steal", self.card.lower())


if __name__ == "__main__":
    unittest.main()
