#!/usr/bin/env python3
"""Hermetic: mailbox-only buyer-reply verify pin.

CLAIM ledger-crm6-mailbox-buyer-reply-verify-20260905-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "host" / "lm_gtm_mailbox_buyer_reply_verify.py"
RECEIPT = ROOT / "p" / "ledger-crm6-mailbox-buyer-reply-verify-20260905-01.md"
BILLINGS = "city-of-billings-bid-1421"
YES_SUBJECT = "hermetic-buyer-reply-yes-01"


def _load():
    spec = importlib.util.spec_from_file_location("mailbox_buyer_reply_verify", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLedgerCrm6MailboxBuyerReplyVerify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_billings_default_is_no_buyer_reply(self):
        result = self.mod.verify_mailbox_buyer_reply(BILLINGS)
        self.assertEqual(result["status"], self.mod.STATUS_NO)
        self.assertEqual(result["mode"], self.mod.MODE_HERMETIC)
        self.assertFalse(result["verified_human_yes"])
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(
            result["outbound_message_ids"],
            ["gmail:1a06e2cbaa802037", "gmail:1a06e2cc33f8c7aa"],
        )
        self.assertEqual(result["inbound_buyer_message_ids"], [])
        self.assertNotIn("VERIFIED_HUMAN_YES", json.dumps(result))

    def test_synthetic_inbound_is_buyer_reply_observed(self):
        result = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
        self.assertEqual(result["status"], self.mod.STATUS_OBSERVED)
        self.assertEqual(result["inbound_buyer_message_ids"], ["gmail:hermetic-in-001"])
        self.assertFalse(result["verified_human_yes"])

    def test_pin_material_reply_only_when_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "revenue" / "lm_gtm_index"
            evidence.mkdir(parents=True)
            evidence_path = evidence / "relationship_handoff_evidence.jsonl"
            evidence_path.write_text("", encoding="utf-8")
            paths = {"root": root}
            no = self.mod.verify_mailbox_buyer_reply(BILLINGS)
            with self.assertRaises(self.mod.idx.IndexError_):
                self.mod.pin_material_reply_evidence(
                    BILLINGS, no, paths, organization="City of Billings"
                )
            yes = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            pinned = self.mod.pin_material_reply_evidence(
                YES_SUBJECT,
                yes,
                paths,
                organization="Hermetic Buyer Fixture",
                event_id="crm6-mailbox-material-reply-hermetic-01",
            )
            self.assertEqual(pinned["type"], "MATERIAL_REPLY")
            self.assertEqual(pinned["kind"], self.mod.KIND_RELATIONSHIP_EVIDENCE)
            rows = self.mod.idx.load_jsonl(evidence_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "crm6-mailbox-material-reply-hermetic-01")
            # INDEX untouched (not present in temp root)
            self.assertFalse((root / "revenue" / "lm_gtm_index" / "INDEX.jsonl").exists())

    def test_receipt_present(self):
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-mailbox-buyer-reply-verify-20260905-01", body)
        self.assertIn("1788653647.048429", body)
        self.assertIn("NO_BUYER_REPLY", body)
        self.assertIn("BUYER_REPLY_OBSERVED", body)
        self.assertIn("#8802", body)
        self.assertIn("VERIFIED_HUMAN_YES", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
