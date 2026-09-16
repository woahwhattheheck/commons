"""grok-change-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on change.md remint."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import llms_txt

ROOT = Path(__file__).resolve().parent
CLAIM = "grok-change-md-keep-larger-fixed-20260916-01"
PRODUCTS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
    "diagnostic.html",
    "commercial.html",
)


class TestGrokChangeMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_change_live_cash_constant_has_autopsy_and_larger(self):
        block = llms_txt.CHANGE_LIVE_CASH
        self.assertIn("## Live cash", block)
        self.assertIn("./agent-rescue.html", block)
        self.assertIn("$199", block)
        self.assertIn("Larger fixed engagements", block)
        self.assertIn("./diagnostic.html", block)
        self.assertIn("./commercial.html", block)
        self.assertIn("$12,000", block)
        self.assertIn("$30,000", block)
        self.assertNotIn("buy.stripe.com", block)

    def test_tip_change_md_has_autopsy_and_larger(self):
        text = (ROOT / "change.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("./agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("./diagnostic.html", text)
        self.assertIn("./commercial.html", text)
        self.assertIn("$12,000", text)
        self.assertIn("$30,000", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertLessEqual(len(text.encode("utf-8")), llms_txt.CHANGE_MAX_BYTES)

    def test_write_change_rate_keeps_larger_under_budget(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        with open(os.path.join(root, "pulse.json"), "w", encoding="utf-8") as handle:
            json.dump({"seq": 1, "post_count": 10, "head": "abc", "newest": []}, handle)
        with open(os.path.join(root, "builds.json"), "w", encoding="utf-8") as handle:
            json.dump({"n_open_prs": 0}, handle)
        text = llms_txt.write_change_rate(
            [{"id": "keep-larger-20260916-01"}],
            "2026-09-16T21:00:00Z",
            head="a" * 40,
            n_tips=0,
            p_new=0,
            root=root,
        )
        self.assertIn("## Live cash", text)
        self.assertIn("./agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("./diagnostic.html", text)
        self.assertIn("./commercial.html", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertLessEqual(len(text.encode("utf-8")), llms_txt.CHANGE_MAX_BYTES)
        baked = Path(root, "change.md").read_text(encoding="utf-8")
        self.assertEqual(baked, text)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
