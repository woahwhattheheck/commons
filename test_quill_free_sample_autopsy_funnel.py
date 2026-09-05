"""free-sample.html points agent-rescue at live $29 Autopsy, not $2500 survival."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "free-sample.html"


class QuillFreeSampleAutopsyFunnelTests(unittest.TestCase):
    def test_nav_names_autopsy_not_agent_survival(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn(
            '<a href="./agent-rescue.html">Agent Failure Autopsy · $29</a>',
            text,
        )
        self.assertNotIn(">agent survival</a>", text)

    def test_agent_eval_insert_is_autopsy_29(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("Agent Failure Autopsy · $29", text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("no dedicated Commons HTML", text)
        self.assertIn("revenue/production_survival/README.md", text)
        self.assertNotIn("same-day-agent-survival-proof is the $2,500", text)
        # Must not sell Survival price as the agent-rescue page product.
        self.assertNotIn(
            "SKU `same-day-agent-survival-proof` is the $2,500 same-day wedge",
            text,
        )


if __name__ == "__main__":
    unittest.main()
