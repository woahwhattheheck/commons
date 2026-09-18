#!/usr/bin/env python3
"""Hermetic: mailbox --send refuse + state.json CRM6 contract pins.

CLAIM ledger-crm6-mailbox-send-refuse-state-contract-20260906-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import importlib.util
import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAILBOX_PATH = ROOT / "host" / "lm_gtm_mailbox_buyer_reply_verify.py"
STATE = ROOT / "revenue" / "lm_gtm_index" / "state.json"
README = ROOT / "revenue" / "lm_gtm_index" / "README.md"
RECEIPT = ROOT / "p" / "ledger-crm6-mailbox-send-refuse-state-contract-20260906-01.md"
BILLINGS = "city-of-billings-bid-1421"


def _load_mailbox():
    spec = importlib.util.spec_from_file_location(
        "lm_gtm_mailbox_buyer_reply_verify_send_refuse", MAILBOX_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMailboxSendRefuseStateContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mailbox = _load_mailbox()

    def test_send_flag_exits_3(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = self.mailbox.main([BILLINGS, "--send"])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED live send", err.getvalue())

    def test_send_subcommand_exits_3(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = self.mailbox.main(["send", BILLINGS])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED live send", err.getvalue())

    def test_billings_verify_still_no_buyer_reply(self):
        result = self.mailbox.verify_mailbox_buyer_reply(BILLINGS)
        self.assertEqual(result["status"], "NO_BUYER_REPLY")
        self.assertIs(result["verified_human_yes"], False)

    def test_state_contract_pins(self):
        state = json.loads(STATE.read_text(encoding="utf-8"))
        contract = state["contract"]
        self.assertEqual(
            contract["mailbox_verify"],
            "python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT",
        )
        self.assertEqual(
            contract["handoff_mailbox_verify"],
            "python3 host/lm_gtm_relationship_handoff.py SUBJECT --mailbox-verify",
        )
        self.assertEqual(contract["mailbox_send"], "illegal; exits 3")
        self.assertEqual(contract["send"], "illegal; exits 3")

    def test_readme_and_receipt(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn(
            "ledger-crm6-mailbox-send-refuse-state-contract-20260906-01", readme
        )
        self.assertIn("Mailbox CLI `--send` exits 3", readme)
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-mailbox-send-refuse-state-contract-20260906-01", body)
        self.assertIn("#8802", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
