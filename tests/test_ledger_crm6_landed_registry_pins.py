#!/usr/bin/env python3
"""Hermetic: landed CRM6 registry pins after #9237/#9267/#9268/#9269.

CLAIM ledger-crm6-landed-registry-pins-20260906-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "features" / "registry"
MAILBOX_REG = ROOT / "revenue" / "lm_gtm_index" / "mailbox_buyer_reply_registry.json"
HTML = ROOT / "lm-gtm-index.html"
README = ROOT / "revenue" / "lm_gtm_index" / "README.md"
RECEIPT = ROOT / "p" / "ledger-crm6-landed-registry-pins-20260906-01.md"

IDS = (
    "ledger-crm6-mailbox-buyer-reply-verify-20260905-01",
    "ledger-crm6-handoff-mailbox-verify-annotate-20260906-01",
    "ledger-crm6-html-successor-doors-20260906-01",
    "ledger-crm6-mailbox-send-refuse-state-contract-20260906-01",
)


class TestLandedRegistryPins(unittest.TestCase):
    def test_feature_registry_rows(self):
        for fid in IDS:
            path = REG / f"{fid}.json"
            self.assertTrue(path.is_file(), path)
            rec = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(rec.get("schema"), "commons-feature-v1")
            self.assertEqual(rec.get("id"), fid)
            self.assertEqual(rec.get("carrier"), "LEDGER")
            self.assertEqual(rec.get("owner_subsystem"), "lm-gtm-index")

    def test_mailbox_registry_send_refuse_pin(self):
        reg = json.loads(MAILBOX_REG.read_text(encoding="utf-8"))
        self.assertEqual(reg["kind"], "LM_GTM_MAILBOX_BUYER_REPLY_REGISTRY")
        by_pr = {row.get("pr"): row for row in reg.get("landed") or []}
        self.assertIn(9237, by_pr)
        self.assertIn(9269, by_pr)
        row = by_pr[9269]
        self.assertEqual(row["claim_id"], "ledger-crm6-mailbox-send-refuse-state-contract-20260906-01")
        self.assertTrue(str(row["merge_sha"]).startswith("bd7263e3"))
        self.assertIs(row["verified_human_yes"], False)
        self.assertIn("exit 3", str(row.get("mechanism", "")).lower() + str(row.get("send", "")).lower())

    def test_html_and_readme_and_receipt(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("tests/test_ledger_crm6_mailbox_send_refuse_state_contract.py", html)
        self.assertIn("9269", html)
        readme = README.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-landed-registry-pins-20260906-01", readme)
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-landed-registry-pins-20260906-01", body)
        self.assertIn("#8802", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
