#!/usr/bin/env python3
"""latch-ci-fix-pack-99-20260917-01 — WO-CI-FIX-PACK-99 pack + fail→green canary."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "ci-fix-99-20260917-01"
RECEIPT = ROOT / "p" / "latch-ci-fix-pack-99-20260917-01.md"
SKU = ROOT / "land" / "sku-ci-fix-99-20260917.md"
CONTRACT = ROOT / "revenue" / "ci_fix_pack_99" / "contract.json"
ENGINE = ROOT / "host" / "ci_fix_pack.py"
CITE = "latch-ci-fix-pack-99-20260917-01"
AUTOPSY = "4gM9AS3Ot8bfeOZ78S43S0g"
REQUIRED = (
    "README.md",
    "offer.md",
    "checkout.md",
    "instructions.md",
    "checklist.md",
    "pr-body.md",
    "receipt-skeleton.md",
    "intake.md",
    "sell-blurb.md",
    "door.html",
    "sample/README.md",
    "sample/fixture/health.py",
    "sample/fixture/test_health.py",
    "sample/fixture/workflow.yml",
    "sample/fixture/actions-log-red.txt",
)


def load_engine():
    spec = importlib.util.spec_from_file_location("ci_fix_pack", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestLatchCiFixPack99(unittest.TestCase):
    def test_pack_files_and_receipt(self) -> None:
        for name in REQUIRED:
            self.assertTrue((PACK / name).is_file(), name)
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(SKU.is_file())
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(ENGINE.is_file())
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CITE, text)
        self.assertIn("WO-CI-FIX-PACK-99", text)
        self.assertIn("NOT_MINTED", text)
        self.assertNotIn(AUTOPSY, text)

    def test_checkout_not_minted_stripe_ask(self) -> None:
        checkout = (PACK / "checkout.md").read_text(encoding="utf-8")
        sku = SKU.read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", checkout)
        self.assertIn("Stripe ask if no PL", checkout)
        self.assertIn("tokenjunkielabs@gmail.com", checkout)
        self.assertNotIn("buy.stripe.com/", checkout)
        self.assertNotIn(AUTOPSY, checkout)
        self.assertIn("NOT_MINTED", sku)
        self.assertNotIn("buy.stripe.com/", sku)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["commercial"]["pack_usd"], 99)
        self.assertEqual(contract["commercial"]["checkout"], "NOT_MINTED")
        self.assertTrue(contract["commercial"]["stripe_ask_if_no_pl"])
        self.assertEqual(contract["commercial"]["cash_usd"], 0)
        self.assertFalse(contract["requires_login"])

    def test_door_is_sellable_without_convert_shelf(self) -> None:
        door = (PACK / "door.html").read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", door)
        self.assertIn("tokenjunkielabs@gmail.com", door)
        self.assertIn("one business day", door)
        self.assertIn("Public repository URL", door)
        self.assertIn("Failing Actions run or job URL", door)
        self.assertIn("Red check name", door)
        self.assertIn("SCRAPPED", door)
        self.assertIn(CITE, door)
        self.assertIn("id=\"titanmcp-pad-pointer\"", door)
        self.assertNotIn("buy.stripe.com", door)
        self.assertNotIn(AUTOPSY, door)
        self.assertNotIn("id=\"buy-now-live-checkout\"", door)

    def test_templates_name_the_deliverable(self) -> None:
        blob = "\n".join(
            (PACK / name).read_text(encoding="utf-8")
            for name in (
                "README.md",
                "checklist.md",
                "pr-body.md",
                "receipt-skeleton.md",
                "intake.md",
            )
        )
        lower = blob.lower()
        self.assertIn("thin pr", lower)
        self.assertIn("thin patch", lower)
        self.assertIn("receipt", lower)
        self.assertIn("class_id", blob)
        self.assertIn("public repository", lower)
        self.assertNotIn(AUTOPSY, blob)
        self.assertNotIn("buy.stripe.com/", blob)

    def test_canary_fail_then_green(self) -> None:
        mod = load_engine()
        fixture = PACK / "sample" / "fixture"
        red = mod.run_unittest(fixture)
        self.assertFalse(red["green"], red["combined"])
        self.assertEqual(red["classification"]["class_id"], "unittest_assertion")
        log = (fixture / "actions-log-red.txt").read_text(encoding="utf-8")
        classified = mod.classify_log(log)
        self.assertEqual(classified["class_id"], "unittest_assertion")
        self.assertTrue(classified["in_scope"])
        receipt = mod.run_canary(ROOT)
        self.assertEqual(receipt["cite"], CITE)
        self.assertEqual(receipt["price_usd"], 99)
        self.assertEqual(receipt["checkout"], "NOT_MINTED")
        self.assertEqual(receipt["cash_usd"], 0)
        self.assertIsNone(receipt["buyer"])
        self.assertFalse(receipt["bryce_as_buyer"])
        self.assertFalse(receipt["invented_stripe"])
        self.assertFalse(receipt["autopsy_sold"])
        self.assertFalse(receipt["red"]["green"])
        self.assertTrue(receipt["green"]["green"])
        self.assertEqual(receipt["patch"]["path"], "health.py")
        self.assertEqual(receipt["diagnosis"]["class_id"], "unittest_assertion")
        self.assertTrue(receipt["pr_body_has_class"])
        proc = subprocess.run(
            [sys.executable, str(ENGINE), "--canary", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cli = json.loads(proc.stdout)
        self.assertTrue(cli["green"]["green"])
        self.assertFalse(cli["red"]["green"])


if __name__ == "__main__":
    unittest.main()
