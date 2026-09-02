#!/usr/bin/env python3
"""Pin unique-pack readback of Harborline pack-market leftover. Do not steal /market."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-harborline-pack-market-render-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
HELPER = ROOT / "host/harborline_pack_market_render.py"

KEEP = {
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-owner-now-revenue-readback-20260902-01.md": "3449da29",
    "owner-now-revenue.html": "1d3f1cdf",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestHarborlinePackMarketRenderReadback(unittest.TestCase):
    def test_keep_leftover_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_renders_without_commons_store(self) -> None:
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
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")

    def test_leftover_send_refused(self) -> None:
        proc = subprocess.run(
            ["python3", str(HELPER), "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["refused"], "--send")

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_pack_market_render.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-pack-market-render-readback-20260902-01", text)
        self.assertIn("0141bf7c8", text)
        self.assertIn("54c348dc", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not dump a store HTML door onto Commons", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
