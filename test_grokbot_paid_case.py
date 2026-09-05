#!/usr/bin/env python3
"""Hermetic tests for Autopsy → G2 paid-case builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from integrations.grokbot_control.paid_case import (
    case_from_autopsy_offer,
    load_autopsy_offer,
)

ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "revenue" / "agent_failure_autopsy" / "offer.json"


class TestAutopsyPaidCase(unittest.TestCase):
    def test_load_checked_in_offer(self):
        offer = load_autopsy_offer()
        self.assertEqual(offer["offer_id"], "agent-failure-autopsy-29")
        self.assertEqual(offer["price"]["payment_url_state"], "LIVE_VERIFIED")

    def test_case_from_default_offer(self):
        case = case_from_autopsy_offer(
            case_ref="private-case-opaque-1",
            client_reference_id="cref-demo",
        )
        self.assertEqual(
            case,
            {
                "offer_id": "agent-failure-autopsy-29",
                "case_ref": "private-case-opaque-1",
                "client_reference_id": "cref-demo",
                "sku": "agent-failure-autopsy-29",
            },
        )

    def test_case_from_mapping_and_path(self):
        offer = json.loads(OFFER.read_text(encoding="utf-8"))
        from_map = case_from_autopsy_offer(offer, case_ref="c2")
        from_path = case_from_autopsy_offer(OFFER, case_ref="c2")
        self.assertEqual(from_map, from_path)
        self.assertEqual(from_map["sku"], "agent-failure-autopsy-29")
        self.assertNotIn("client_reference_id", from_map)

    def test_custom_sku_and_rejects(self):
        case = case_from_autopsy_offer(case_ref="c3", sku="custom-sku")
        self.assertEqual(case["sku"], "custom-sku")
        with self.assertRaises(ValueError):
            case_from_autopsy_offer(case_ref="")
        with self.assertRaises(ValueError):
            case_from_autopsy_offer({"offer_id": ""}, case_ref="c")
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "offer.json"
            bad.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_autopsy_offer(bad)


if __name__ == "__main__":
    unittest.main()
