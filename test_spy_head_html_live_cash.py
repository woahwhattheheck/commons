import unittest
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "head.html").read_text()


class TestSpyHeadHtmlLiveCash(unittest.TestCase):
    def test_live_cash(self):
        self.assertIn('id="live-cash"', TEXT)
        self.assertIn("agent-rescue.html", TEXT)
        self.assertIn("dealer-service-lead-rescue.html", TEXT)
        self.assertNotIn("337 NO", TEXT)


if __name__ == "__main__":
    unittest.main()
