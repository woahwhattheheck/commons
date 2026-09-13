#!/usr/bin/env python3
"""Hostiles for mailbox reply chronology, fixture generation, and pin time."""
from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "host" / "lm_gtm_mailbox_buyer_reply_verify.py"
YES_SUBJECT = "hermetic-buyer-reply-yes-01"


def _load():
    spec = importlib.util.spec_from_file_location("mailbox_buyer_reply_verify", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(subject: str, inbound_ts: str) -> dict:
    return {
        "schema_version": "commons-lm-gtm-index/v1",
        "kind": "LM_GTM_MAILBOX_FIXTURE",
        "subject_id": subject,
        "cash_usd": 0,
        "messages": [
            {
                "id": "out-001",
                "direction": "outbound",
                "thread_id": "thread-001",
                "ts": "2026-09-13T10:00:00Z",
                "role": "seller",
            },
            {
                "id": "in-001",
                "direction": "inbound",
                "thread_id": "thread-001",
                "ts": inbound_ts,
                "role": "buyer",
            },
        ],
    }


class TestBuyerReplyChronologyGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _empty_evidence_root(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        evidence = root / "revenue" / "lm_gtm_index"
        evidence.mkdir(parents=True)
        (evidence / "relationship_handoff_evidence.jsonl").write_text("", encoding="utf-8")
        return tmp, root

    def test_equal_timestamp_does_not_establish_reply_order(self):
        subject = "equal-chronology-hostile-01"
        result = self.mod.verify_mailbox_buyer_reply(
            subject,
            fixture=_fixture(subject, "2026-09-13T10:00:00Z"),
        )
        self.assertEqual(result["status"], self.mod.STATUS_NO)
        self.assertEqual(result["inbound_buyer_message_ids"], [])
        self.assertIsNone(result["inbound_buyer_latest_ts"])

    def test_strictly_later_reply_is_observed_and_time_bound(self):
        subject = "strict-chronology-positive-01"
        result = self.mod.verify_mailbox_buyer_reply(
            subject,
            fixture=_fixture(subject, "2026-09-13T10:00:01Z"),
        )
        self.assertEqual(result["status"], self.mod.STATUS_OBSERVED)
        self.assertEqual(result["inbound_buyer_message_ids"], ["in-001"])
        self.assertEqual(result["inbound_buyer_latest_ts"], "2026-09-13T10:00:01Z")
        self.assertRegex(result["fixture_generation_sha256"], r"^[0-9a-f]{64}$")

    def test_fixture_generation_digest_changes_with_validated_source(self):
        subject = "fixture-generation-hostile-01"
        fixture = _fixture(subject, "2026-09-13T10:00:01Z")
        first = self.mod.verify_mailbox_buyer_reply(subject, fixture=fixture)
        changed = copy.deepcopy(fixture)
        changed["notes"] = "same mailbox semantics, different validated fixture generation"
        second = self.mod.verify_mailbox_buyer_reply(subject, fixture=changed)
        self.assertNotEqual(
            first["fixture_generation_sha256"],
            second["fixture_generation_sha256"],
        )

    def test_valid_pin_carries_fixture_generation_and_source_horizon(self):
        tmp, root = self._empty_evidence_root()
        with tmp:
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            pinned = self.mod.pin_buyer_reply_observed_evidence(
                YES_SUBJECT,
                observed,
                {"root": root},
                organization="Hermetic Buyer Fixture",
                event_id="crm6-generation-bound-observed-01",
                ts="2026-09-13T14:00:00Z",
            )
            self.assertEqual(
                pinned["mailbox_fixture_sha256"],
                observed["fixture_generation_sha256"],
            )
            self.assertEqual(
                pinned["source_observed_through"],
                observed["inbound_buyer_latest_ts"],
            )

    def test_pin_timestamp_cannot_predate_inbound_source(self):
        tmp, root = self._empty_evidence_root()
        with tmp:
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            with self.assertRaises(self.mod.idx.IndexError_) as caught:
                self.mod.pin_buyer_reply_observed_evidence(
                    YES_SUBJECT,
                    observed,
                    {"root": root},
                    organization="Hermetic Buyer Fixture",
                    event_id="crm6-pre-source-observation-hostile-01",
                    ts="2026-09-05T15:29:59Z",
                )
            self.assertIn("predates inbound source", str(caught.exception))
            evidence_path = root / "revenue" / "lm_gtm_index" / "relationship_handoff_evidence.jsonl"
            self.assertEqual(self.mod.idx.load_jsonl(evidence_path), [])

    def test_pin_timestamp_cannot_be_arbitrarily_future_dated(self):
        tmp, root = self._empty_evidence_root()
        with tmp:
            observed = self.mod.verify_mailbox_buyer_reply(YES_SUBJECT)
            with self.assertRaises(self.mod.idx.IndexError_) as caught:
                self.mod.pin_buyer_reply_observed_evidence(
                    YES_SUBJECT,
                    observed,
                    {"root": root},
                    organization="Hermetic Buyer Fixture",
                    event_id="crm6-future-observation-hostile-01",
                    ts="2999-01-01T00:00:00Z",
                )
            self.assertIn("observation timestamp is in the future", str(caught.exception))
            evidence_path = root / "revenue" / "lm_gtm_index" / "relationship_handoff_evidence.jsonl"
            self.assertEqual(self.mod.idx.load_jsonl(evidence_path), [])

    def test_mutated_generation_identity_cannot_pin(self):
        tmp, root = self._empty_evidence_root()
        with tmp:
            observed = dict(self.mod.verify_mailbox_buyer_reply(YES_SUBJECT))
            observed["fixture_generation_sha256"] = "0" * 64
            with self.assertRaises(self.mod.idx.IndexError_) as caught:
                self.mod.pin_buyer_reply_observed_evidence(
                    YES_SUBJECT,
                    observed,
                    {"root": root},
                    organization="Hermetic Buyer Fixture",
                    event_id="crm6-generation-tamper-hostile-01",
                    ts="2026-09-13T14:00:00Z",
                )
            self.assertIn("does not match the canonical current hermetic fixture", str(caught.exception))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
