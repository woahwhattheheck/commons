import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT = (ROOT / "ground" / "HEAD.md").read_text()


class TestSpyGroundHeadLiveCash(unittest.TestCase):
    def test_live_cash_section(self):
        self.assertIn("## Live cash", TEXT)
        self.assertIn("agent-rescue.html", TEXT)
        self.assertIn("dealer-service-lead-rescue.html", TEXT)
        self.assertIn("referral-intake-completeness.html", TEXT)
        self.assertIn("repair-booking-preflight.html", TEXT)
        self.assertIn("plant-downtime-handoff.html", TEXT)


if __name__ == "__main__":
    unittest.main()
