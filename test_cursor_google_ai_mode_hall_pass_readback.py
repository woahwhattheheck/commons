#!/usr/bin/env python3
"""Pin unique-pack readback of Google AI Mode hall-pass leftover. Do not remint leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-google-ai-mode-hall-pass-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-google-ai-mode-hall-pass-20260902-01.md"
SKILL = ROOT / ".agents/skills/google-ai-mode-hall-pass/SKILL.md"
TOKEN = ROOT / "ground/tokens/google-ai-mode-hall-pass.md"

KEEP = {
    "p/cursor-google-ai-mode-hall-pass-20260902-01.md": "4bb8b78d",
    "test_google_ai_mode_hall_pass.py": "9fe45498",
    "p/codex-google-research-routing-notice-20260902-01.md": "a8fc95c1",
    "p/codex-google-research-grok-automation-resource-delta-20260902-01.md": "0ba4c667",
    "p/codex-google-research-resource-delta-landed-20260902-01.md": "ee08c28d",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "a3934e26",
    "ground/WIRE_SUPER_MCP.md": "aecb9b00",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "p/cursor-big-huge-commerce-agents-readback-20260902-01.md": "2a5ce894",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "hub_pages.py": "c4e9198a",
    "door.js": "5bc431b1",
    "ground/OWNER_NOW.md": "0a574d94",
}

HISTORICAL_TREE = "dc5455bf2894fa705bf57a4510ceee0119a6c729"
HISTORICAL_LIVE_FILES = {
    ".agents/skills/google-ai-mode-hall-pass/SKILL.md": "bb22f950",
    "ground/tokens/google-ai-mode-hall-pass.md": "f730edc2",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def git_blob_at(tree: str, rel: str) -> str:
    line = subprocess.check_output(
        ["git", "ls-tree", tree, "--", rel], text=True
    ).strip()
    return line.split()[2] if line else ""


class TestCursorGoogleAiModeHallPassReadback(unittest.TestCase):
    def test_keep_leftover_skill_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_historical_skill_blobs_remain_at_recorded_tree(self) -> None:
        for rel, prefix in HISTORICAL_LIVE_FILES.items():
            blob = git_blob_at(HISTORICAL_TREE, rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"historical {rel}: want {prefix} got {blob[:8]}",
            )

    def test_live_skill_distinguishes_route_from_verified_claims(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        token = TOKEN.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        joined = skill + "\n" + token
        self.assertIn("www.google.com", joined)
        self.assertIn("no login", joined.lower())
        self.assertIn("AI Mode", joined)
        self.assertIn("Google tool calls", joined)
        self.assertIn("Intended feature, not a hack", joined)
        self.assertIn("Bryce/WIRE attribution", skill)
        self.assertIn("signed-in session cannot establish signed-out availability", skill)
        self.assertIn("No run here establishes universal access", skill)
        self.assertIn("If no sources or search result appear", skill)
        self.assertIn("ASTRA reported a measured browser run", token)
        self.assertIn("$147 sale price", token)
        self.assertIn("$689 value/struck figure", token)
        self.assertIn("one-payment wording", token)
        self.assertIn("Adobe Illustrator/InDesign", token)
        self.assertIn("Canva/Adobe Express compatibility", token)
        for keep in (
            "codex-google-research-routing-notice-20260902-01",
            "codex-google-research-grok-automation-resource-delta-20260902-01",
            "codex-google-research-resource-delta-landed-20260902-01",
        ):
            self.assertIn(keep, skill)
            self.assertIn(keep, token)
        self.assertIn("1788388806.376349", leftover)
        self.assertIn("Did **not** remint", leftover)
        self.assertNotIn("buy.stripe.com", skill)

    def test_leftover_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_google_ai_mode_hall_pass.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 8 tests", leftover.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-google-ai-mode-hall-pass-readback-20260902-01", text)
        self.assertIn("97070cc2e", text)
        self.assertIn("4bb8b78d", text)
        self.assertIn("ecc43da1", text)
        self.assertIn("9fe45498", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("F0BUL9V9Z34", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
