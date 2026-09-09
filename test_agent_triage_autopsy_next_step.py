"""Free triage paid-next-step points at live $29 Autopsy, not stale $2,500 survival."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "agent-triage.html"
JS = ROOT / "agent-triage.js"


class AgentTriageAutopsyNextStepTests(unittest.TestCase):
    def test_html_nav_names_autopsy_not_same_day_proof(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("Agent Failure Autopsy", text)
        self.assertIn("agent-rescue.html", text)
        self.assertNotIn(">same-day proof<", text)

    def test_js_severe_offer_is_autopsy_29(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('id: "agent-failure-autopsy-29"', text)
        self.assertIn('name: "Agent Failure Autopsy"', text)
        self.assertIn('price: "$29"', text)
        self.assertIn('href: "./agent-rescue.html"', text)
        self.assertNotIn("same-day-agent-survival-proof", text)
        self.assertNotIn("$2,500", text)


if __name__ == "__main__":
    unittest.main()
