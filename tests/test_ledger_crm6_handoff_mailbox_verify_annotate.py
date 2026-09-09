#!/usr/bin/env python3
"""Hermetic: optional --mailbox-verify annotate on CRM6 handoff.

CLAIM ledger-crm6-handoff-mailbox-verify-annotate-20260906-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_PATH = ROOT / "host" / "lm_gtm_relationship_handoff.py"
REGISTRY = ROOT / "revenue" / "lm_gtm_index" / "mailbox_buyer_reply_registry.json"
RECEIPT = ROOT / "p" / "ledger-crm6-handoff-mailbox-verify-annotate-20260906-01.md"
BILLINGS = "city-of-billings-bid-1421"


def _load_handoff():
    spec = importlib.util.spec_from_file_location("lm_gtm_relationship_handoff_annotate", HANDOFF_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHandoffMailboxVerifyAnnotate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handoff = _load_handoff()

    def test_default_handoff_omits_mailbox_verify(self):
        packet = self.handoff.relationship_handoff(BILLINGS)
        self.assertNotIn("mailbox_verify", packet)

    def test_billings_mailbox_verify_is_no_buyer_reply(self):
        packet = self.handoff.relationship_handoff(BILLINGS, include_mailbox_verify=True)
        mv = packet["mailbox_verify"]
        self.assertEqual(mv["status"], "NO_BUYER_REPLY")
        self.assertIs(mv["verified_human_yes"], False)
        self.assertEqual(mv["cash_usd"], 0)
        brief = self.handoff.successor_brief(packet)
        self.assertIn("mailbox_verify", brief)
        self.assertIn("NO_BUYER_REPLY", brief)

    def test_unknown_when_fixture_missing(self):
        with patch.object(
            self.handoff.mailbox_verify,
            "verify_mailbox_buyer_reply",
            side_effect=self.handoff.idx.IndexError_("missing"),
        ):
            packet = self.handoff.relationship_handoff(
                BILLINGS, include_mailbox_verify=True
            )
        self.assertEqual(packet["mailbox_verify"]["status"], "UNKNOWN")
        self.assertIs(packet["mailbox_verify"]["verified_human_yes"], False)
        self.assertIsNotNone(self.handoff.successor_reads_next_action(packet))

    def test_refuses_invented_verified_human_yes(self):
        bad = {
            "status": "BUYER_REPLY_OBSERVED",
            "verified_human_yes": True,
            "cash_usd": 0,
        }
        with patch.object(
            self.handoff.mailbox_verify,
            "verify_mailbox_buyer_reply",
            return_value=bad,
        ):
            packet = self.handoff.relationship_handoff(
                BILLINGS, include_mailbox_verify=True
            )
        # fail-closed to UNKNOWN rather than invent YES
        self.assertEqual(packet["mailbox_verify"]["status"], "UNKNOWN")
        self.assertIs(packet["mailbox_verify"]["verified_human_yes"], False)

    def test_registry_and_receipt(self):
        self.assertTrue(REGISTRY.is_file(), REGISTRY)
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(reg["kind"], "LM_GTM_MAILBOX_BUYER_REPLY_REGISTRY")
        self.assertEqual(reg["landed"][0]["claim_id"], "ledger-crm6-mailbox-buyer-reply-verify-20260905-01")
        self.assertEqual(reg["landed"][0]["pr"], 9237)
        self.assertFalse(reg["landed"][0]["verified_human_yes"])
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-handoff-mailbox-verify-annotate-20260906-01", body)
        self.assertIn("--mailbox-verify", body)
        self.assertIn("#8802", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
