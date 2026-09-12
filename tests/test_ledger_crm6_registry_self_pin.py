#!/usr/bin/env python3
"""Hermetic: features/registry self-row for landed-registry-pins #9283.

CLAIM ledger-crm6-registry-self-pin-20260912-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "features" / "registry"
README = ROOT / "revenue" / "lm_gtm_index" / "README.md"
RECEIPT = ROOT / "p" / "ledger-crm6-registry-self-pin-20260912-01.md"

SELF_ID = "ledger-crm6-landed-registry-pins-20260906-01"
CLAIM_ID = "ledger-crm6-registry-self-pin-20260912-01"


class TestRegistrySelfPin(unittest.TestCase):
    def test_landed_pins_self_row(self):
        path = REG / f"{SELF_ID}.json"
        self.assertTrue(path.is_file(), path)
        rec = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(rec.get("schema"), "commons-feature-v1")
        self.assertEqual(rec.get("id"), SELF_ID)
        self.assertEqual(rec.get("carrier"), "LEDGER")
        self.assertEqual(rec.get("owner_subsystem"), "lm-gtm-index")
        links = " ".join(rec.get("resource_links") or [])
        self.assertIn("9283", links)

    def test_claim_self_row(self):
        path = REG / f"{CLAIM_ID}.json"
        self.assertTrue(path.is_file(), path)
        rec = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(rec.get("schema"), "commons-feature-v1")
        self.assertEqual(rec.get("id"), CLAIM_ID)
        self.assertEqual(rec.get("carrier"), "LEDGER")
        self.assertEqual(rec.get("owner_subsystem"), "lm-gtm-index")
        self.assertIs(rec.get("related", {}).get("profitability"), False)

    def test_readme_and_receipt(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn(CLAIM_ID, readme)
        self.assertIn(SELF_ID, readme)
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CLAIM_ID, body)
        self.assertIn("#8802", body)
        self.assertIn("VERIFIED_HUMAN_YES", body)
        self.assertNotIn("VERIFIED_HUMAN_YES: true", body)
        self.assertNotIn("verified_human_yes\": true", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
