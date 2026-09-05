from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST_HANDOFF = ROOT / "host" / "lm_gtm_relationship_handoff.py"
SPEC = importlib.util.spec_from_file_location("lm_gtm_relationship_handoff", HOST_HANDOFF)
assert SPEC and SPEC.loader
handoff_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff_mod)

idx = handoff_mod.idx
EMAIL_RE = idx.EMAIL_AT_RE
PHONE_RE = idx.PHONE_RE
BILLINGS = "city-of-billings-bid-1421"
BILLINGS_OWNER_HOLD = "lm-gtm-billings-owner-hold-status-20260831-02"
BILLINGS_POINTER = "lm-gtm-billings-material-reply-20260831-01"
BILLINGS_SENT = "crm6-billings-submission-sent-20260904-01"
BILLINGS_POST_SUBMISSION = "crm6-billings-post-submission-status-20260904-01"


class RelationshipHandoffTests(unittest.TestCase):
    def test_billings_handoff_is_evidence_bound_and_current(self) -> None:
        packet = handoff_mod.relationship_handoff(BILLINGS)
        self.assertEqual(packet["kind"], "LM_GTM_RELATIONSHIP_HANDOFF")
        self.assertEqual(packet["subject_id"], BILLINGS)
        self.assertEqual(packet["decision"], "OWNER_HOLD")
        self.assertEqual(packet["lane"], "owner_hold")
        self.assertTrue(packet["dnr"])
        self.assertEqual(packet["due"], "2026-09-28")
        self.assertEqual(packet["route_ref"], "airtable:rec2mCS4ETa8FOvqN")
        self.assertEqual(
            packet["canonical_crm"],
            "JOJO Revenue Recovery CRM / Revenue Pipeline",
        )
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["transport"], "NONE")
        self.assertTrue(packet["invent_guard"]["no_second_crm"])
        self.assertTrue(packet["invent_guard"]["no_customer_contact"])
        self.assertTrue(packet["invent_guard"]["pointer_is_not_message"])
        self.assertTrue(
            packet["invent_guard"]["relationship_evidence_is_not_crm"]
        )

        relationship = packet["relationship_evidence"]
        self.assertEqual(
            relationship["path"],
            "revenue/lm_gtm_index/relationship_handoff_evidence.jsonl",
        )
        self.assertFalse(relationship["canonical_index_mutated"])
        self.assertEqual(
            relationship["event_ids"],
            [BILLINGS_SENT, BILLINGS_POST_SUBMISSION],
        )

        fields = packet["fields"]
        successor = fields["successor_next_action"]
        self.assertEqual(successor["status"], "SOURCED")
        nxt = successor["value"].casefold()
        self.assertIn("owner_hold", nxt)
        self.assertIn("submission_sent", nxt)
        self.assertIn("do not resend", nxt)
        self.assertIn("do not contact cheri", nxt)
        self.assertIn("recipient acknowledgement", nxt)
        self.assertIn("award", nxt)
        self.assertIn("payment", nxt)
        self.assertIn("no duplicate bid submission by agents", nxt)
        self.assertNotIn("submit the bid now", nxt)
        self.assertNotIn("owner emails cheri", nxt)

        due = fields["next_time_sensitive"]
        self.assertEqual(due["status"], "SOURCED")
        self.assertEqual(due["value"], "2026-09-28")
        self.assertIn(
            f"relationship:{BILLINGS_POST_SUBMISSION}", due["evidence"]
        )

        sent = fields["sent_communication"]
        self.assertEqual(sent["status"], "SOURCED")
        self.assertEqual(sent["provenance"], "SUMMARY_POINTER")
        self.assertIn("two outbound messages", sent["value"].casefold())
        self.assertIn("gmail:1a06e2cbaa802037", sent["evidence"])
        self.assertIn("gmail:1a06e2cc33f8c7aa", sent["evidence"])
        self.assertIn(f"relationship:{BILLINGS_SENT}", sent["evidence"])

        promised = fields["promised"]
        self.assertEqual(promised["status"], "ABSENT")

        chain = {item["id"]: item for item in packet["evidence_chain"]}
        self.assertIn(BILLINGS_OWNER_HOLD, chain)
        self.assertIn(BILLINGS_POINTER, chain)
        self.assertIn(BILLINGS_SENT, chain)
        self.assertIn(BILLINGS_POST_SUBMISSION, chain)
        self.assertEqual(
            chain[BILLINGS_SENT]["source_kind"], "RELATIONSHIP_EVIDENCE"
        )
        self.assertEqual(
            chain[BILLINGS_POST_SUBMISSION]["source_kind"],
            "RELATIONSHIP_EVIDENCE",
        )
        self.assertEqual(
            chain[BILLINGS_OWNER_HOLD]["source_kind"], "INDEX_OVERLAY"
        )

        blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))
        for token in ("armstrongc@", "cheri@", "@billingsmt.gov", "6803283352"):
            self.assertNotIn(token, blob)

    def test_successor_reads_next_action_from_packet_only(self) -> None:
        packet = handoff_mod.relationship_handoff(BILLINGS)
        value = handoff_mod.successor_reads_next_action(packet)
        self.assertIsNotNone(value)
        assert value is not None
        self.assertEqual(value, packet["fields"]["successor_next_action"]["value"])
        self.assertIn("OWNER_HOLD", value)
        self.assertIn("SUBMISSION_SENT", value)
        # Prove no re-read of ledgers is required: strip to packet fields only.
        slim = {
            "fields": {
                "successor_next_action": packet["fields"]["successor_next_action"]
            }
        }
        self.assertEqual(handoff_mod.successor_reads_next_action(slim), value)

    def test_unknown_subject_fails_closed(self) -> None:
        with self.assertRaises(idx.IndexError_):
            handoff_mod.relationship_handoff("brand-new-buyer-mint-refuse")

    def test_composio_hot_handoff_surfaces_ready_to_draft(self) -> None:
        packet = handoff_mod.relationship_handoff("composio")
        self.assertEqual(packet["decision"], "READY_TO_DRAFT")
        self.assertEqual(packet["lane"], "ready_to_draft")
        self.assertEqual(packet["relationship_evidence"]["event_ids"], [])
        self.assertEqual(packet["fields"]["successor_next_action"]["status"], "SOURCED")

    def test_cli_billings_and_send_exit(self) -> None:
        ok = subprocess.run(
            [sys.executable, str(HOST_HANDOFF), BILLINGS],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        packet = json.loads(ok.stdout)
        self.assertEqual(packet["subject_id"], BILLINGS)
        self.assertEqual(packet["decision"], "OWNER_HOLD")
        self.assertEqual(packet["due"], "2026-09-28")
        self.assertIn(
            "SUBMISSION_SENT",
            packet["fields"]["successor_next_action"]["value"],
        )
        self.assertIsNone(EMAIL_RE.search(ok.stdout))
        self.assertIsNone(PHONE_RE.search(ok.stdout))

        refused = subprocess.run(
            [sys.executable, str(HOST_HANDOFF), BILLINGS, "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(refused.returncode, 3)
        self.assertIn("never transports mail", refused.stderr.casefold())

    def test_no_second_crm_roots(self) -> None:
        for name in ("crm", "people", "contacts", "sales"):
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
