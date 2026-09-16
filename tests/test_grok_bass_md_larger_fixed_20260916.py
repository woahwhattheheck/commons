from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "grok-bass-md-larger-fixed-20260916-01"
FILES = {
    "AGENT_VIEW.md": "",
    "analysis/titan-v3-e11-last-usable-absorption/README.md": "../../",
    "ci/WORKFLOW_SURFACE.md": "../",
    "ci/actions_execution_truth/README.md": "../../",
    "commercial/alcorn-rfp-5588/README.md": "../../",
    "commercial/alcorn-rfp-5588/workshare.md": "../../",
    "commercial/cpca-hccn-connect/README.md": "../../",
    "commercial/cpca-hccn-connect/response_outline.md": "../../",
}


class T(unittest.TestCase):
    def test_bass_md_larger_fixed(self):
        for rel, prefix in FILES.items():
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("Live cash", text)
                self.assertIn(f"{prefix}agent-rescue.html", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn(f"{prefix}diagnostic.html", text)
                self.assertIn(f"{prefix}commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertIn(CLAIM, text)


if __name__ == "__main__":
    unittest.main()
