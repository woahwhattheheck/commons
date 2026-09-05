#!/usr/bin/env python3
"""Hermetic: Autopsy R4 fixture points at commerce.html tip-shelf."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from roles import RoleStore

AUTOPSY_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "synthetic_agent_failure_autopsy_role.json"
)
COMMERCE_PAGE = "commerce.html"
LIVE_CHECKOUT = "buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"


class AutopsyTipShelfPointerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_fixture_points_at_tip_shelf(self) -> None:
        raw = json.loads(AUTOPSY_FIXTURE.read_text(encoding="utf-8"))
        role = self.store.create(raw)
        pointers = {k["pointer"] for k in role["knowledge"]}
        self.assertIn(COMMERCE_PAGE, pointers)
        pay = next(
            r for r in role["access_routes"] if r["name"] == "payment_capability"
        )
        self.assertIn(COMMERCE_PAGE, pay.get("note", ""))
        self.assertIn("tip-shelf", pay.get("note", ""))
        # Live checkout preserved; no Stripe invent / tip-shelf remint.
        blob = json.dumps(role)
        self.assertIn(LIVE_CHECKOUT, blob)
        for forbidden in ("prod_", "price_", "plink_", "acct_"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
