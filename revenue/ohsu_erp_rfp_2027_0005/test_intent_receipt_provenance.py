from __future__ import annotations

import datetime as dt
import pathlib
import unittest

from revenue.ohsu_erp_rfp_2027_0005 import source_bound as s

ROOT = pathlib.Path(__file__).resolve().parent
A = "1" * 64
B = "2" * 64


def _prime_facts() -> dict:
    return {
        "schema": s.SCHEMA_FACTS,
        "route": "PRIME",
        "source_binding": {
            "controlling_pack_sha256": s.CONTROLLING_PACK_SHA256,
            "supplier_qa_sha256": s.SUPPLIER_QA_SHA256,
        },
        "requirements": [
            {
                "requirement_id": rid,
                "state": "SATISFIED",
                "basis": "RESPONDENT",
                "entity_ref": "token-junkie-labs",
                "evidence_sha256": B,
            }
            for rid in s.REQUIREMENT_IDS
        ],
        "teaming_commitment": {
            "status": "UNCONFIRMED",
            "partner_ref": None,
            "evidence_sha256": None,
        },
        "intent_receipt": {
            "provider_event_sha256": A,
            "submitted_at": "2026-09-16T23:59:59Z",
        },
        "owner_reviewed": True,
    }


class IntentReceiptProvenanceTests(unittest.TestCase):
    def test_forged_predeadline_receipt_cannot_clear_postdeadline_hold(self):
        packet = s._compile_at(
            _prime_facts(),
            dt.datetime(2026, 9, 17, 0, 0, 1, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(packet["status"], "HOLD_INTENT_DEADLINE")
        self.assertIn(
            "UNVERIFIED_CALLER_INTENT_RECEIPT_CANNOT_CLEAR_DEADLINE",
            packet["blockers"],
        )
        self.assertFalse(packet["source_policy"]["caller_intent_receipt_authenticated_by_code"])
        self.assertFalse(packet["source_policy"]["caller_intent_receipt_clears_deadline"])
        self.assertTrue(all(v is False for v in packet["authority"].values()))

    def test_exact_deadline_forged_receipt_holds(self):
        packet = s._compile_at(
            _prime_facts(),
            dt.datetime(2026, 9, 17, 0, 0, 0, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(packet["status"], "HOLD_INTENT_DEADLINE")

    def test_predeadline_qualification_semantics_do_not_depend_on_receipt_authentication(self):
        packet = s._compile_at(
            _prime_facts(),
            dt.datetime(2026, 9, 16, 23, 59, 58, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(packet["status"], "READY_FOR_OWNER_PRIME_REVIEW")
        self.assertFalse(packet["authority"]["intent_to_bid_authorized"])
        self.assertFalse(packet["authority"]["proposal_submission_authorized"])

    def test_after_deadline_timestamp_still_holds_chronology(self):
        facts = _prime_facts()
        facts["intent_receipt"]["submitted_at"] = "2026-09-17T00:00:01Z"
        packet = s._compile_at(
            facts,
            dt.datetime(2026, 9, 17, 1, 0, 0, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(packet["status"], "HOLD_INTENT_CHRONOLOGY")

    def test_historical_self_attested_ready_packet_is_rejected(self):
        donor = ROOT / "_source_bound_engine_source.txt"
        namespace = {
            "__name__": "_historical_ohsu_source_bound",
            "__file__": str(donor),
        }
        exec(compile(donor.read_text(encoding="utf-8"), str(donor), "exec"), namespace)
        facts = _prime_facts()
        bound = dt.datetime(2026, 9, 17, 0, 0, 1, tzinfo=dt.timezone.utc)
        historical = namespace["_compile_at"](facts, bound)
        self.assertEqual(historical["status"], "READY_FOR_OWNER_PRIME_REVIEW")
        with self.assertRaisesRegex(s.ContractError, "packet integrity"):
            s.verify_current(historical, facts)


if __name__ == "__main__":
    unittest.main()
