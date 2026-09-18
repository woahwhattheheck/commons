"""STAMP Larger-fixed tail on remaining Live-cash doors."""
from __future__ import annotations
import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parent
DOORS=['chargeback-evidence-readiness.html', 'discount-concession-leakage.html', 'hotel-room-turn-evidence.html', 'late-cancel-noshow-fee-leakage.html', 'organabio-multisite-donor-coa.html', 'ptl-controlled-sample-order-preflight.html', 'sc-labs-multistate-coa-rule-version-gate.html']
class T(unittest.TestCase):
    def test_each(self):
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
