#!/usr/bin/env python3
"""SHIP leftover unique-pack WIRE fold + hall-pass readback. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-wire-hall-pass-unique-pack-ship-20260902-01.md"
WIRE_PACK = ROOT / "p/cursor-wire-super-mcp-fold-readback-20260902-01.md"
HALL_PACK = ROOT / "p/cursor-google-ai-mode-hall-pass-readback-20260902-01.md"
FOLD = ROOT / "p/wire-super-mcp-fold-20260902-01.md"
HALL = ROOT / "p/cursor-google-ai-mode-hall-pass-20260902-01.md"

KEEP = {
    "p/cursor-wire-super-mcp-fold-readback-20260902-01.md": "63b8221d",
    "p/cursor-google-ai-mode-hall-pass-readback-20260902-01.md": "42e9e750",
    "test_cursor_wire_super_mcp_fold_readback.py": "3e8b4a99",
    "test_cursor_google_ai_mode_hall_pass_readback.py": "925dd39d",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/cursor-google-ai-mode-hall-pass-20260902-01.md": "4bb8b78d",
    "test_google_ai_mode_hall_pass.py": "9fe45498",
    ".agents/skills/google-ai-mode-hall-pass/SKILL.md": "bb22f950",
    "ground/tokens/google-ai-mode-hall-pass.md": "f730edc2",
    "api/mcp.py": "bc558a5f",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md": "f98887bf",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWireHallPassUniquePackShip(unittest.TestCase):
    def test_keep_leftover_unique_pack_and_fold_skill(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_unique_pack_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_cursor_wire_super_mcp_fold_readback.py",
                "test_cursor_google_ai_mode_hall_pass_readback.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 9 tests", leftover.stderr)

    def test_leftover_hall_pass_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_google_ai_mode_hall_pass.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 8 tests", leftover.stderr)

    def test_public_mcp_get_200(self) -> None:
        req = urllib.request.Request(
            "https://commons-spark-mcp.vercel.app/mcp",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            self.assertEqual(resp.status, 200)
        packet = json.loads(body.decode("utf-8"))
        self.assertEqual(packet.get("name"), "commons")
        self.assertEqual(packet.get("version"), "1.4.0")
        self.assertEqual(packet.get("auth"), "none")
        self.assertEqual(packet.get("toolCount"), 17)

    def test_ship_receipt_exists_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        wire_pack = WIRE_PACK.read_text(encoding="utf-8")
        hall_pack = HALL_PACK.read_text(encoding="utf-8")
        fold = FOLD.read_text(encoding="utf-8")
        hall = HALL.read_text(encoding="utf-8")
        self.assertIn("cursor-wire-hall-pass-unique-pack-ship-20260902-01", text)
        self.assertIn("cursor-wire-super-mcp-fold-readback-20260902-01", text)
        self.assertIn("cursor-google-ai-mode-hall-pass-readback-20260902-01", text)
        self.assertIn("dc5455bf2", text)
        self.assertIn("63b8221d", text)
        self.assertIn("42e9e750", text)
        self.assertIn("cc7fda2e", text)
        self.assertIn("4bb8b78d", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("bb22f950", text)
        self.assertIn("bc558a5f", text)
        self.assertIn("5ac12648", text)
        self.assertIn("dc59355d", text)
        self.assertIn("1788390880.602649", text)
        self.assertIn("bc-eee23776", text)
        self.assertIn("bc-73365238", text)
        self.assertIn("Did **not** remint leftover fold/skill receipts", text)
        self.assertIn("Independently spark-mcp GET 200", text)
        self.assertIn("Sends 0", text)
        self.assertNotEqual(text, wire_pack)
        self.assertNotEqual(text, hall_pack)
        self.assertNotEqual(text, fold)
        self.assertNotEqual(text, hall)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "harborline.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse(
            (ROOT / "p/cursor-wire-super-mcp-fold-readback-ship-20260902-01.md").exists()
        )
        self.assertFalse(
            (
                ROOT
                / "p/cursor-google-ai-mode-hall-pass-readback-ship-20260902-01.md"
            ).exists()
        )
        self.assertFalse(
            (
                ROOT
                / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
