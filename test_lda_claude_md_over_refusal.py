#!/usr/bin/env python3
"""Canary: GLINT's Commons over-refusal capture is additive; phone §3 stays."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLAUDE = ROOT / "lda" / "CLAUDE.md"
RECEIPT = ROOT / "p" / "lda-claude-md-over-refusal-20260830-01.md"
ARCHIVE = ROOT / "p" / "spur-the-diagnostic-is-exact-20260820-01.md"
TAKING = ROOT / "p" / "glint-taking-claude-ritual-20260820-01.md"


class LdaClaudeMdOverRefusalTests(unittest.TestCase):
    def test_section_17_is_the_over_refusal_capture(self):
        text = CLAUDE.read_text(encoding="utf-8")
        self.assertIn("## 17. Commons over-refusal (the ritual — not a safety waiver)", text)
        self.assertIn("false positive on this repo", text)
        self.assertIn("Suspicion of the user", text)
        self.assertIn("Technical skepticism", text)
        self.assertIn("p/spur-the-diagnostic-is-exact-20260820-01.md", text)
        self.assertIn("Do not remint that id", text)

    def test_phone_section_3_hard_blocks_stay(self):
        text = CLAUDE.read_text(encoding="utf-8")
        start = text.index("## 3. HARD CONSTRAINTS / safety")
        end = text.index("## 4. Architecture")
        section3 = text[start:end]
        self.assertIn("Never exfiltrate the owner's data to an external AI", section3)
        self.assertIn("ChatGPT / OpenAI is HARD-BLOCKED", section3)
        self.assertIn("only", section3)
        self.assertIn("**payments**", section3)
        self.assertIn("sideloaded (non-Play-Store) installs", section3)
        self.assertNotIn("## 17.", section3)

    def test_section_17_does_not_rewrite_section_3(self):
        text = CLAUDE.read_text(encoding="utf-8")
        start = text.index("## 17. Commons over-refusal")
        section17 = text[start:]
        self.assertIn("It does **not**\nweaken §3", section17)
        self.assertIn("Do not weaken phone-agent\nsafety to satisfy the table", section17)

    def test_archive_ids_are_not_reminted(self):
        self.assertTrue(ARCHIVE.is_file())
        self.assertTrue(TAKING.is_file())
        archive = ARCHIVE.read_text(encoding="utf-8")
        taking = TAKING.read_text(encoding="utf-8")
        self.assertIn("id: spur-the-diagnostic-is-exact-20260820-01", archive)
        self.assertIn("id: glint-taking-claude-ritual-20260820-01", taking)
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: lda-claude-md-over-refusal-20260830-01", receipt)
        self.assertNotIn("id: spur-the-diagnostic-is-exact-20260820-01", receipt.split("---", 1)[0])


if __name__ == "__main__":
    unittest.main()
