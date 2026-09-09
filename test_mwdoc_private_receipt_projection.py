#!/usr/bin/env python3
"""Keep the public MWDOC receipt aligned with its private-placement record."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POST = "mwdoc-d365-partner-soq-packet-20260902-01"
PUBLIC_PRODUCT_PATHS = (
    "revenue/mwdoc_d365_soq/README.md",
    "revenue/mwdoc_d365_soq/readiness.json",
    "revenue/mwdoc_d365_soq/readiness.html",
    "revenue/mwdoc_d365_soq/rate-sheet-template.csv",
    "scripts/build_mwdoc_d365_soq.py",
    "tests/test_mwdoc_d365_soq.py",
)


class MWDOCPrivateReceiptProjectionTests(unittest.TestCase):
    def test_commercial_packet_stays_off_public_commons(self):
        for path in PUBLIC_PRODUCT_PATHS:
            self.assertFalse((ROOT / path).exists(), path)

    def test_markdown_and_html_record_private_placement(self):
        markdown = (ROOT / "p" / f"{POST}.md").read_text(encoding="utf-8")
        page = (ROOT / "p" / f"{POST}.html").read_text(encoding="utf-8")
        for text in (markdown, page):
            self.assertIn("STATE: MOVED OFF PUBLIC COMMONS", text)
            self.assertIn("woahwhattheheck/aquatrace-lims", text)
            self.assertIn("Do not re-merge them here", text)

    def test_html_drops_superseded_public_candidate_claim(self):
        page = (ROOT / "p" / f"{POST}.html").read_text(encoding="utf-8")
        self.assertNotIn("STATE: REVIEWED CANDIDATE", page)
        self.assertNotIn("compares the official RFQ to current Commons evidence", page)

    def test_no_login_or_secret_material_is_added(self):
        page = (ROOT / "p" / f"{POST}.html").read_text(encoding="utf-8")
        lower = page.lower()
        self.assertNotIn("type=\"password\"", lower)
        for marker in ("ghp_", "sk_live_", "xoxb-", "akia"):
            self.assertNotIn(marker, lower)


if __name__ == "__main__":
    unittest.main()
