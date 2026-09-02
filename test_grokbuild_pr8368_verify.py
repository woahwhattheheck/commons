#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8368. Do not remint 8357 leftover."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_render_ship.py"
LEFTOVER_HELPER = ROOT / "host/harborline_pack_market_render.py"
SHIP = ROOT / "p/cursor-harborline-pack-market-render-ship-20260902-01.md"
LEFTOVER_8357 = ROOT / "p/grokbuild-pr8357-terminal-20260902-01.md"
RECEIPT = ROOT / "p/grokbuild-pr8368-verify-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8357-terminal-20260902-01.md": "0997206e",
    "p/cursor-harborline-pack-market-render-ship-20260902-01.md": "89457966",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/grokbuild-pr8345-terminal-20260902-01.md": "baae9aaf",
}

BODY_SHA256 = "c7fbedfd551ec5716aa71691da4ebce4c0b7181ba2cda005a8e18b3d4b5586fc"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8368Verify(unittest.TestCase):
    def test_keep_8368_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertTrue(git_blob("hub_pages.py").startswith("5ac12648"))

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

    def test_receipt_cites_8368_and_matches_ntfy_body(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER_8357.read_text(encoding="utf-8")
        ship = SHIP.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8368-verify-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8368@056a24f1576bfa6abcc6130f7c7b9f895112ffc7", text)
        self.assertIn("faa3ee273e0e391b5e31965e474cb3a378689adb", text)
        self.assertIn("056a24f1576bfa6abcc6130f7c7b9f895112ffc7", text)
        self.assertIn("0997206e", text)
        self.assertIn("issuecomment-5516487581", text)
        self.assertIn("MeDdixxJ86P0", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("17/17 OK", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, ship)


if __name__ == "__main__":
    unittest.main()
