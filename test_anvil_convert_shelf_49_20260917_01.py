#!/usr/bin/env python3
"""anvil-convert-shelf-49-20260917-01 — WO-CONVERT-SHELF-49 pack + render canary."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "convert-shelf-49-20260917-01"
RECEIPT = ROOT / "p" / "anvil-convert-shelf-49-20260917-01.md"
SKU = ROOT / "land" / "sku-convert-shelf-49-20260917.md"
CONTRACT = ROOT / "revenue" / "convert_shelf_49" / "contract.json"
ENGINE = ROOT / "host" / "convert_shelf_pack.py"
CITE = "anvil-convert-shelf-49-20260917-01"
AUTOPSY = "4gM9AS3Ot8bfeOZ78S43S0g"
REQUIRED = (
    "README.md",
    "offer.md",
    "checkout.md",
    "instructions.md",
    "checklist.md",
    "intake.md",
    "sell-blurb.md",
    "door.html",
    "template.html",
    "sample/README.md",
    "sample/context.json",
    "sample/shelf.rendered.html",
)


def load_engine():
    spec = importlib.util.spec_from_file_location("convert_shelf_pack", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestAnvilConvertShelf49(unittest.TestCase):
    def test_pack_files_and_receipt(self) -> None:
        for name in REQUIRED:
            self.assertTrue((PACK / name).is_file(), name)
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(SKU.is_file())
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(ENGINE.is_file())
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CITE, text)
        self.assertIn("WO-CONVERT-SHELF-49", text)
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
        self.assertEqual(contract["commercial"]["pack_usd"], 49)
        self.assertEqual(contract["commercial"]["checkout"], "NOT_MINTED")
        self.assertTrue(contract["commercial"]["stripe_ask_if_no_pl"])
        self.assertEqual(contract["commercial"]["cash_usd"], 0)
        self.assertFalse(contract["requires_login"])

    def test_door_is_sellable_without_minted_checkout(self) -> None:
        door = (PACK / "door.html").read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", door)
        self.assertIn("tokenjunkielabs@gmail.com", door)
        self.assertIn("one business day", door)
        self.assertIn("existing payment", door.lower())
        self.assertIn("SCRAPPED", door)
        self.assertIn(CITE, door)
        self.assertIn('id="titanmcp-pad-pointer"', door)
        self.assertNotIn("buy.stripe.com", door)
        self.assertNotIn(AUTOPSY, door)
        self.assertNotIn('id="buy-now-live-checkout"', door)

    def test_templates_name_the_deliverable(self) -> None:
        blob = "\n".join(
            (PACK / name).read_text(encoding="utf-8")
            for name in (
                "README.md",
                "offer.md",
                "checklist.md",
                "intake.md",
                "instructions.md",
                "sell-blurb.md",
            )
        )
        lower = blob.lower()
        self.assertIn("existing", lower)
        self.assertIn("template.html", lower)
        self.assertIn("context.json", lower)
        self.assertIn("one-page", lower)
        self.assertIn("splice", lower)
        self.assertIn("receipt", lower)
        self.assertNotIn(AUTOPSY, blob)
        self.assertNotIn("buy.stripe.com/", blob)

    def test_template_splices_only_existing_url(self) -> None:
        mod = load_engine()
        template = (PACK / "template.html").read_text(encoding="utf-8")
        self.assertIn("{{PAYMENT_URL}}", template)
        self.assertIn("{{PRODUCT_NAME}}", template)
        self.assertIn("{{CTA_LABEL}}", template)
        self.assertNotIn("buy.stripe.com", template)
        self.assertNotIn(AUTOPSY, template)
        context = json.loads((PACK / "sample" / "context.json").read_text(encoding="utf-8"))
        self.assertEqual(mod.validate_context(context), [])
        bad = dict(context, PAYMENT_URL="http://insecure.example.com/x")
        self.assertTrue(mod.validate_context(bad))
        bad2 = dict(context, PAYMENT_URL="https://buy.stripe.com/" + AUTOPSY)
        self.assertTrue(any("Autopsy" in p for p in mod.validate_context(bad2)))
        rendered = mod.render(template, context)
        check = mod.validate_rendered(rendered, context)
        self.assertTrue(check["clean"], check)
        self.assertIn('href="https://checkout.example.com/queueboard-monthly"', rendered)
        self.assertIn("Queueboard", rendered)
        unsafe = dict(context, TAGLINE="Fast <b>&amp;</b> cheap")
        escaped = mod.render(template, unsafe)
        self.assertIn("Fast &lt;b&gt;&amp;amp;&lt;/b&gt; cheap", escaped)
        self.assertNotIn("<b>&</b>", escaped)

    def test_rendered_sample_matches_canary_output(self) -> None:
        mod = load_engine()
        template = (PACK / "template.html").read_text(encoding="utf-8")
        context = json.loads((PACK / "sample" / "context.json").read_text(encoding="utf-8"))
        expected = mod.render(template, context)
        shipped = (PACK / "sample" / "shelf.rendered.html").read_text(encoding="utf-8")
        self.assertEqual(shipped, expected)

    def test_canary_render_splice(self) -> None:
        mod = load_engine()
        receipt = mod.run_canary(ROOT)
        self.assertEqual(receipt["cite"], CITE)
        self.assertEqual(receipt["price_usd"], 49)
        self.assertEqual(receipt["checkout"], "NOT_MINTED")
        self.assertEqual(receipt["cash_usd"], 0)
        self.assertIsNone(receipt["buyer"])
        self.assertFalse(receipt["bryce_as_buyer"])
        self.assertFalse(receipt["invented_stripe"])
        self.assertFalse(receipt["autopsy_sold"])
        self.assertTrue(receipt["splice_only_existing_url"])
        self.assertTrue(receipt["rendered"]["clean"], receipt["rendered"])
        self.assertEqual(receipt["pack_missing"], [])
        proc = subprocess.run(
            [sys.executable, str(ENGINE), "--canary", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cli = json.loads(proc.stdout)
        self.assertTrue(cli["rendered"]["clean"])
        self.assertEqual(cli["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
