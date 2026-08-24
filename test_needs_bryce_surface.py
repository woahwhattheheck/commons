#!/usr/bin/env python3
"""Contract for the narrow owner-blocker surface."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
CHANNEL_ID = "C0BRX6EV739"
FIELDS = ("NEED", "WHY ONLY BRYCE", "SMALLEST ACTION", "EVIDENCE", "AFTER")


class NeedsBryceSurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page = (ROOT / "needs-bryce.html").read_text(encoding="utf-8")
        self.contract = (ROOT / "ground" / "NEEDS_BRYCE.md").read_text(encoding="utf-8")

    def test_live_slack_channel_and_home_paths_are_named(self) -> None:
        for text in (self.page, self.contract):
            self.assertIn(CHANNEL_ID, text)
            self.assertIn("https://tokenjunkielabs.slack.com/archives/" + CHANNEL_ID, text)
        self.assertIn('href="./index.html"', self.page)
        self.assertIn('href="./to/BRYCE.html"', self.page)

    def test_narrow_queue_is_not_the_broad_owner_inbox(self) -> None:
        for text in (self.page, self.contract):
            self.assertIn("to: BRYCE", text)
            self.assertIn("kind: OWNER_BLOCKER", text)
            self.assertIn("broad", text.lower())
            self.assertIn("inbox", text.lower())
        self.assertIn("do not cross-post", self.page.lower())

    def test_actionable_only_shape_is_complete(self) -> None:
        for field in FIELDS:
            self.assertIn(field + ":", self.page)
            self.assertIn(field + ":", self.contract)

    def test_convention_never_becomes_an_ingest_gate(self) -> None:
        for text in (self.page, self.contract):
            lowered = text.lower()
            self.assertIn("routing convention", lowered)
            self.assertIn("not", lowered)
            self.assertIn("gate", lowered)
            self.assertIn("missing metadata never", lowered)


if __name__ == "__main__":
    unittest.main()
