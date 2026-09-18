"""grok-patent-docket-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on INVENTION_BURST remint."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "ground" / "INVENTION_BURST_INDEX.md"
PRODUCTS = ("agent-rescue.html", "diagnostic.html", "commercial.html")
# hist pin 0720ef57 plus later Contest product section; cash successors strip off.
BASELINE_BLOB = "5de7ae09bc1cbb5c169720967f7c577ff0d8049c"
SPY_LABEL = "spy-ground-live-cash-v1"
LARGER_LABEL = "grok-patent-docket-md-keep-larger-fixed-20260916-01"


def _load_docket():
    import importlib.util

    path = ROOT / "host" / "patent_docket.py"
    spec = importlib.util.spec_from_file_location("patent_docket_keep", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestGrokPatentDocketMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_invention_burst_has_autopsy_and_larger(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("../agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("spy-ground-batch-live-cash-20260905-18", text)
        self.assertNotIn("buy.stripe.com", text)
        live, larger = text.split("Larger fixed engagements", 1)
        self.assertIn("Shelf:", live)
        self.assertIn("diagnostic.html", larger)

    def test_second_successor_keeps_spy_ground_and_larger(self):
        mod = _load_docket()
        entries = mod.PROVENANCE_SUCCESSORS["ground/INVENTION_BURST_INDEX.md"]
        self.assertEqual([label for label, _ in entries], [SPY_LABEL, LARGER_LABEL])
        spy = entries[0][1].decode("utf-8")
        larger = entries[1][1].decode("utf-8")
        self.assertIn("## Live cash", spy)
        self.assertIn("../agent-rescue.html", spy)
        self.assertIn("spy-ground-batch-live-cash-20260905-18", spy)
        self.assertNotIn("Larger fixed engagements", spy)
        self.assertNotIn("diagnostic.html", spy)
        self.assertIn("Larger fixed engagements", larger)
        self.assertIn("../diagnostic.html", larger)
        self.assertIn("../commercial.html", larger)
        self.assertNotIn("buy.stripe.com", spy)
        self.assertNotIn("buy.stripe.com", larger)
        raw = INDEX.read_bytes()
        baseline, applied = mod._normalize_provenance_successors(
            "ground/INVENTION_BURST_INDEX.md", raw
        )
        self.assertEqual(applied, [SPY_LABEL, LARGER_LABEL])
        self.assertEqual(mod._git_blob_oid(baseline), BASELINE_BLOB)
        self.assertNotIn(b"## Live cash", baseline)
        self.assertNotIn(b"diagnostic.html", baseline)
        self.assertEqual(raw.count(entries[0][1]), 1)
        self.assertEqual(raw.count(entries[1][1]), 1)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
