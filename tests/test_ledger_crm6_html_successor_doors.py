#!/usr/bin/env python3
"""Hermetic: public lm-gtm-index.html successor doors how-to.

CLAIM ledger-crm6-html-successor-doors-20260906-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "lm-gtm-index.html"
RECEIPT = ROOT / "p" / "ledger-crm6-html-successor-doors-20260906-01.md"


class TestHtmlSuccessorDoors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = HTML.read_text(encoding="utf-8")

    def test_successor_doors_section_present(self):
        self.assertIn('id="successor-doors-heading"', self.body)
        self.assertIn("Successor doors (CRM6 how-to)", self.body)
        self.assertIn("ledger-crm6-html-successor-doors-20260906-01", self.body)

    def test_brief_freshness_mailbox_annotate_pins(self):
        self.assertIn("python3 host/lm_gtm_index.py brief", self.body)
        self.assertIn("python3 host/lm_gtm_index.py freshness", self.body)
        self.assertIn(
            "python3 host/lm_gtm_mailbox_buyer_reply_verify.py city-of-billings-bid-1421",
            self.body,
        )
        self.assertIn("--mailbox-verify", self.body)
        self.assertIn("--index-freshness", self.body)
        self.assertIn("--brief", self.body)

    def test_send_exit_3_and_never_invent_yes(self):
        self.assertIn("--send", self.body)
        self.assertIn("exits 3", self.body)
        self.assertIn("VERIFIED_HUMAN_YES", self.body)
        self.assertIn("Never invent", self.body)
        self.assertIn("NO_BUYER_REPLY", self.body)

    def test_hermetic_unittest_pins(self):
        self.assertIn(
            "tests/test_ledger_crm6_composed_at_freshness_gate.py", self.body
        )
        self.assertIn(
            "tests/test_ledger_crm6_mailbox_buyer_reply_verify.py", self.body
        )
        self.assertIn(
            "tests/test_ledger_crm6_handoff_mailbox_verify_annotate.py", self.body
        )
        self.assertIn(
            "tests/test_ledger_crm6_html_successor_doors.py", self.body
        )

    def test_receipt(self):
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-html-successor-doors-20260906-01", receipt)
        self.assertIn("lm-gtm-index.html", receipt)
        self.assertIn("#8802", receipt)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
