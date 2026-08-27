#!/usr/bin/env python3
"""Contracts for the two immediate-sale doors recovered from source commit 91704dd8."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent
TASK_FORGE = ROOT / "task-forge.html"
TITAN_HOUR = ROOT / "titan-hour.html"
UNLOCK_SKU = ROOT / "land" / "sku-unlock-20260826.md"
WHITEBOX_SKU = ROOT / "land" / "sku-whitebox-hour-20260826.md"
UNLOCK_CHECKOUT = "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04"
WHITEBOX_CHECKOUT = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
PACK_SHA256 = "2597ac55ff5b04e7584d0c786e7f93f8ae5a182b6e2788f1e07b0fc33ad98cff"


def field(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S.*?)\s*$", text)
    return match.group(1) if match else ""


class StrictHTMLParser(HTMLParser):
    pass


class ImmediateSaleDoorTests(unittest.TestCase):
    def test_prices_and_checkouts_are_existing_canonical_skus(self) -> None:
        unlock = UNLOCK_SKU.read_text(encoding="utf-8")
        whitebox = WHITEBOX_SKU.read_text(encoding="utf-8")

        self.assertEqual(field(unlock, "price"), "$5 USD one-time")
        self.assertEqual(field(unlock, "checkout"), UNLOCK_CHECKOUT)
        self.assertEqual(field(unlock, "status"), "LIVE")
        self.assertEqual(field(whitebox, "product"), "one dated White Box / dests hour")
        self.assertEqual(field(whitebox, "checkout"), WHITEBOX_CHECKOUT)
        self.assertEqual(field(whitebox, "status"), "LIVE")

    def test_task_forge_is_immediately_deliverable_and_stays_open(self) -> None:
        page = TASK_FORGE.read_text(encoding="utf-8")

        for marker in (
            "32 CC0 agent-evaluation tasks",
            "45,578 bytes",
            PACK_SHA256,
            "./artifacts/KITE_TASK_FORGE_0_R0.jsonl",
            "./artifacts/KITE_TASK_FORGE_0_R0.sha256",
            "Immediate delivery",
            UNLOCK_CHECKOUT,
            "does not buy secrecy or remove the free/open copy",
        ):
            self.assertIn(marker, page)

    def test_titan_hour_has_exact_intake_delivery_and_truth_boundaries(self) -> None:
        page = TITAN_HOUR.read_text(encoding="utf-8")

        for marker in (
            "TITAN Hands Activation Hour",
            "$250 / hour",
            WHITEBOX_CHECKOUT,
            "Exact intake",
            "Objective:",
            "Target surface:",
            "Success proof:",
            "Stop and rollback:",
            "Scheduling windows:",
            "Up to 60 scheduled minutes",
            "land/session-YYYYMMDD.md",
            "No perpetual agent, tool, shell, wireless, device, repository, or account access",
            "not the paid-session tool unlock proposed in PR #4074",
        ):
            self.assertIn(marker, page)

    def test_both_doors_are_static_valid_and_make_no_outcome_claim(self) -> None:
        pages = [TASK_FORGE.read_text(encoding="utf-8"), TITAN_HOUR.read_text(encoding="utf-8")]

        for page in pages:
            parser = StrictHTMLParser()
            parser.feed(page)
            parser.close()
            self.assertNotIn("<script", page.lower())
            for gate in ("login required", "account required", "sign up to buy", "log in to buy"):
                self.assertNotIn(gate, page.lower())

        combined = "\n".join(pages)
        for marker in ("payment", "settlement", "payout", "cash"):
            self.assertIn(marker, combined.lower())
        self.assertNotIn("paid_session", combined)
        self.assertNotIn("STRIPE_SECRET_KEY", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
