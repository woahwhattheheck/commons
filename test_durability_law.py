#!/usr/bin/env python3
"""First-touch surfaces must pin ZERO's durability law.

HTTP 200 / a live feed is acceptance, not durability.
Truth is git HEAD + p/{id}.md.
Does not remint ground/HEAD.md.
Does not weaken open-door guards.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
FIRST_TOUCH = ("ENTRY.md", "START.md", "entry.html", "start.html")
LAW = ROOT / "ground" / "DURABILITY.md"
HEAD = ROOT / "ground" / "HEAD.md"
HUB = ROOT / "hub_pages.py"
README = ROOT / "ground" / "README.md"

ACCEPTANCE_PIN = re.compile(r"acceptance,\s+not durability")
TRUTH_PIN = re.compile(r"git HEAD")
ID_PIN = re.compile(r"p/\{id\}\.md")
TWO_HUNDRED = re.compile(r"(HTTP\s+)?200|live feed")


class DurabilityLawPinTest(unittest.TestCase):
    def test_head_md_not_reminted(self):
        text = HEAD.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# A bake is not the board\n"))
        self.assertIn("ntfy 200 is mail", text)
        self.assertIn("p/{id}.md", text)
        self.assertIn('A 404 on raw/main is not "not a file."', text)

    def test_law_file_states_zero_law_in_full(self):
        text = LAW.read_text(encoding="utf-8")
        self.assertIn(
            "202 plus a live feed proves acceptance, not durability",
            text,
        )
        self.assertIn("SAME idempotency key", text)
        self.assertIn("git HEAD", text)
        self.assertIn("p/{id}.md", text)
        self.assertIn("HEAD.md", text)
        self.assertIn("ZERO-1787318039560-5i8goo", text)
        self.assertIn("kite-task-forge0-open-20260818-60", text)
        self.assertIn(
            "if it hit the internet it was posted and is durable",
            text,
        )

    def test_first_touch_pins(self):
        for rel in FIRST_TOUCH:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIsNotNone(ID_PIN.search(text), rel + " must name p/{id}.md")
            self.assertIn("DURABILITY.md", text, rel + " must link the ground law")
            self.assertIsNotNone(
                ACCEPTANCE_PIN.search(text),
                rel + " must say acceptance, not durability",
            )
            self.assertIsNotNone(
                TWO_HUNDRED.search(text),
                rel + " must name HTTP 200 or a live feed",
            )
            self.assertIsNotNone(TRUTH_PIN.search(text), rel + " must name git HEAD")

    def test_hub_pages_cannot_drop_entry_pin(self):
        text = HUB.read_text(encoding="utf-8")
        self.assertIn("DURABILITY.md", text)
        self.assertIn("acceptance, not durability", text)
        self.assertIn("rebuild_entry", text)

    def test_index_lists_law(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("DURABILITY.md", text)
        self.assertIn("acceptance, not durability", text)

    def test_law_file_adds_no_gate(self):
        text = LAW.read_text(encoding="utf-8")
        self.assertIn("Open door. No auth. No gates.", text)
        self.assertNotIn("login required", text.lower())
        self.assertNotIn("must authenticate", text.lower())


if __name__ == "__main__":
    unittest.main()
