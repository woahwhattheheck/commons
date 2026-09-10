#!/usr/bin/env python3
"""Expand right-now catalog live_cash after tests battery 34406500391.

Delayed pull_request battery on already-merged PR #11770
(head 183a04992021d02cfe095fb7be9f2e563aac1bf3, merge-ref
938f66295151806291913944ee81c793a5a3f024) failed 150 files.
Later KEEP-lifts closed living KEEP dicts of reminted shared files.
Unique leftover test_coil_wakeup_muhl_once.py still passes.
Remaining graph: revenue/right_now/catalog.json already carries leftover
live_cash (five verified product pages, cite goat-right-now-catalog-json-live-cash-20260909-01)
but host/right_now_revenue.py exact-set validation rejected that extra
field, so test_right_now_execution.py could not compile. Expand the
control contract to require and measure live_cash. Recompile control.json
source_receipts. Do not remint leftover receipts. Historical SOURCE_REV
maps stay on their frozen trees. Hands off #8802.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGINALS = (
    "test_coil_wakeup_muhl_once.py",
    "test_right_now_execution.py",
    "test_right_now.py",
)
RECEIPT = ROOT / "p/grokbuild-tests-battery-34406500391-keep-lift-20260910-01.md"
DEDUPE = (
    "woahwhattheheck/commons:tests:"
    "183a04992021d02cfe095fb7be9f2e563aac1bf3:"
    "the whole battery, one failure fails the run"
)
WAKEUP = "27f8043f"
CATALOG = "944dae85"
STALE_CONTROL = "375e8f45"
CONTROL = "aa19c74b"
REVENUE = "ef9255f5"
LEFTOVER = "71002112"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery34406500391KeepLift(unittest.TestCase):
    def test_live_wakeup_and_catalog_match_lifted_prefixes(self) -> None:
        wakeup = git_blob("wakeup.html")
        catalog = git_blob("revenue/right_now/catalog.json")
        control = git_blob("revenue/right_now/control.json")
        revenue = git_blob("host/right_now_revenue.py")
        leftover = git_blob("p/coil-wakeup-muhl-once-20260909-01.md")
        self.assertTrue(wakeup.startswith(WAKEUP), wakeup)
        self.assertTrue(catalog.startswith(CATALOG), catalog)
        self.assertTrue(control.startswith(CONTROL), control)
        self.assertFalse(control.startswith(STALE_CONTROL), control)
        self.assertTrue(revenue.startswith(REVENUE), revenue)
        self.assertTrue(leftover.startswith(LEFTOVER), leftover)

    def test_wakeup_cite_and_live_cash_contract_stay(self) -> None:
        wake = (ROOT / "wakeup.html").read_text(encoding="utf-8")
        self.assertIn("python host/muhl_tools_once.py --go", wake)
        self.assertIn("host/muhl_tools_once.py", wake)
        catalog = json.loads(
            (ROOT / "revenue/right_now/catalog.json").read_text(encoding="utf-8")
        )
        self.assertIn("live_cash", catalog)
        products = [
            (row["name"], row["price_usd"], row["path"])
            for row in catalog["live_cash"]["products"]
        ]
        self.assertEqual(
            products,
            [
                ("Agent Failure Autopsy", 29, "agent-rescue.html"),
                ("Dealer Service Lead Rescue", 199, "dealer-service-lead-rescue.html"),
                ("Referral Intake Completeness", 199, "referral-intake-completeness.html"),
                ("Repair Booking Preflight", 199, "repair-booking-preflight.html"),
                ("Plant Downtime Handoff", 199, "plant-downtime-handoff.html"),
            ],
        )
        self.assertIn(
            "goat-right-now-catalog-json-live-cash-20260909-01",
            catalog["live_cash"]["cite"],
        )
        revenue = (ROOT / "host/right_now_revenue.py").read_text(encoding="utf-8")
        self.assertIn('"live_cash"', revenue)
        self.assertIn("def validate_live_cash", revenue)
        self.assertIn("LIVE_CASH_CITE", revenue)
        self.assertNotIn('type="password"', wake)
        self.assertNotIn("Authorization", revenue)

    def test_originally_failing_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    ["python3", name],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{name}\n{proc.stdout}\n{proc.stderr}",
                )

    def test_did_not_remint_leftover_receipts(self) -> None:
        leftover = ROOT / "p/coil-wakeup-muhl-once-20260909-01.md"
        peer = ROOT / "p/digit-peer-coil-wakeup-muhl-once-20260909-01.md"
        self.assertTrue(leftover.is_file())
        self.assertTrue(peer.is_file())
        self.assertTrue(git_blob("p/coil-wakeup-muhl-once-20260909-01.md").startswith(LEFTOVER))
        self.assertTrue(git_blob("p/digit-peer-coil-wakeup-muhl-once-20260909-01.md").startswith("c64a1243"))
        text = leftover.read_text(encoding="utf-8")
        self.assertIn("coil-wakeup-muhl-once-20260909-01", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)

    def test_receipt_names_dedupe_key(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-battery-34406500391-keep-lift-20260910-01", text)
        self.assertIn(DEDUPE, text)
        self.assertIn("34406500391", text)
        self.assertIn("183a04992021d02cfe095fb7be9f2e563aac1bf3", text)
        self.assertIn("live_cash", text)


if __name__ == "__main__":
    unittest.main()
