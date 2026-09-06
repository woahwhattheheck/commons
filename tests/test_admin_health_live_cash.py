from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def test(self):
        text = (ROOT / "health.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        for href in ("agent-rescue.html","dealer-service-lead-rescue.html","referral-intake-completeness.html","repair-booking-preflight.html","plant-downtime-handoff.html"):
            self.assertIn(href, text)
if __name__ == "__main__":
    unittest.main()
