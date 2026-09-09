"""README fail ladder leads with Autopsy $29; Survival not on agent-rescue."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"


class QuillReadmeAutopsyFunnelTests(unittest.TestCase):
    def test_autopsy_29_first_cash_step(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("Agent Failure Autopsy · $29", text)
        self.assertIn(
            "https://woahwhattheheck.github.io/commons/agent-rescue.html",
            text,
        )
        self.assertLess(
            text.index("Agent Failure Autopsy · $29"),
            text.index("$2,500"),
        )

    def test_survival_not_sold_via_agent_rescue(self):
        text = README.read_text(encoding="utf-8")
        fail = text.split("**One-link contract.**", 1)[0]
        self.assertIn("revenue/production_survival/README.md", fail)
        self.assertIn("do not use agent-rescue.html for Survival", fail)
        # Old copy that sold Survival as the only next cash step after $199.
        self.assertNotIn(
            "A working $2,500\nsurvival proof is the next step only when the diagnosis calls for one.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
