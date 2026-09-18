"""Hermetic: docs Live cash shelves KEEP Larger fixed."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PATHS = [
    "docs/paid-opportunities.md",
    "docs/GROKCOM_REVENUE_ORCHESTRATOR.md",
    "docs/TITAN_HANDS.md",
    "docs/TITAN_HANDS_PEERS.md",
    "CRAWLERS.md",
    "dest/LIVE_MOUTHS.md",
]
RECEIPT = ROOT / "p" / "newbot-docs-larger-fixed-20260916-24.md"


class DocsLargerFixedTests(unittest.TestCase):
    def test_larger_on_each(self) -> None:
        for rel in PATHS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("Larger fixed", text, rel)
            self.assertIn("diagnostic.html", text, rel)
            self.assertIn("commercial.html", text, rel)

    def test_receipt(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("newbot-docs-larger-fixed-20260916-24", text)


if __name__ == "__main__":
    unittest.main()
