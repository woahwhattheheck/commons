"""llms.txt Commercial maps agent-rescue to $29 Autopsy, not Survival ladder."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import llms_txt

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

    def test_actual_bake_preserves_the_corrected_commercial_section(self):
        rows = [{"id": "current-post", "from": "TEST", "body": "Current post remains."}]
        with tempfile.TemporaryDirectory() as directory, patch.multiple(
            llms_txt,
            ROOT=directory,
            rows_from_git=lambda: rows,
            git_head=lambda: "1" * 40,
            branch_tips=lambda: [],
        ), patch.object(llms_txt.read_mesh, "publish") as publish:
            self.assertEqual(llms_txt.main(publish_mesh=False), 0)
            generated = (Path(directory) / "llms.txt").read_text(encoding="utf-8")
        expected = LLMS.read_text(encoding="utf-8").split("## Commercial", 1)[1].split("## Fresh", 1)[0]
        actual = generated.split("## Commercial", 1)[1].split("## Fresh", 1)[0]
        self.assertEqual(actual, expected)
        self.assertIn("current-post", generated)
        self.assertIn("## Doors", generated)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
