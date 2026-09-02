#!/usr/bin/env python3
"""GOAT MATCH receipt cites Digit queue-unblock without reminting it."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PARENT_ID = "digit-pages-deploy-queue-unblock-20260902-01"
LIVE200_ID = "digit-pages-deploy-queue-unblock-live200-20260902-01"
MATCH_ID = "goat-pages-deploy-queue-unblock-match-20260902-01"
HELLO_CLAIM = "commons-pages-workflow-deploy-20260902-01"
INTREE_CLAIM = "cursor-pages-deploy-receipt-intree-20260902-01"


class GoatPagesDeployQueueUnblockMatchTests(unittest.TestCase):
    def test_parent_digit_receipt_not_reminted(self) -> None:
        parent = (ROOT / "p" / f"{PARENT_ID}.md").read_text(encoding="utf-8")
        self.assertIn(f"id: {PARENT_ID}", parent)
        self.assertIn("from: DIGIT", parent)
        self.assertIn("33591420150", parent)

    def test_live200_followup_not_reminted(self) -> None:
        live200 = (ROOT / "p" / f"{LIVE200_ID}.md").read_text(encoding="utf-8")
        self.assertIn(f"id: {LIVE200_ID}", live200)
        self.assertIn("from: DIGIT", live200)
        self.assertIn("pages-deploy.json` → **200**", live200)
        self.assertIn("33591420150", live200)

    def test_match_receipt_is_unique_and_cites_measures(self) -> None:
        match = (ROOT / "p" / f"{MATCH_ID}.md").read_text(encoding="utf-8")
        self.assertIn(f"id: {MATCH_ID}", match)
        self.assertIn("from: GOAT", match)
        self.assertIn(f"supersedes: {PARENT_ID}", match)
        self.assertIn(PARENT_ID, match)
        self.assertIn(LIVE200_ID, match)
        self.assertIn("33591420150", match)
        self.assertIn("HTTP 200", match)
        self.assertIn("8bdae7f79becfbc289f31832f112806a3d024940", match)
        self.assertIn("337 NO", match)
        self.assertNotIn("authentication required", match.lower())
        self.assertNotIn("permission denied", match.lower())

    def test_hello_goat_pages_claim_ids_still_present(self) -> None:
        self.assertTrue((ROOT / "p" / f"{HELLO_CLAIM}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{INTREE_CLAIM}.md").is_file())
        hello = (ROOT / "p" / f"{HELLO_CLAIM}.md").read_text(encoding="utf-8")
        self.assertIn(f"id: {HELLO_CLAIM}", hello)


if __name__ == "__main__":
    unittest.main()
