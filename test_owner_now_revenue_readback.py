#!/usr/bin/env python3
"""Pin unique-pack readback of OWNER_NOW revenue leftover. Do not remint rails."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-owner-now-revenue-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-owner-now-revenue-20260902-01.md"
HELPER = ROOT / "host/owner_now_revenue.py"

KEEP = {
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "host/owner_now_revenue.py": "d78f949f",
    "owner-now-revenue.html": "1d3f1cdf",
    "land/owner-now-revenue-20260902.md": "db81f250",
    "test_owner_now_revenue.py": "3ca325a9",
    "pay.js": "65a960f2",
    "ground/OWNER_NOW.md": "6b8ee988",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "14eeedb0",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestOwnerNowRevenueReadback(unittest.TestCase):
    def test_keep_leftover_rails_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_asks_for_sale(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE", packet)
        self.assertEqual(packet["sku_count"], 7)
        self.assertTrue(packet["chargeable"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet["new_stripe_mint"], "EXTERNAL_PROVIDER_ACTION")
        self.assertFalse(packet["not_minted_is_freeze"])
        self.assertTrue(packet["leftover_match"]["ok"])

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_owner_now_revenue.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 7 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-owner-now-revenue-readback-20260902-01", text)
        self.assertIn("0674c9216", text)
        self.assertIn("fe5ba035", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertIn("Did not remint leftover door", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("https://buy.stripe.com/", text)
        self.assertNotIn("https://donate.stripe.com/", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
