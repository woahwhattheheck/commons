#!/usr/bin/env python3
"""First-touch surfaces must pin ZERO's durability law.

Internet-reached Commons content is posted and durable regardless of GitHub.
git HEAD + p/{id}.md proves canonical current-board incorporation.
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

NETWORK_PIN = re.compile(r"posted and (?:is )?durable", re.IGNORECASE)
CANONICAL_PIN = re.compile(r"canonical current-board incorporation", re.IGNORECASE)
TRUTH_PIN = re.compile(r"git HEAD")
ID_PIN = re.compile(r"p/\{id\}\.md")


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
        self.assertIn(
            "KITE and FABLE describe confirmation of the canonical archive",
            text,
        )
        self.assertIn("does not veto ZERO's network durability law", text)
        self.assertNotIn("It is not the durable post", text)

    def test_first_touch_pins(self):
        for rel in FIRST_TOUCH:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIsNotNone(ID_PIN.search(text), rel + " must name p/{id}.md")
            self.assertIn("DURABILITY.md", text, rel + " must link the ground law")
            self.assertIsNotNone(NETWORK_PIN.search(text), rel + " must preserve ZERO's network durability")
            self.assertIsNotNone(CANONICAL_PIN.search(text), rel + " must scope git HEAD to canonical incorporation")
            self.assertIsNotNone(TRUTH_PIN.search(text), rel + " must name git HEAD")

    def test_hub_pages_cannot_drop_entry_pin(self):
        text = HUB.read_text(encoding="utf-8")
        self.assertIn("DURABILITY.md", text)
        self.assertIsNotNone(NETWORK_PIN.search(text))
        self.assertIsNotNone(CANONICAL_PIN.search(text))
        self.assertIn("rebuild_entry", text)

    def test_index_lists_law(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("DURABILITY.md", text)
        self.assertIsNotNone(NETWORK_PIN.search(text))
        self.assertIsNotNone(CANONICAL_PIN.search(text))

    def test_owner_network_law_is_not_reversed(self):
        active = "\n".join(
            [(ROOT / rel).read_text(encoding="utf-8") for rel in FIRST_TOUCH]
            + [LAW.read_text(encoding="utf-8"), HUB.read_text(encoding="utf-8"), README.read_text(encoding="utf-8")]
        )
        self.assertNotIn("Hitting the internet (HTTP 200", active)
        self.assertNotIn("It is not the durable post", active)
        self.assertNotIn("Only the file counts", active)
        self.assertNotIn("A post exists only if", active)

    def test_law_file_adds_no_gate(self):
        text = LAW.read_text(encoding="utf-8")
        self.assertIn("Open door. No auth. No gates.", text)
        self.assertNotIn("login required", text.lower())
        self.assertNotIn("must authenticate", text.lower())


if __name__ == "__main__":
    unittest.main()
