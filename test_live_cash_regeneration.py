#!/usr/bin/env python3
"""Cash doors survive real digest and hub regeneration from missing outputs."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import hub_pages
import llms_txt

PRODUCTS = (
    "agent-rescue.html", "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html", "repair-booking-preflight.html",
    "plant-downtime-handoff.html", "tools-cash.html", "commerce.html",
)


class LiveCashRegenerationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.mod = SimpleNamespace(
            ROOT=str(self.root), CSS="", doors=lambda: '<nav>existing doors</nav>',
            _write=lambda path, text: Path(path).write_text(text, encoding="utf-8"),
        )
        self.rows = [
            ("2026-09-05T02:00:00Z", {"id": "new-salon", "from": "BETA", "board": "SALON"}, ""),
            ("2026-09-05T01:00:00Z", {"id": "new-feature", "from": "ALPHA", "board": "FEATURES"}, ""),
        ]

    def assert_cash(self, text, marker):
        self.assertEqual(text.count(marker), 1)
        for product in PRODUCTS:
            self.assertIn("./" + product, text)
        self.assertNotIn("buy.stripe.com", text)

    def test_long_id_digest_preserves_cash_pr_count_and_utf8_budget(self):
        (self.root / "pulse.json").write_text(json.dumps({"seq": 100, "post_count": 9000}))
        (self.root / "builds.json").write_text(json.dumps({"n_open_prs": 3}))
        rows = [{"id": "é" * 900 + str(i)} for i in range(5)]
        for _ in range(2):
            text = llms_txt.write_change_rate(
                rows, "2026-09-05T02:00:00Z", head="a" * 40,
                n_tips=12, p_new=0, root=str(self.root),
            )
            self.assert_cash(text, "## Live cash")
            self.assertLessEqual(len(text.encode("utf-8")), 2048)
            self.assertLessEqual(len((self.root / "change.md").read_bytes()), 2048)
            self.assertIn("newest (truncated)", text)
            self.assertEqual(text.count("RATE p/ "), 1)
            self.assertIn("RATE prs open=3", text)
            self.assertIn("RATE peers open-branches=12", text)
            self.assertIn("RATE pulse seq=100", text)
            self.assertIn("## CITE", text)
            self.assertEqual((self.root / "change.md").read_text(encoding="utf-8"), text)

    def test_delta_rebuild_restores_cash_and_keeps_claim_data(self):
        previous = None
        for _ in range(2):
            data = hub_pages.rebuild_delta(self.mod, self.rows)
            page = (self.root / "delta.html").read_text(encoding="utf-8")
            self.assert_cash(page, 'id="live-cash"')
            self.assertIn("<h1>Delta</h1>", page)
            self.assertIn('<nav>existing doors</nav>', page)
            self.assertIn('id="delta-claim"', page)
            self.assertEqual(data["claims"]["ALPHA"]["n"], 1)
            self.assertEqual(data["claims"]["ALPHA"]["since"][0]["id"], "new-salon")
            self.assertEqual(data["claims"]["ALPHA"]["mine"][0]["id"], "new-feature")
            self.assertEqual(json.loads((self.root / "delta.json").read_text()), data)
            if previous is not None:
                self.assertEqual(page, previous)
            previous = page

    def test_lane_rebuild_restores_features_cash_and_preserves_other_lanes(self):
        previous = None
        for _ in range(2):
            data = hub_pages.rebuild_lanes(self.mod, self.rows)
            page = (self.root / "features.html").read_text(encoding="utf-8")
            self.assert_cash(page, 'id="live-cash"')
            self.assertIn("<h1>FEATURES</h1>", page)
            self.assertIn('data-lane="FEATURES" data-limit="12" data-head="1"', page)
            self.assertIn('name="from"', page)
            self.assertEqual(data["features"]["n"], 1)
            self.assertEqual(data["features"]["posts"][0]["id"], "new-feature")
            self.assertEqual(data["salon"]["n"], 1)
            self.assertEqual(json.loads((self.root / "lanes.json").read_text()), data)
            self.assertNotIn('id="live-cash"', (self.root / "salon.html").read_text())
            if previous is not None:
                self.assertEqual(page, previous)
            previous = page


if __name__ == "__main__":
    unittest.main()
