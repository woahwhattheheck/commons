#!/usr/bin/env python3
"""Pin grok-build terminal leftover for PR 8357. Do not remint pack-market SHIP leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_render_ship.py"
LEFTOVER_HELPER = ROOT / "host/harborline_pack_market_render.py"
SHIP = ROOT / "p/cursor-harborline-pack-market-render-ship-20260902-01.md"
SHIP_TEST = ROOT / "test_harborline_pack_market_render_ship.py"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
RECEIPT = ROOT / "p/grokbuild-pr8357-terminal-20260902-01.md"
PEER = ROOT / "p/grokbuild-pr8345-terminal-20260902-01.md"

KEEP = {
    "p/cursor-harborline-pack-market-render-ship-20260902-01.md": "89457966",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "p/cursor-harborline-pack-market-slack-render-20260902-01.md": "0d95f2ab",
    "host/harborline_pack_market_slack_render.py": "a03534da",
    "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md": "f965e00f",
    "p/cursor-harborline-pack-market-render-readback-ack-20260902-01.md": "9d221c75",
    "p/grokbuild-pr8345-terminal-20260902-01.md": "baae9aaf",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8357Terminal(unittest.TestCase):
    def test_keep_ship_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertTrue(git_blob("hub_pages.py").startswith("5ac12648"))
        self.assertFalse(git_blob("hub_pages.py").startswith("14eeedb0"))

    def test_ship_helper_still_ships_standalone_store(self) -> None:
        proc = subprocess.run(
            ["python3", str(HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ship_ok"])
        self.assertEqual(payload["verdict"], "SHIP")
        self.assertEqual(payload["store"], "standalone")
        self.assertEqual(payload["desk_route"], "/market")
        self.assertFalse(payload["commons_is_store"])
        self.assertFalse(payload["marketplace_html_on_commons"])
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        leftover = subprocess.run(
            ["python3", str(LEFTOVER_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        leftover_payload = json.loads(leftover.stdout)
        self.assertEqual(leftover_payload["verdict"], "RENDER")
        self.assertEqual(leftover_payload["price_usd"], 200)
        refused = subprocess.run(
            ["python3", str(HELPER), "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["sent"], 0)
        self.assertFalse((ROOT / "marketplace.html").exists())

    def test_receipt_cites_8357_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        ship = SHIP.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8357-terminal-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8357@a7847360423bb5416f833867fa1ec599e5d52b66", text)
        self.assertIn("4a59669d46adf9cf3408c19db1977eaa43110a08", text)
        self.assertIn("781c1a9c7b", text)
        self.assertIn("932d089d90", text)
        self.assertIn("89457966ba", text)
        self.assertIn("issuecomment-5516363464", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("27/27 OK", text)
        self.assertNotEqual(text, ship)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, peer)
        self.assertTrue(SHIP_TEST.read_text(encoding="utf-8").count("54c348dc") >= 1)


if __name__ == "__main__":
    unittest.main()
