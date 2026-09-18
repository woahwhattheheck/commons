#!/usr/bin/env python3
"""Exact-evidence tests for the dated White Box collaboration-offer catalog."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "whitebox_collaboration_offers", ROOT / "host/whitebox_collaboration_offers.py"
)
offers = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(offers)


class WhiteBoxCollaborationOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.schema = offers.load(ROOT)

    def test_schema_and_semantic_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/ip").validate_file(
            self.data, "whitebox_collaboration_offers.schema.json"
        )
        result = offers.validate(ROOT, self.data, self.schema)
        self.assertEqual(
            result,
            {
                "status": "VALID",
                "offers": 4,
                "available": 2,
                "scoping": 1,
                "blocked": 1,
                "entry_routes": 1,
                "archive_transfer_cleared": False,
                "cash_received": False,
            },
        )

    def test_exact_four_roads_and_states(self):
        self.assertEqual([offer["id"] for offer in self.data["offers"]], list(offers.OFFER_IDS))
        self.assertEqual(
            [offer["state"] for offer in self.data["offers"]],
            ["BLOCKED_EVIDENCE_REQUIRED", "AVAILABLE_CUSTOMER_OWNED_ASSET", "SCOPING_AVAILABLE", "AVAILABLE_CUSTOMER_OWNED_ASSET"],
        )

    def test_archive_license_cannot_be_marked_available(self):
        broken = copy.deepcopy(self.data)
        broken["offers"][0]["state"] = "SCOPING_AVAILABLE"
        with self.assertRaisesRegex(offers.CollaborationOfferError, "archive license must remain blocked"):
            offers.validate(ROOT, broken, self.schema)

    def test_no_offer_can_transfer_owner_archive_payload(self):
        broken = copy.deepcopy(self.data)
        broken["offers"][2]["uses_owner_archive_payload"] = True
        with self.assertRaisesRegex(offers.CollaborationOfferError, "archive payload use must remain false"):
            offers.validate(ROOT, broken, self.schema)

    def test_non_archive_roads_cannot_switch_to_owner_archive(self):
        messages = ("benchmark asset boundary drift", "joint-paper asset boundary drift", "private evaluation asset boundary drift")
        for index, message in zip((1, 2, 3), messages):
            with self.subTest(offer=self.data["offers"][index]["id"]):
                broken = copy.deepcopy(self.data)
                broken["offers"][index]["asset_boundary"] = "OWNER_ARCHIVE"
                with self.assertRaisesRegex(offers.CollaborationOfferError, message):
                    offers.validate(ROOT, broken, self.schema)

    def test_exact_service_prices_fail_closed(self):
        broken = copy.deepcopy(self.data)
        broken["offers"][1]["price"]["amount_usd"] = 12500
        with self.assertRaisesRegex(offers.CollaborationOfferError, "sponsored benchmark price drift"):
            offers.validate(ROOT, broken, self.schema)

    def test_source_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["sources"][0]["blob_sha"] = "0" * 40
        with self.assertRaisesRegex(offers.CollaborationOfferError, "source blob drift"):
            offers.validate(ROOT, broken, self.schema)

    def test_commercial_truth_cannot_be_invented(self):
        broken = copy.deepcopy(self.data)
        broken["truth"]["cash_received"] = True
        with self.assertRaisesRegex(offers.CollaborationOfferError, "may not invent"):
            offers.validate(ROOT, broken, self.schema)

    def test_live_entry_checkout_is_exact(self):
        broken = copy.deepcopy(self.data)
        broken["entry_routes"][0]["checkout_url"] = "https://example.com"
        with self.assertRaisesRegex(offers.CollaborationOfferError, "checkout route drift"):
            offers.validate(ROOT, broken, self.schema)

    def test_cli_validate(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/whitebox_collaboration_offers.py"), "validate", "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["offers"], 4)


if __name__ == "__main__":
    unittest.main()
