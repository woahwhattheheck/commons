#!/usr/bin/env python3
"""Pin grok-build terminal leftover for PR 8348. Do not remint MCP GET / grounding door."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8348-terminal-20260902-01.md"
CURSOR = ROOT / "p/cursor-mcp-get-grounding-20260902-01.md"
TRACKER = ROOT / "p/grok-build-repair-tracker-mcp-get-20260902-01.md"

KEEP = {
    "grounding.html": "abb91caf",
    "api/mcp.py": "bc558a5f",
    "commons_mcp.py": "23996ca3",
    "test_mcp_get_open.py": "239564b9",
    "test_grounding_door.py": "ef9a7982",
    "p/cursor-mcp-get-grounding-20260902-01.md": "0bc79b8c",
    "p/grok-build-repair-tracker-mcp-get-20260902-01.md": "14760206",
    "hub_pages.py": "5ac12648",
    "features/registry/cursor-mcp-get-grounding-20260902-01.json": "2ad88f05",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8348Terminal(unittest.TestCase):
    def test_keep_mcp_get_and_grounding_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertTrue((ROOT / "grounding.html").is_file())
        page = (ROOT / "grounding.html").read_text(encoding="utf-8")
        self.assertIn("No login", page)
        self.assertIn("Possessing the link is authorization", page)
        self.assertNotIn('type="password"', page)
        core = json.loads(
            subprocess.check_output(
                [
                    "python3",
                    "-c",
                    "import json,commons_mcp as cm; print(json.dumps(cm.public_mcp_capability_map()))",
                ],
                cwd=ROOT,
                text=True,
            )
        )
        self.assertEqual(core["auth"], "none")
        self.assertTrue(core["open_door"])
        self.assertFalse(core["login"])
        self.assertFalse(core["oauth"])
        self.assertIsNone(core["session"])

    def test_receipt_cites_8348_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        cursor = CURSOR.read_text(encoding="utf-8")
        tracker = TRACKER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8348-terminal-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8348@9ebf05d098389c4d556dd849b95b11434e53329b",
            text,
        )
        self.assertIn("34e77be19456dbe0162ecc3b8301254af45d96f2", text)
        self.assertIn("abb91caf", text)
        self.assertIn("0bc79b8c", text)
        self.assertIn("14760206", text)
        self.assertIn("auth=none", text)
        self.assertIn("open_door=true", text)
        self.assertIn("Did not remint cursor leftover", text)
        self.assertNotEqual(text, cursor)
        self.assertNotEqual(text, tracker)
        self.assertIn("cursor-mcp-get-grounding-20260902-01", cursor)
        self.assertIn("grok-build-repair-tracker-mcp-get-20260902-01", tracker)


if __name__ == "__main__":
    unittest.main()
