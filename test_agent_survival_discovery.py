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

    def test_home_surfaces_scope_first_agent_failure_diagnostic_before_door_grid(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")

        offer = home.index('id="agent-failure-diagnostic-offer"')
        door_grid = home.index('id="door-hub"')

        self.assertLess(offer, door_grid)
        self.assertIn('href="./agent-triage.html"', home[offer:door_grid])
        self.assertIn("Build the failure packet", home[offer:door_grid])


if __name__ == "__main__":
    unittest.main()
