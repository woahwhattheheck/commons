#!/usr/bin/env python3
"""Later-main rematch of Harborline pack-market leftover + first unique-pack."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md"
UNIQUE_PACK = ROOT / "p/cursor-harborline-pack-market-render-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
HELPER = ROOT / "host/harborline_pack_market_render.py"

KEEP = {
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "test_harborline_pack_market_render_readback.py": "f4ee4f15",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "test_harborline_pack_market_render.py": "e8f8703c",
    "ground/OWNER_NOW.md": "6b8ee988",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-owner-now-revenue-readback-20260902-01.md": "3449da29",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-rematch-20260902-01.md": "c6707847",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestHarborlinePackMarketRenderReadbackRematch(unittest.TestCase):
    def test_keep_leftover_unique_pack_and_peers(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_renders_standalone(self) -> None:
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
        self.assertEqual(payload["featured"], "harborline-local-sites")
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")

    def test_leftover_hub_pages_keep_is_later_main_miss_not_remint(self) -> None:
        hub = git_blob("hub_pages.py")
        leftover_test = git_blob("test_harborline_pack_market_render.py")
        unique_pack_test = git_blob("test_harborline_pack_market_render_readback.py")
        self.assertTrue(hub.startswith("5ac12648"), hub)
        self.assertFalse(hub.startswith("14eeedb0"), hub)
        self.assertTrue(leftover_test.startswith("e8f8703c"), leftover_test)
        self.assertTrue(unique_pack_test.startswith("f4ee4f15"), unique_pack_test)
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_pack_market_render.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        combined = proc.stdout + proc.stderr
        self.assertIn("hub_pages.py reminted: want 14eeedb0 got 5ac12648", combined)
        self.assertNotIn("cursor-harborline-pack-market-render-20260902-01.md reminted", combined)
        self.assertNotIn("harborline_pack_market_render.py reminted", combined)

    def test_rematch_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        unique_pack = UNIQUE_PACK.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-pack-market-render-readback-rematch-20260902-01", text)
        self.assertIn("0141bf7c8", text)
        self.assertIn("3a418c574", text)
        self.assertIn("54c348dc", text)
        self.assertIn("6efbac54", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not remint leftover unique-pack", text)
        self.assertIn("remint leftover tests to lift that pin", text)
        self.assertIn("5ac12648", text)
        self.assertIn("Did not dump a store HTML door onto Commons", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertNotEqual(text, unique_pack)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "harborline.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
