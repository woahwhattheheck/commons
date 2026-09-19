from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class AgentSurvivalDiscoveryTest(unittest.TestCase):
    def test_readme_surfaces_scope_first_agent_failure_diagnostic(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        offer = readme.index("**Production agent failing?**")
        contract = readme.index("**One-link contract.**")

        self.assertLess(offer, contract)
        self.assertIn("agent-triage.html", readme[offer:contract])
        self.assertIn("before payment", readme[offer:contract])

    def test_home_keeps_retired_autopsy_offer_out(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="door-hub"', home)
        self.assertNotIn('id="agent-failure-diagnostic-offer"', home)
        self.assertNotIn('href="./agent-rescue.html"', home)
        self.assertNotIn("4gM9AS3Ot8bfeOZ78S43S0g", home)


if __name__ == "__main__":
    unittest.main()
