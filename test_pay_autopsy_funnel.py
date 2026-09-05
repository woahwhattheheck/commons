"""pay.html surfaces the live $29 Agent Failure Autopsy checkout."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
PAY = ROOT / "pay.html"
PLINK = "4gM9AS3Ot8bfeOZ78S43S0g"


class PayAutopsyFunnelTests(unittest.TestCase):
    def test_pay_page_surfaces_autopsy_checkout(self):
        text = PAY.read_text(encoding="utf-8")
        self.assertIn("$29", text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("Agent Failure Autopsy", text)
        self.assertIn(PLINK, text)
        self.assertIn("id=\"autopsy-cash\"", text)


if __name__ == "__main__":
    unittest.main()
