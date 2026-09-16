"""grok-experience-wiki-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on wiki remint."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "grok-experience-wiki-keep-larger-fixed-20260916-01"
WIKI = [
    "experience/wiki/index.md",
    "experience/wiki/patterns/change-generator-with-generated-output.md",
    "experience/wiki/patterns/publish-discovery-before-interaction.md",
    "experience/wiki/patterns/share-operation-identity-across-carriers.md",
]


class TestGrokExperienceWikiKeepLargerFixed2026091601(unittest.TestCase):
    def test_helper_emits_nested_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        from host.experience_compiler import live_cash_markdown, WIKI_DIR, PATTERN_DIR
        index = live_cash_markdown(WIKI_DIR / "index.md")
        pattern = live_cash_markdown(PATTERN_DIR / "x.md")
        self.assertIn("## Live cash", index)
        self.assertIn("../../agent-rescue.html", index)
        self.assertIn("Larger fixed engagements", index)
        self.assertIn("../../diagnostic.html", index)
        self.assertIn("../../commercial.html", index)
        self.assertIn("../../../diagnostic.html", pattern)
        self.assertIn("../../../commercial.html", pattern)
        self.assertNotIn("buy.stripe.com", index)
        self.assertNotIn("buy.stripe.com", pattern)

    def test_tip_wiki_has_autopsy_and_larger(self):
        for rel in WIKI:
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("agent-rescue.html", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("diagnostic.html", text, rel)
            self.assertIn("commercial.html", text, rel)
            self.assertNotIn("buy.stripe.com", text, rel)

    def test_compile_keeps_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        from host import experience_compiler as compiler
        outputs = compiler.compile_outputs(compiler.load_records())
        index = outputs[compiler.WIKI_DIR / "index.md"]
        self.assertEqual((ROOT / "experience/wiki/index.md").read_text(encoding="utf-8"), index)
        self.assertIn("Larger fixed engagements", index)
        self.assertIn("../../diagnostic.html", index)
        self.assertNotIn("buy.stripe.com", index)

    def test_product_pages_exist(self):
        for name in (
            "agent-rescue.html",
            "dealer-service-lead-rescue.html",
            "diagnostic.html",
            "commercial.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
