#!/usr/bin/env python3
"""Pin grok-build terminal leftover for PR 8345. Do not remint pack-market leftover tests."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_render.py"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
LEFTOVER_TEST = ROOT / "test_harborline_pack_market_render.py"
RECEIPT = ROOT / "p/grokbuild-pr8345-terminal-20260902-01.md"

KEEP = {
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8345Terminal(unittest.TestCase):
    def test_keep_leftover_unique_paths_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertTrue(git_blob("hub_pages.py").startswith("5ac12648"))
        self.assertFalse(git_blob("hub_pages.py").startswith("14eeedb0"))

    def test_helper_still_renders_standalone_store(self) -> None:
        proc = subprocess.run(
            ["python3", str(HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "RENDER")
        self.assertEqual(payload["store"], "standalone")
        self.assertFalse(payload["commons_is_store"])
        self.assertFalse(payload["marketplace_html_on_commons"])
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
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

    def test_receipt_cites_8345_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8345-terminal-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8345@74bded427557f0ee32417f7b3fbb065e389aaa7f", text)
        self.assertIn("0141bf7c8de8526ae8d748eca428cf793cb75b66", text)
        self.assertIn("cc9a33209e", text)
        self.assertIn("54c348dc16", text)
        self.assertIn("e8f8703c34", text)
        self.assertIn("issuecomment-5516297673", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("26/26 OK", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("14eeedb0", LEFTOVER_TEST.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
