"""reply-to-revenue.html nav labels agent-rescue as Autopsy $29."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "reply-to-revenue.html"


class QuillReplyLedgerAutopsyLabelTests(unittest.TestCase):
    def test_nav_autopsy_not_agent_survival(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn(
            '<a href="./agent-rescue.html">Agent Failure Autopsy · $29</a>',
            text,
        )
        self.assertNotIn(
            '<a href="./agent-rescue.html">agent survival</a>',
            text,
        )


if __name__ == "__main__":
    unittest.main()
