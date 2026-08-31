#!/usr/bin/env python3
"""Canaries for the patent-products door, sales insert, receipt, and registry.

The door is proof/catalog, never a storefront. The insert is internal and
must not invent payment links, buyers, cash, or device actuation.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOOR = ROOT / "patent-products.html"
INSERT = ROOT / "patent-products" / "SALES-INSERT.md"
POST = ROOT / "p" / "patent-products-20260831-01.md"
REGISTRY = ROOT / "features" / "registry" / "patent-products-20260831-01.json"
PATENT_MD = ROOT / "muhl" / "docs" / "PROVISIONAL_SESSION.md"
PATENT_PDF = ROOT / "muhl" / "docs" / "PROVISIONAL_SESSION.pdf"
TOOLS = (
    ROOT / "host" / "germline.py",
    ROOT / "host" / "mirror_organ.py",
    ROOT / "host" / "winner_fold.py",
)
TESTS = (
    ROOT / "test_germline.py",
    ROOT / "test_mirror_organ.py",
    ROOT / "test_winner_fold.py",
)

BANNED_EVERYWHERE = (
    "buy.stripe.com",
    "stripe.com/buy",
    "shopify.com",
    "fire 337",
    "fire_action",
)


class TestPatentProductSurfaces(unittest.TestCase):
    def test_all_paths_exist(self):
        for path in (DOOR, INSERT, POST, REGISTRY, PATENT_MD, PATENT_PDF, *TOOLS, *TESTS):
            self.assertTrue(path.is_file(), f"missing {path}")

    def test_door_cites_patent_and_runnable_proof(self):
        html = DOOR.read_text()
        self.assertIn("PROVISIONAL_SESSION", html)
        self.assertIn("Bryce Muhlnickel", html)
        self.assertIn("test_germline.py", html)
        self.assertIn("test_mirror_organ.py", html)
        self.assertIn("test_winner_fold.py", html)
        self.assertIn("not a storefront", html.lower())

    def test_insert_keeps_sales_motion_honest(self):
        text = INSERT.read_text()
        self.assertIn("$199", text)
        self.assertIn("$2,500", text)
        self.assertIn("Master of Accounts", text)
        self.assertIn("never send a prospect to Commons/GitHub", text)

    def test_no_invented_payment_or_actuation_anywhere(self):
        for path in (DOOR, INSERT, POST):
            body = path.read_text().lower()
            for banned in BANNED_EVERYWHERE:
                self.assertNotIn(banned.lower(), body, f"{banned} in {path}")

    def test_receipt_preserves_id_and_boundaries(self):
        post = POST.read_text()
        self.assertIn("id: patent-products-20260831-01", post)
        self.assertIn("no `.mno` actuation", post)
        self.assertIn("21/21", post)

    def test_registry_entry_is_valid_and_points_at_tests(self):
        entry = json.loads(REGISTRY.read_text())
        self.assertEqual(entry["schema"], "commons-feature-v1")
        self.assertEqual(entry["id"], "patent-products-20260831-01")
        self.assertEqual(entry["public_entrypoint"], "patent-products.html")
        for test in ("test_germline.py", "test_mirror_organ.py", "test_winner_fold.py"):
            self.assertIn(test, entry["test_paths"])
            self.assertIn(test, entry["claimed_paths"])


if __name__ == "__main__":
    unittest.main()
