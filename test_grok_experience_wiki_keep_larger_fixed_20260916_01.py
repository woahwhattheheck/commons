"""grok-experience-wiki-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on wiki remint."""
from __future__ import annotations

import unittest
from pathlib import Path

import host.experience_compiler as compiler

ROOT = Path(__file__).resolve().parent
CLAIM = "grok-experience-wiki-keep-larger-fixed-20260916-01"
WIKI = [
    "experience/wiki/index.md",
    "experience/wiki/patterns/change-generator-with-generated-output.md",
    "experience/wiki/patterns/publish-discovery-before-interaction.md",
    "experience/wiki/patterns/share-operation-identity-across-carriers.md",
]
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
    "diagnostic.html",
    "commercial.html",
]


class TestGrokExperienceWikiKeepLargerFixed2026091601(unittest.TestCase):
    def test_compiler_emits_autopsy_and_larger(self):
        index_md = compiler.live_cash_markdown(compiler.WIKI_DIR / "index.md")
        self.assertIn("[$29 Autopsy checkout](../../agent-rescue.html)", index_md)
        self.assertIn("$199", index_md)
        self.assertIn("Larger fixed engagements", index_md)
        self.assertIn("../../diagnostic.html", index_md)
        self.assertIn("../../commercial.html", index_md)
        self.assertIn("$12,000", index_md)
        self.assertIn("$30,000", index_md)
        self.assertNotIn("buy.stripe.com", index_md)

        pattern_md = compiler.live_cash_markdown(
            compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"
        )
        self.assertIn("[$29 Autopsy checkout](../../../agent-rescue.html)", pattern_md)
        self.assertIn("../../../diagnostic.html", pattern_md)
        self.assertIn("../../../commercial.html", pattern_md)
        self.assertNotIn("buy.stripe.com", pattern_md)

    def test_tip_wiki_has_autopsy_and_larger(self):
        for rel in WIKI:
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("agent-rescue.html", text, rel)
            self.assertIn("$29", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("diagnostic.html", text, rel)
            self.assertIn("commercial.html", text, rel)
            self.assertIn("$12,000", text, rel)
            self.assertIn("$30,000", text, rel)
            self.assertNotIn("buy.stripe.com", text, rel)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_compile_check_keeps_larger_and_no_drift(self):
        outputs = compiler.compile_outputs(compiler.load_records())
        self.assertEqual([], compiler.check_outputs(outputs))
        index = outputs[compiler.WIKI_DIR / "index.md"]
        pattern = outputs[
            compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"
        ]
        self.assertIn("Larger fixed engagements", index)
        self.assertIn("../../diagnostic.html", index)
        self.assertIn("../../commercial.html", index)
        self.assertIn("Larger fixed engagements", pattern)
        self.assertIn("../../../diagnostic.html", pattern)
        self.assertIn("../../../commercial.html", pattern)
        self.assertNotIn("buy.stripe.com", index)
        self.assertNotIn("buy.stripe.com", pattern)
        for rel in WIKI:
            path = ROOT / rel
            compiled = outputs[path]
            self.assertEqual(path.read_text(encoding="utf-8"), compiled, rel)


if __name__ == "__main__":
    unittest.main()
