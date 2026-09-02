#!/usr/bin/env python3
"""Pin grok-build verify leftover for PR 8358. Do not remint 8345 leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8358-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8345-terminal-20260902-01.md"
HELPER = ROOT / "host/harborline_pack_market_render.py"
LEFTOVER_TEST = ROOT / "test_harborline_pack_market_render.py"

KEEP = {
    "p/grokbuild-pr8345-terminal-20260902-01.md": "baae9aaf",
    "test_grokbuild_pr8345_terminal.py": "4ea55398",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "test_harborline_pack_market_render.py": "e8f8703c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8358Verify(unittest.TestCase):
    def test_keep_8358_and_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertTrue(git_blob("hub_pages.py").startswith("5ac12648"))
        self.assertFalse(git_blob("hub_pages.py").startswith("14eeedb0"))

    def test_helper_still_renders_standalone(self) -> None:
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

    def test_receipt_cites_8358_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8358-verify-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8358@035593cf9af8ecb80390c626cd16952f359c42d2", text)
        self.assertIn("3b6f53740b1e120eb27e2a6ca273be3343b749b6", text)
        self.assertIn("baae9aaffc", text)
        self.assertIn("4ea553988d", text)
        self.assertIn("issuecomment-5516401481", text)
        self.assertIn("7xLIdCV0jYwH", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("28/28 OK", text)
        self.assertNotEqual(text, prior)
        self.assertTrue(LEFTOVER_TEST.read_text(encoding="utf-8").count("14eeedb0") >= 1)


if __name__ == "__main__":
    unittest.main()
