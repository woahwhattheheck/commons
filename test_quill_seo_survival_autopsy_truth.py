"""SEO pages: agent-rescue nav is Autopsy $29; Survival not via agent-rescue."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
PAGES = (
    "agentic-production-failure.html",
    "agent-runaway-cost.html",
    "ai-agent-stop-button.html",
    "distro.html",
)


class QuillSeoSurvivalAutopsyTruthTests(unittest.TestCase):
    def test_nav_autopsy_not_agent_survival(self):
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(
                    '<a href="./agent-rescue.html">Agent Failure Autopsy · $29</a>',
                    text,
                )
                self.assertNotIn(
                    '<a href="./agent-rescue.html">agent survival</a>',
                    text,
                )

    def test_seo_pages_point_survival_to_readme(self):
        for name in (
            "agentic-production-failure.html",
            "agent-runaway-cost.html",
            "ai-agent-stop-button.html",
        ):
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("revenue/production_survival/README.md", text)
                self.assertNotIn(
                    '<a href="./agent-rescue.html">agent survival page</a>',
                    text,
                )
                self.assertIn("do not use agent-rescue.html for Survival", text)
                # Stripe plink unchanged
                self.assertIn(
                    "https://buy.stripe.com/8x25kC3Ot9fj5ep1Oy43S0a",
                    text,
                )


if __name__ == "__main__":
    unittest.main()
