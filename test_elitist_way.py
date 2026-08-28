#!/usr/bin/env python3
"""THE ELITIST WAY is short-prompt dispatch on existing surfaces, not a second ship-loop."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / ".agents" / "skills" / "elitist-way" / "SKILL.md"
CARD = ROOT / "ground" / "ELITIST_WAY.md"
TOKEN = ROOT / "ground" / "tokens" / "elitist-way.md"
MANUAL = ROOT / "skills" / "MANUAL.md"
MANIFEST = ROOT / "skills.json"
CHECK = ROOT / "skills" / "check.py"


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    data = {}
    key = None
    for line in text[4:end].splitlines():
        if line.startswith("  ") and key == "description":
            data[key] = (data.get(key, "") + " " + line.strip()).strip()
            continue
        if line.startswith("  ") and key == "metadata":
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, val = match.group(1), match.group(2).strip()
        if val in {">", "|"}:
            data[key] = ""
            continue
        data[key] = val.strip("\"'")
    return data


class ElitistWayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.card = CARD.read_text(encoding="utf-8")
        cls.token = TOKEN.read_text(encoding="utf-8")
        cls.manual = MANUAL.read_text(encoding="utf-8")
        cls.registry = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.owned = "\n".join([cls.skill, cls.card, cls.token])

    def test_required_files_exist(self):
        self.assertTrue(SKILL.is_file(), SKILL)
        self.assertTrue(CARD.is_file(), CARD)
        self.assertTrue(TOKEN.is_file(), TOKEN)

    def test_frontmatter_matches_directory(self):
        meta = frontmatter(self.skill)
        self.assertEqual(meta["name"], "elitist-way")
        self.assertEqual(SKILL.parent.name, meta["name"])
        desc = meta.get("description") or ""
        self.assertGreaterEqual(len(desc), 1)
        self.assertLessEqual(len(desc), 1024)
        self.assertIn("END RESULT", desc)
        self.assertIn("Grok Build", desc)

    def test_catalog_and_manual_registration(self):
        matches = [row for row in self.registry["skills"] if row["id"] == "elitist-way"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0]["job"],
            "launch a Grok Build / Heavy lane from a thinking model",
        )
        self.assertEqual(matches[0].get("token"), "ground/tokens/elitist-way.md")
        self.assertIn(
            "[elitist-way](../.agents/skills/elitist-way/SKILL.md)",
            self.manual,
        )
        ids = [row["id"] for row in self.registry["skills"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("gpt-grok-ship-loop", ids)
        self.assertIn("review-and-ship", ids)
        self.assertIn("grok-web-commons", ids)

    def test_not_a_second_ship_loop(self):
        for blob in (self.skill, self.card, self.token):
            self.assertIn("not a second ship-loop", blob.lower())
            self.assertIn("gpt-grok-ship-loop", blob)
        self.assertIn("review-and-ship", self.skill)
        self.assertIn("grok-web-commons", self.skill)
        self.assertNotIn("schema/build-contract.schema.json", self.owned)
        self.assertNotIn("scripts/ship_loop.py", self.owned)

    def test_copy_ready_prompt_and_constraints(self):
        self.assertIn("## Copy-ready prompt", self.card)
        self.assertIn("## BRYCE'S CONSTRAINTS", self.card)
        for marker in (
            "open public participation",
            "no auth",
            "no fabricated completion",
            "no secret exposure",
            "no force",
            "no walking on eggshells",
            "no code-style rules invented by GPT",
        ):
            self.assertIn(marker, self.card)
        self.assertIn("Leave design to Grok", self.card)
        self.assertIn("GitHub main is the completion ledger", self.card)

    def test_route_is_grok_com_not_cursor(self):
        self.assertIn("Not Cursor", self.skill)
        self.assertIn("Not Grokbot", self.skill)
        self.assertIn("grok.com", self.skill.lower())
        self.assertNotIn("You are Grokbot", self.owned)
        self.assertNotIn("Sent using Cursor", self.owned)

    def test_open_door_and_unseated(self):
        self.assertIn("Blank `from=` lands as `UNSEATED`", self.owned)
        self.assertIn("Possessing the link", self.owned)
        self.assertIn("never a gate", self.skill)
        lower = self.owned.lower()
        self.assertNotIn("authentication required", lower)
        self.assertNotIn("authorization required", lower)
        self.assertNotIn("permission denied", lower)

    def test_compose_pointers_on_review_and_ship_and_grok_web_commons(self):
        review = (ROOT / ".agents" / "skills" / "review-and-ship" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        grokweb = (ROOT / ".agents" / "skills" / "grok-web-commons" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[elitist-way](../elitist-way/SKILL.md)", review)
        self.assertIn("Do not mint a second ship-loop", review)
        self.assertIn("integration and current-main readback", review)
        self.assertIn("[elitist-way](../elitist-way/SKILL.md)", grokweb)
        self.assertIn("Do not mint a second ship system", grokweb)
        self.assertIn("grok.com connector road", grokweb)

    def test_skills_check_receipt_passes(self):
        result = subprocess.run(
            ["python3", str(CHECK)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("PASS"), result.stdout)


if __name__ == "__main__":
    unittest.main()
