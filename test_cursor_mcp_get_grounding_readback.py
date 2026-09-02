#!/usr/bin/env python3
"""Pin unique-pack readback of MCP GET + grounding leftover. Do not remint hub."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-mcp-get-grounding-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-mcp-get-grounding-20260902-01.md"
DOOR = ROOT / "grounding.html"

KEEP = {
    "p/cursor-mcp-get-grounding-20260902-01.md": "0bc79b8c",
    "grounding.html": "abb91caf",
    "test_mcp_get_open.py": "239564b9",
    "test_grounding_door.py": "ef9a7982",
    "commons_mcp.py": "23996ca3",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorMcpGetGroundingReadback(unittest.TestCase):
    def test_keep_leftover_hub_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_capability_map_has_no_login(self) -> None:
        import commons_mcp as cm
        from api import mcp

        core = cm.public_mcp_capability_map()
        self.assertEqual(core["auth"], "none")
        self.assertTrue(core["open_door"])
        self.assertFalse(core["login"])
        self.assertFalse(core["oauth"])
        self.assertIsNone(core["session"])
        public = cm.public_mcp_capability_map(
            extra_tools=(mcp.GET_SEND_LINK_TOOL["name"],),
            url="https://commons-spark-mcp.vercel.app/mcp",
        )
        self.assertEqual(public["toolCount"], 17)
        blob = json.dumps(public)
        self.assertNotIn("password", blob.lower())
        self.assertNotIn("api-key", blob.lower())

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_mcp_get_open.py",
                "test_grounding_door.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 8 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-mcp-get-grounding-readback-20260902-01", text)
        self.assertIn("34e77be19", text)
        self.assertIn("0bc79b8c", text)
        self.assertIn("abb91caf", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("Did **not** unique-pack this seat item 6", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("Possessing the link is authorization", door)
        self.assertIn('id="tab-what"', door)
        self.assertIn('id="tab-roads"', door)
        self.assertNotIn('type="password"', door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
