from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "discount-concession-leakage.html",
    "chargeback-evidence-readiness.html",
    "hotel-room-turn-evidence.html",
    "late-cancel-noshow-fee-leakage.html",
]


class T(unittest.TestCase):
    def test_larger_on_all(self):
        for name in FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Larger fixed engagements", text, name)
            self.assertIn("./diagnostic.html", text, name)
            self.assertIn("./commercial.html", text, name)
            self.assertIn('id="larger-fixed"', text, name)


if __name__ == "__main__":
    unittest.main()
