#!/usr/bin/env python3
"""SHIP leftover: unique-pack OWNER_NOW revenue readback already on main.

Did not remint leftover door/pay.js. Did not invent Stripe URLs.
Did not steal Harborline /harborline.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import owner_now_revenue_readback_ship as ship  # noqa: E402

SHIP_ID = "cursor-owner-now-revenue-readback-ship-20260902-01"
READBACK_ID = "cursor-owner-now-revenue-readback-20260902-01"
ASK_ID = "cursor-owner-now-revenue-20260902-01"
CANONICAL = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
    "sku-muhlnickel-titan-20260826",
)


class TestOwnerNowRevenueReadbackShip(unittest.TestCase):
    def test_keep_leftover_unique_pack_and_ask_for_sale_rails(self) -> None:
        match = ship.leftover_readback_match(ROOT)
        self.assertTrue(match["ok"], match)
        self.assertTrue(match["did_not_remint_leftover_door"])
        self.assertTrue(match["did_not_remint_pay_js"])
        self.assertTrue(match["did_not_steal_harborline"])
        self.assertTrue(match["harborline_path_absent"])
        self.assertTrue(match["leftover_blob"].startswith("3449da29"))
        self.assertTrue(match["leftover_receipt_blob"].startswith("fe5ba035"))
        for rel, prefix in ship.KEEP.items():
            blob = match["blobs"][rel]
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_unique_ship_asks_for_sale_on_seven_proven_rails(self) -> None:
        packet = ship.ask_for_sale(ROOT)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE", packet)
        self.assertEqual(packet["id"], SHIP_ID)
        self.assertEqual(packet["leftover_id"], READBACK_ID)
        self.assertEqual(packet["leftover_ask_id"], ASK_ID)
        self.assertEqual(packet["leftover_land"], "2d087a03e")
        self.assertEqual(packet["leftover_blob"], "3449da29")
        self.assertEqual(packet["leftover_receipt_blob"], "fe5ba035")
        self.assertEqual(packet["leftover_pr"], 8343)
        self.assertEqual(packet["sku_count"], 7)
        self.assertTrue(packet["chargeable"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet["new_stripe_mint"], "EXTERNAL_PROVIDER_ACTION")
        self.assertEqual(packet["checkout"], "NOT_MINTED")
        self.assertFalse(packet["not_minted_is_freeze"])
        self.assertTrue(packet["did_not_remint_leftover_door"])
        self.assertTrue(packet["did_not_remint_pay_js"])
        self.assertTrue(packet["did_not_steal_harborline"])
        skus = [row["sku"] for row in packet["ask_for_sale"]]
        self.assertEqual(skus, list(CANONICAL))

    def test_invented_stripe_url_is_refused(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "owner_now_revenue_readback_ship.py"),
                "--json",
                "--url",
                "https://buy.stripe.com/inventedNotARealLink",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        packet = json.loads(completed.stdout)
        self.assertEqual(packet["verdict"], "INVENTED_REFUSED")
        self.assertTrue(packet["invented_stripe_urls"])
        self.assertEqual(packet["url_check"]["verdict"], "INVENTED_REFUSED")

    def test_leftover_ask_for_sale_still_runs(self) -> None:
        leftover = subprocess.run(
            [sys.executable, str(ROOT / "host" / "owner_now_revenue.py"), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, leftover.stderr)
        packet = json.loads(leftover.stdout)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE")
        self.assertEqual(packet["sku_count"], 7)
        self.assertFalse(packet["invented_stripe_urls"])
        invented = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "owner_now_revenue.py"),
                "--json",
                "--url",
                "https://buy.stripe.com/inventedNotARealLink",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(invented.returncode, 1, invented.stderr)
        refused = json.loads(invented.stdout)
        self.assertEqual(refused["verdict"], "INVENTED_REFUSED")

    def test_ship_receipt_exists_and_does_not_steal(self) -> None:
        text = (ROOT / f"p/{SHIP_ID}.md").read_text(encoding="utf-8")
        leftover = (ROOT / f"p/{ASK_ID}.md").read_text(encoding="utf-8")
        readback = (ROOT / f"p/{READBACK_ID}.md").read_text(encoding="utf-8")
        self.assertIn(SHIP_ID, text)
        self.assertIn(READBACK_ID, text)
        self.assertIn("2d087a03e", text)
        self.assertIn("3449da29", text)
        self.assertIn("fe5ba035", text)
        self.assertIn("#8343", text)
        self.assertIn("ASK_FOR_SALE", text)
        self.assertIn("Did not remint leftover door", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertIn("Did not steal Harborline", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotIn("https://buy.stripe.com/", text)
        self.assertNotIn("https://donate.stripe.com/", text)
        self.assertFalse((ROOT / "harborline").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_cli_ask_for_sale_exits_zero(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "owner_now_revenue_readback_ship.py"),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        packet = json.loads(completed.stdout)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE")
        self.assertEqual(packet["id"], SHIP_ID)


if __name__ == "__main__":
    unittest.main()
