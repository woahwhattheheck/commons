#!/usr/bin/env python3
"""Build-floor Slack habit card names rooms and stays a routing card, not a lock."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CARD = ROOT / "ground" / "SLACK_BUILD_FLOOR.md"
CATALOG = ROOT / "ground" / "SLACK_BUILD_FLOOR.json"
RECEIPT = ROOT / "p" / "cursor-slack-build-floor-20260830-01.md"


class SlackBuildFloorTests(unittest.TestCase):
    def test_catalog_names_measured_rooms_and_habits(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(catalog["id"], "cursor-slack-build-floor-20260830-01")
        self.assertTrue(catalog["not_a_lock"])
        self.assertEqual(catalog["build_floor"]["id"], "C0BS7AZ4BSL")
        self.assertEqual(catalog["control_plane"]["id"], "C0BRGMDQB6G")
        self.assertEqual(catalog["owner_exclusive"]["id"], "C0BRX6EV739")
        self.assertEqual(catalog["informal"]["id"], "C0BRB1M9RL6")
        self.assertEqual(catalog["announcements"]["id"], "C0BS7ASU1LY")
        self.assertEqual(
            catalog["source_slack"]["build_floor_ts"], "1788074608.972799"
        )
        habits = " ".join(catalog["habits"])
        self.assertIn("one top-level message per lane", habits)
        self.assertIn("do not duplicate the same full receipt", habits)
        self.assertIn("work-thread link", habits)

    def test_card_and_receipt_stay_routing_not_admission(self) -> None:
        card = CARD.read_text(encoding="utf-8")
        receipt = RECEIPT.read_text(encoding="utf-8")
        for blob in (card, receipt):
            self.assertIn("C0BS7AZ4BSL", blob)
            self.assertIn("C0BRGMDQB6G", blob)
            self.assertIn("1788074608.972799", blob)
            self.assertIn("one top-level", blob.lower())
            self.assertIn("not a lock", blob.lower())
            self.assertNotIn("verb allowlist", blob.lower())
            self.assertNotIn("login, signup", blob.lower())
            self.assertNotIn("protected-path", blob.lower())
        self.assertIn("cursor-slack-build-floor-20260830-01", receipt)
        self.assertIn("Direct Contents / Git Data", card)
        self.assertIn("current HEAD", card)
        self.assertIn("exact id", card)


if __name__ == "__main__":
    unittest.main()
