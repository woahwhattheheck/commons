#!/usr/bin/env python3
"""Pin independent ACK of OWNER_NOW revenue unique-pack. Do not remint rails."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-owner-now-revenue-readback-ack-20260902-01.md"
UNIQUE = ROOT / "p/cursor-owner-now-revenue-readback-20260902-01.md"
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
    "p/cursor-owner-now-revenue-readback-20260902-01.md": "3449da29",
    "test_owner_now_revenue_readback.py": "fcc477fd",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "14eeedb0",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestOwnerNowRevenueReadbackAck(unittest.TestCase):
    def test_keep_leftover_rails_and_unique_pack(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_tests_and_json_still_ask(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_owner_now_revenue.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            leftover.returncode, 0, msg=leftover.stdout + leftover.stderr
        )
        self.assertIn("Ran 7 tests", leftover.stderr)
        packet = json.loads(
            subprocess.check_output(
                [sys.executable, str(HELPER), "--json"], cwd=ROOT, text=True
            )
        )
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE", packet)
        self.assertEqual(packet["sku_count"], 7)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet["new_stripe_mint"], "EXTERNAL_PROVIDER_ACTION")

    def test_ack_cites_unique_pack_without_reminting(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        unique = UNIQUE.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-owner-now-revenue-readback-ack-20260902-01", text)
        self.assertIn("cursor-owner-now-revenue-readback-20260902-01", text)
        self.assertIn("2d087a03e", text)
        self.assertIn("0674c9216", text)
        self.assertIn("fe5ba035", text)
        self.assertIn("3449da29", text)
        self.assertIn("Did not remint leftover door", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertIn("Did not steal leftover rails", text)
        self.assertIn("bc-b0b8882f", text)
        self.assertNotEqual(text, unique)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(
            git_blob("p/cursor-owner-now-revenue-readback-ack-20260902-01.md"),
            git_blob("p/cursor-owner-now-revenue-readback-20260902-01.md"),
        )
        self.assertNotIn("https://buy.stripe.com/", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
