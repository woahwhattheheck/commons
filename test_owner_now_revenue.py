#!/usr/bin/env python3
"""OWNER_NOW leftover: ask for the sale on proven rails. Not a remint."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import owner_now_revenue as onr  # noqa: E402


KEEP = {
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
}

CANONICAL = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
    "sku-muhlnickel-titan-20260826",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestOwnerNowRevenue(unittest.TestCase):
    def test_keep_owner_now_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_match_is_independent(self) -> None:
        match = onr.leftover_match(ROOT)
        self.assertTrue(match["ok"], match)
        self.assertTrue(match["did_not_remint_leftover"])
        self.assertTrue(match["leftover_blob"].startswith("1b3cd631"))
        self.assertIn("invented 337 closer was never Bryce law", (ROOT / "ground/OWNER_NOW.md").read_text(encoding="utf-8"))

    def test_ask_for_sale_on_seven_proven_rails(self) -> None:
        packet = onr.ask_for_sale(ROOT)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE", packet)
        self.assertEqual(packet["point"], "generate revenue")
        self.assertTrue(packet["chargeable"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertFalse(packet["not_minted_is_freeze"])
        self.assertTrue(packet["did_not_ack_hourly"])
        self.assertEqual(packet["new_stripe_mint"], "EXTERNAL_PROVIDER_ACTION")
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet["sku_count"], 7)
        skus = [row["sku"] for row in packet["ask_for_sale"]]
        self.assertEqual(skus, list(CANONICAL))
        for row in packet["ask_for_sale"]:
            self.assertEqual(row["ask"], "ASK_FOR_SALE")
            self.assertTrue(onr.looks_like_stripe_checkout(row["url"]))

    def test_invented_stripe_url_is_refused(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "owner_now_revenue.py"),
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

    def test_canonical_url_is_not_invented(self) -> None:
        packet = onr.ask_for_sale(ROOT)
        tip = packet["ask_for_sale"][0]["url"]
        check = json.loads(
            subprocess.check_output(
                [
                    sys.executable,
                    str(ROOT / "host" / "owner_now_revenue.py"),
                    "--json",
                    "--url",
                    tip,
                ],
                text=True,
            )
        )
        self.assertEqual(check["verdict"], "ASK_FOR_SALE")
        self.assertFalse(check["invented_stripe_urls"])
        self.assertEqual(check["url_check"]["verdict"], "CANONICAL")

    def test_door_asks_for_sale_without_static_stripe(self) -> None:
        door = (ROOT / "owner-now-revenue.html").read_text(encoding="utf-8")
        self.assertIn('data-checkout-first="1"', door)
        self.assertIn("js-checkout-slot", door)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", door)
        self.assertIn("generate revenue", door)
        self.assertIn("348ffcc2a", door)
        self.assertIn("1b3cd631", door)
        self.assertIn("6b8ee988", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("https://donate.stripe.com/", door)
        for sku in CANONICAL:
            self.assertIn('data-sku="%s"' % sku, door)
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn('getAttribute("data-checkout-first")', pay_js)

    def test_cli_ask_for_sale_exits_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host" / "owner_now_revenue.py"), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        packet = json.loads(completed.stdout)
        self.assertEqual(packet["verdict"], "ASK_FOR_SALE")


if __name__ == "__main__":
    unittest.main()
