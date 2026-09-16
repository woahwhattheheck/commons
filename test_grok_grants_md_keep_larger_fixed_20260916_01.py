"""grok-grants-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on GRANTS.md remint."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GRANTS = ROOT / "GRANTS.md"
PRODUCTS = ("agent-rescue.html", "diagnostic.html", "commercial.html")
BASELINE_BLOB = "34e4baadebb27388137d12c2b7cfa515f88d4672"


def _load_docket():
    spec = importlib.util.spec_from_file_location(
        "patent_docket", ROOT / "host" / "patent_docket.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestGrokGrantsMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_grants_has_autopsy_and_larger(self):
        text = GRANTS.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("./agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("./diagnostic.html", text)
        self.assertIn("./commercial.html", text)
        self.assertIn("$12,000", text)
        self.assertIn("$30,000", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_second_successor_keeps_historical_blob(self):
        docket = _load_docket()
        successors = docket.PROVENANCE_SUCCESSORS["GRANTS.md"]
        self.assertEqual(
            [label for label, _ in successors],
            [
                "bass-grants-live-cash-v2",
                "grok-grants-md-keep-larger-fixed-20260916-01",
            ],
        )
        raw = GRANTS.read_bytes()
        baseline, applied = docket._normalize_provenance_successors("GRANTS.md", raw)
        self.assertEqual(
            applied,
            [
                "bass-grants-live-cash-v2",
                "grok-grants-md-keep-larger-fixed-20260916-01",
            ],
        )
        self.assertEqual(docket._git_blob_oid(baseline), BASELINE_BLOB)
        self.assertNotIn(b"## Live cash", baseline)
        self.assertNotIn(b"diagnostic.html", baseline)
        self.assertNotIn(b"buy.stripe.com", raw)

    def test_index_spy_ground_successor_untouched(self):
        docket = _load_docket()
        labels = [label for label, _ in docket.PROVENANCE_SUCCESSORS["ground/INVENTION_BURST_INDEX.md"]]
        self.assertEqual(labels, ["spy-ground-live-cash-v1"])

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
