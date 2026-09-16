"""grok-patent-docket-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on INVENTION_BURST remint."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestGrokPatentDocketMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_invention_burst_has_autopsy_and_larger(self):
        text = (ROOT / "ground" / "INVENTION_BURST_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("../agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("spy-ground-batch-live-cash-20260905-18", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_provenance_successor_keeps_larger_fixed(self):
        import importlib.util

        path = ROOT / "host" / "patent_docket.py"
        spec = importlib.util.spec_from_file_location("patent_docket_keep", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        entries = mod.PROVENANCE_SUCCESSORS["ground/INVENTION_BURST_INDEX.md"]
        self.assertEqual(len(entries), 1)
        label, raw = entries[0]
        self.assertEqual(label, "spy-ground-live-cash-v1")
        text = raw.decode("utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("../agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("spy-ground-batch-live-cash-20260905-18", text)
        self.assertNotIn("buy.stripe.com", text)
        tip = (ROOT / "ground" / "INVENTION_BURST_INDEX.md").read_bytes()
        self.assertEqual(tip.count(raw), 1)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
