#!/usr/bin/env python3
"""digit-right-now-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on right-now remint."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "digit-right-now-keep-larger-fixed-20260916-01"
CORE = ROOT / "host" / "right_now_revenue_core.py"
CATALOG = ROOT / "revenue" / "right_now" / "catalog.json"
LARGER = ("diagnostic.html", "commercial.html")
SPEC = importlib.util.spec_from_file_location("right_now_revenue_core_keep", CORE)
assert SPEC and SPEC.loader
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


def _tip_live() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))["live_cash"]


class DigitRightNowKeepLargerFixed2026091601Test(unittest.TestCase):
    def test_tip_catalog_validate_keeps_larger_fixed(self) -> None:
        live = core.validate_live_cash(_tip_live())
        self.assertEqual(
            [(row["path"], row["price_usd"]) for row in live["products"]],
            [
                ("agent-rescue.html", 29),
                ("dealer-service-lead-rescue.html", 199),
                ("referral-intake-completeness.html", 199),
                ("repair-booking-preflight.html", 199),
                ("plant-downtime-handoff.html", 199),
            ],
        )
        larger = live["larger_fixed"]
        self.assertEqual(len(larger), 2)
        by_path = {row["path"]: row for row in larger}
        for path in LARGER:
            self.assertIn(path, by_path)
        self.assertEqual(by_path["diagnostic.html"]["price_usd"], 12000)
        self.assertEqual(by_path["diagnostic.html"]["days"], 10)
        self.assertEqual(by_path["commercial.html"]["price_usd"], 30000)
        self.assertEqual(by_path["commercial.html"]["days"], 30)
        blob = json.dumps(live)
        self.assertNotIn("buy.stripe.com", blob)
        self.assertNotIn("plink_", blob)
        self.assertIn("Larger fixed", live["note"])
        self.assertIn(core.LIVE_CASH_CITE, live["cite"])

    def test_dropping_larger_fixed_fails_closed(self) -> None:
        live = copy.deepcopy(_tip_live())
        del live["larger_fixed"]
        with self.assertRaisesRegex(core.ControlError, "live_cash fields differ"):
            core.validate_live_cash(live)

    def test_autopsy_products_still_required(self) -> None:
        live = copy.deepcopy(_tip_live())
        live["products"] = live["products"][1:]
        with self.assertRaisesRegex(core.ControlError, "five verified product pages"):
            core.validate_live_cash(live)

    def test_invented_stripe_on_larger_fixed_fails_closed(self) -> None:
        live = copy.deepcopy(_tip_live())
        live["larger_fixed"][0]["payment_url"] = "https://buy.stripe.com/invented"
        with self.assertRaisesRegex(core.ControlError, "entry fields differ"):
            core.validate_live_cash(live)

    def test_core_contract_names_larger_fixed(self) -> None:
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("LIVE_CASH_LARGER_FIXED", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)
        self.assertIn("12000", text)
        self.assertIn("30000", text)
        self.assertIn('"larger_fixed"', text)

    def test_did_not_remint_catalog_json(self) -> None:
        local = subprocess.check_output(
            ["git", "hash-object", str(CATALOG)],
            cwd=ROOT,
            text=True,
        ).strip()
        tip = subprocess.check_output(
            ["git", "rev-parse", "HEAD:revenue/right_now/catalog.json"],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(local, tip)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        self.assertTrue(receipt.is_file())
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("host/right_now_revenue_core.py", text)
        paths = text.split("## Paths", 1)[1].split("## Products", 1)[0]
        self.assertNotIn("catalog.json", paths)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)


if __name__ == "__main__":
    unittest.main()
