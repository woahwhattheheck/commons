"""llms.txt Commercial maps agent-rescue to $29 Autopsy, not Survival ladder."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class QuillLlmsAutopsyCommercialTests(unittest.TestCase):
    def test_autopsy_29_on_agent_rescue(self):
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn(
            "[$29 Agent Failure Autopsy](https://woahwhattheheck.github.io/commons/agent-rescue.html)",
            text,
        )

    def test_survival_not_on_agent_rescue(self):
        text = LLMS.read_text(encoding="utf-8")
        self.assertNotIn(
            "[$2,500 same-day crash-resume proof](https://woahwhattheheck.github.io/commons/agent-rescue.html)",
            text,
        )
        self.assertNotIn(
            "[$15,000 five-day recovery sprint](https://woahwhattheheck.github.io/commons/agent-rescue.html)",
            text,
        )
        self.assertIn(
            "revenue/production_survival/README.md",
            text,
        )
        # agent-rescue appears once for Autopsy, not for Survival prices
        commercial = text.split("## Commercial", 1)[1].split("## Fresh", 1)[0]
        self.assertEqual(
            commercial.count("agent-rescue.html"),
            1,
            "agent-rescue.html must appear only for Autopsy in Commercial",
        )


if __name__ == "__main__":
    unittest.main()
