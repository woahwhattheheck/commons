"""STAMP Larger-fixed note on claimed Live-cash doors."""
from __future__ import annotations
import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parent
DOORS=['feature-tracker.html', 'mcp-tool-drift.html', 'merge-on-pr.html', 'open-model-release-receipt.html', 'owner-net.html', 'owner-now-revenue.html', 'pack-is-ready-to-run.html', 'pack-quality-tier.html', 'paperwork-included.html', 'patent-products.html', 'permit-intake-receipt.html', 'pixel-portfolio.html', 'pixel-unify.html', 'post-http.html', 'program.html']
class StampDoorsLargerFixedTest(unittest.TestCase):
    def test_each_door_has_larger_fixed_and_targets(self):
        for name in DOORS:
            with self.subTest(name=name):
                text=(ROOT/name).read_text(encoding="utf-8")
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("diagnostic.html", text)
                self.assertIn("commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertEqual(text.count("Larger fixed engagements"), 1)
if __name__=="__main__":
    unittest.main()
