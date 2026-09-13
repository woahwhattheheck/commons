#!/usr/bin/env python3
"""Hermetic contract tests for mailbox reply observation materiality fences.

A provider-observed reply is relationship evidence, not proof of human identity
or commercial materiality. Raw mailbox observation must never mint the hottest
MATERIAL_REPLY lane by itself.
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
        self.assertFalse(result["material_reply_verified"])
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(
            result["outbound_message_ids"],
            ["gmail:1a06e2cbaa802037", "gmail:1a06e2cc33f8c7aa"],
        )
        self.assertEqual(result["inbound_buyer_message_ids"], [])
        self.assertNotIn("VERIFIED_HUMAN_YES", json.dumps(result))

    def test_synthetic_inbound_is_observed_never_material(self):
        result = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
        self.assertEqual(result["status"], self.mod.STATUS_OBSERVED)
        self.assertEqual(result["inbound_buyer_message_ids"], ["gmail:hermetic-in-001"])
        self.assertFalse(result["verified_human_yes"])
        self.assertFalse(result["material_reply_verified"])
        self.assertTrue(result["invent_guard"]["never_mint_material_reply_from_arrival"])

    def test_thread_specific_chronology_blocks_pre_anchor_reply(self):
        subject = "thread-anchor-hostile-01"
        fixture = {
            "schema_version": self.mod.idx.SCHEMA_VERSION,
            "kind": self.mod.KIND_FIXTURE,
            "subject_id": subject,
            "cash_usd": 0,
            "messages": [
                {
                    "id": "out-a",
                    "direction": "outbound",
                    "thread_id": "thread-a",
                    "ts": "2026-09-13T10:00:00Z",
                    "role": "seller",
                },
                {
                    "id": "in-b-before-anchor",
                    "direction": "inbound",
                    "thread_id": "thread-b",
                    "ts": "2026-09-13T11:00:00Z",
                    "role": "buyer",
                },
                {
                    "id": "out-b",
                    "direction": "outbound",
                    "thread_id": "thread-b",
                    "ts": "2026-09-13T12:00:00Z",
                    "role": "seller",
                },
            ],
        }
        result = self.mod.verify_mailbox_buyer_reply(subject, fixture=fixture)
        self.assertEqual(result["status"], self.mod.STATUS_NO)
        self.assertEqual(result["inbound_buyer_message_ids"], [])

    def test_duplicate_message_ids_fail_closed(self):
        subject = "duplicate-message-hostile-01"
        fixture = {
            "schema_version": self.mod.idx.SCHEMA_VERSION,
            "kind": self.mod.KIND_FIXTURE,
            "subject_id": subject,
            "cash_usd": 0,
            "messages": [
                {
                    "id": "same-id",
                    "direction": "outbound",
                    "thread_id": "thread-a",
                    "ts": "2026-09-13T10:00:00Z",
                    "role": "seller",
                },
                {
                    "id": "same-id",
                    "direction": "inbound",
                    "thread_id": "thread-a",
                    "ts": "2026-09-13T11:00:00Z",
                    "role": "buyer",
                },
            ],
        }
        with self.assertRaises(self.mod.idx.IndexError_):
            self.mod.verify_mailbox_buyer_reply(subject, fixture=fixture)

    def test_raw_observation_cannot_mint_material_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "revenue" / "lm_gtm_index"
            evidence.mkdir(parents=True)
            evidence_path = evidence / "relationship_handoff_evidence.jsonl"
            evidence_path.write_text("", encoding="utf-8")
            paths = {"root": root}
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            with self.assertRaises(self.mod.idx.IndexError_) as caught:
                self.mod.pin_material_reply_evidence(
                    YES_SUBJECT,
                    observed,
                    paths,
                    organization="Hermetic Buyer Fixture",
                    event_id="crm6-mailbox-material-reply-hermetic-01",
                )
            self.assertIn("does not verify human identity or commercial materiality", str(caught.exception))
            self.assertEqual(self.mod.idx.load_jsonl(evidence_path), [])

    def test_observed_reply_pins_neutral_status_not_hot_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "revenue" / "lm_gtm_index"
            evidence.mkdir(parents=True)
            evidence_path = evidence / "relationship_handoff_evidence.jsonl"
            evidence_path.write_text("", encoding="utf-8")
            paths = {"root": root}
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            pinned = self.mod.pin_buyer_reply_observed_evidence(
                YES_SUBJECT,
                observed,
                paths,
                organization="Hermetic Buyer Fixture",
                event_id="crm6-mailbox-reply-observed-hermetic-01",
                ts="2026-09-13T14:00:00Z",
            )
            self.assertEqual(pinned["type"], "STATUS")
            self.assertEqual(pinned["decision"], self.mod.DECISION_OBSERVED)
            self.assertFalse(pinned["dnr"])
            self.assertEqual(pinned["cash_usd"], 0)
            self.assertEqual(pinned["transport"], "NONE")
            self.assertIn("HUMAN_CLASSIFICATION_REQUIRED", pinned["next_action"])
            rows = self.mod.idx.load_jsonl(evidence_path)
            self.assertEqual(rows, [pinned])

            neutral_row = {
                "role": "external_prospect",
                "live": True,
                "decision": self.mod.DECISION_OBSERVED,
                "dnr": False,
            }
            self.assertIsNone(self.mod.idx.hot_class(neutral_row))
            material_row = dict(neutral_row, decision="MATERIAL_REPLY")
            self.assertEqual(self.mod.idx.hot_class(material_row), "material_reply")

    def test_same_inbound_message_cannot_be_reminted_under_new_event_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "revenue" / "lm_gtm_index"
            evidence.mkdir(parents=True)
            (evidence / "relationship_handoff_evidence.jsonl").write_text("", encoding="utf-8")
            paths = {"root": root}
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            self.mod.pin_buyer_reply_observed_evidence(
                YES_SUBJECT,
                observed,
                paths,
                organization="Hermetic Buyer Fixture",
                event_id="crm6-mailbox-reply-observed-hermetic-01",
                ts="2026-09-13T14:00:00Z",
            )
            with self.assertRaises(self.mod.idx.IndexError_):
                self.mod.pin_buyer_reply_observed_evidence(
                    YES_SUBJECT,
                    observed,
                    paths,
                    organization="Hermetic Buyer Fixture",
                    event_id="crm6-mailbox-reply-observed-hermetic-02",
                    ts="2026-09-13T14:01:00Z",
                )

    def test_no_observation_cannot_be_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "revenue" / "lm_gtm_index"
            evidence.mkdir(parents=True)
            (evidence / "relationship_handoff_evidence.jsonl").write_text("", encoding="utf-8")
            result = self.mod.verify_mailbox_buyer_reply(BILLINGS)
            with self.assertRaises(self.mod.idx.IndexError_):
                self.mod.pin_buyer_reply_observed_evidence(
                    BILLINGS,
                    result,
                    {"root": root},
                    organization="City of Billings",
                    event_id="crm6-mailbox-reply-observed-billings-01",
                )

    def test_original_receipt_remains_available_for_lineage(self):
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
